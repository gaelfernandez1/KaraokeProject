import { describe, expect, it } from 'vitest';
import { ApiError } from '#lib/api';
import { PartyConnection } from './connection.svelte';
import type { PartyCommand, PartyState } from './types';

/** Stands in for EventSource: the test dispatches the server's events by hand. */
class FakeSource {
	readonly url: string;
	closed = false;
	readyState = 1;
	readonly #listeners = new Map<string, ((event: unknown) => void)[]>();

	constructor(url: string) {
		this.url = url;
	}

	addEventListener(type: string, listener: (event: unknown) => void): void {
		this.#listeners.set(type, [...(this.#listeners.get(type) ?? []), listener]);
	}

	close(): void {
		this.closed = true;
	}

	emit(type: string, data?: unknown): void {
		if (this.closed) return;
		const event = data === undefined ? { type } : { type, data: JSON.stringify(data) };
		for (const listener of this.#listeners.get(type) ?? []) listener(event);
	}
}

function snapshot(version: number, title = 'Song'): PartyState {
	return {
		code: 'BCDF',
		version,
		guests: [],
		queue: [
			{
				id: 'q1',
				guest_id: 'g1',
				song_id: 's1',
				title,
				artist: null,
				duration: 180,
				added_at: 1,
				state: 'queued',
				promoted: false
			}
		],
		playback: { item_id: null, playing: false, position: 0, at: 0, vocals: 0.15, pitch: 0 },
		settings: { guests_control: false }
	};
}

function connect(fetchParty: (code: string) => Promise<unknown> = async () => ({})) {
	const sources: FakeSource[] = [];
	const commands: PartyCommand[] = [];
	const connection = new PartyConnection('bcdf', 'tok', {
		fetchParty,
		createSource: (url) => {
			const source = new FakeSource(url);
			sources.push(source);
			return source as unknown as EventSource;
		},
		onCommand: (command) => commands.push(command)
	});
	connection.start();
	return { connection, source: sources[0], sources, commands };
}

describe('PartyConnection', () => {
	it('knows when the TV ends the party, and stops listening', () => {
		const { connection, source } = connect();
		source.emit('state', snapshot(3));
		source.emit('ended', snapshot(3));
		expect(connection.ended).toBe(true);
		expect(source.closed).toBe(true);
	});

	it('takes a party the server no longer has as ended', async () => {
		const gone = new ApiError(404, 'No such party', 'not_found');
		const { connection, source } = connect(() => Promise.reject(gone));
		source.readyState = 2; // the browser gave up: the events URL answered 404
		source.emit('error');
		await Promise.resolve();
		await Promise.resolve();
		expect(connection.ended).toBe(true);
	});

	it('keeps waiting while the browser is still reconnecting', async () => {
		const { connection, source } = connect(() => Promise.reject(new Error('should not ask')));
		source.emit('error');
		await Promise.resolve();
		expect(connection.ended).toBe(false);
	});

	it('listens to the party events with its token', () => {
		const { connection, source } = connect();
		expect(source.url).toBe('/api/parties/BCDF/events?token=tok');
		expect(connection.state).toBeNull();
		expect(connection.connected).toBe(false);
	});

	it('takes the state the server sends', () => {
		const { connection, source } = connect();
		source.emit('state', snapshot(3));
		expect(connection.state).toEqual(snapshot(3));
		source.emit('state', snapshot(4, 'Next'));
		expect(connection.state?.queue[0].title).toBe('Next');
	});

	it('ignores a state older than or as old as the one it has', () => {
		const { connection, source } = connect();
		source.emit('state', snapshot(5, 'New'));
		source.emit('state', snapshot(4, 'Stale'));
		source.emit('state', snapshot(5, 'Same'));
		expect(connection.state?.version).toBe(5);
		expect(connection.state?.queue[0].title).toBe('New');
	});

	it('takes the first state after reconnecting even if a restarted server counts from 1', () => {
		const { connection, source } = connect();
		source.emit('open', {});
		source.emit('state', snapshot(57, 'Before'));
		source.emit('error', {});
		source.emit('open', {});
		source.emit('state', snapshot(1, 'After restart'));
		expect(connection.state?.queue[0].title).toBe('After restart');
		source.emit('state', snapshot(1, 'Same again'));
		expect(connection.state?.queue[0].title).toBe('After restart');
	});

	it('hands commands to the TV', () => {
		const { source, commands } = connect();
		source.emit('command', { type: 'pause' });
		source.emit('command', { type: 'pitch', value: -2 });
		expect(commands).toEqual([{ type: 'pause' }, { type: 'pitch', value: -2 }]);
	});

	it('says whether it is connected', () => {
		const { connection, source } = connect();
		source.emit('open');
		expect(connection.connected).toBe(true);
		source.emit('error');
		expect(connection.connected).toBe(false);
		source.emit('open');
		expect(connection.connected).toBe(true);
	});

	it('starts only once', () => {
		const { connection, sources } = connect();
		connection.start();
		expect(sources).toHaveLength(1);
	});

	it('stops listening when closed', () => {
		const { connection, source } = connect();
		source.emit('open');
		connection.close();
		expect(source.closed).toBe(true);
		expect(connection.connected).toBe(false);
	});
});
