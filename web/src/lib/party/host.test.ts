import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { PlayerSession } from '#lib/player/session.svelte.js';
import type { PartyState, QueueItem } from './types';

const advance = vi.fn(async (...args: unknown[]) => void args);
const endParty = vi.fn(async (...args: unknown[]) => void args);
vi.mock('./client', () => ({
	advance: (...args: unknown[]) => advance(...args),
	endParty: (...args: unknown[]) => endParty(...args),
	publishPlayback: async () => {},
	updateSettings: async () => {}
}));

let loads: { resolve: () => void; reject: (e: Error) => void; songId: string }[] = [];
vi.mock('#lib/api', () => ({
	mediaUrl: (id: string, file: string) => `/media/${id}/${file}`,
	getDoc: (songId: string) =>
		new Promise((resolve, reject) =>
			loads.push({
				songId,
				resolve: () => resolve({ title: songId, audio: { instrumental: 'i.m4a', vocals: null } }),
				reject
			})
		)
}));

const { HostParty, ERROR_GRACE_MS } = await import('./host.svelte');

class FakeSession {
	state = 'idle';
	playing = false;
	time = 0;
	duration = 100;
	vocals = 0;
	pitch = 0;
	plays = 0;
	clock = { now: () => this.time };
	tick() {}
	async load() {
		this.state = 'ready';
	}
	seek() {}
	async play() {
		this.plays++;
		this.playing = true;
		this.state = 'playing';
	}
	pause() {
		this.playing = false;
	}
	destroy() {}
	setVocals() {}
	async setPitch() {}
}

const item = (id: string, state: QueueItem['state'] = 'queued', added = 1): QueueItem => ({
	id,
	guest_id: 'g1',
	song_id: `song-${id}`,
	title: id,
	artist: null,
	duration: 100,
	added_at: added,
	state,
	promoted: false
});

function party(queue: QueueItem[]): PartyState {
	return {
		code: 'ABCD',
		version: 1,
		guests: [{ id: 'g1', name: 'Ana', color: '#FF8A3D', joined_at: 0 }],
		queue,
		playback: { item_id: null, playing: false, position: 0, at: 0, vocals: 0, pitch: 0 },
		settings: { guests_control: false }
	};
}

const flush = () => new Promise((r) => setTimeout(r, 0));

function setup(queue: QueueItem[]) {
	const session = new FakeSession();
	const host = new HostParty(
		{ code: 'ABCD', host_token: 't' },
		{ device: { vocals: 0, latencyMs: 0 }, session: session as unknown as PlayerSession }
	);
	host.connection.state = party(queue);
	return { host, session };
}

describe('HostParty', () => {
	beforeEach(() => {
		loads = [];
		advance.mockClear();
	});

	it('does not announce a song it has just ended while the server state still says playing', async () => {
		const { host } = setup([item('a', 'playing')]);
		host.frame();
		expect(host.current?.id).toBe('a');
		host.skip();
		await flush();
		host.frame();
		expect(host.phase).toBe('lobby');
		expect(loads.map((l) => l.songId)).toEqual(['song-a']);
	});

	it('ignores a slow load of a song skipped meanwhile', async () => {
		const { host, session } = setup([item('a'), item('b', 'queued', 2)]);
		host.frame();
		host.skip();
		await flush();
		host.frame();
		expect(host.current?.id).toBe('b');
		loads[0].resolve();
		await flush();
		expect(host.doc).toBeNull();
		loads[1].resolve();
		await flush();
		expect(host.doc?.title).toBe('song-b');
		host.startNow();
		await flush();
		expect(session.plays).toBe(1);
	});

	it('a song started before its lyrics arrive waits for them instead of ending', async () => {
		const { host, session } = setup([item('a'), item('b', 'queued', 2)]);
		host.frame();
		loads[0].resolve();
		await flush();
		host.startNow();
		await flush();
		// Song a plays to its end; the session still says so while b is announced.
		session.playing = false;
		session.state = 'ended';
		host.frame();
		await flush();
		host.frame();
		expect(host.current?.id).toBe('b');
		host.startNow(); // before b's karaoke.json has arrived
		await flush();
		host.frame();
		await flush();
		// Nothing of b plays (nor a's audio again) until b is loaded.
		expect(session.plays).toBe(1);
		expect(host.phase).toBe('countdown');
		expect(advance.mock.calls.map((c) => `${String(c[2])}:${String(c[3])}`)).not.toContain(
			'b:done'
		);
		loads[1].resolve();
		await new Promise((r) => setTimeout(r, 150));
		expect(host.phase).toBe('singing');
		expect(session.plays).toBe(2);
	});

	it('a song whose sound fails while singing is skipped after a moment', async () => {
		const { host, session } = setup([item('a'), item('b', 'queued', 2)]);
		host.frame(0);
		loads[0].resolve();
		await flush();
		host.startNow();
		await flush();
		expect(host.phase).toBe('singing');
		session.state = 'error'; // the browser stopped playing it
		host.frame(1000);
		await flush();
		expect(host.phase).toBe('singing');
		host.frame(1000 + ERROR_GRACE_MS + 1);
		await flush();
		expect(host.phase).not.toBe('singing');
		expect(advance.mock.calls.map((c) => `${String(c[2])}:${String(c[3])}`)).toContain('a:skipped');
	});

	it('ending the party tells the server, with the TV token', async () => {
		const { host } = setup([item('a')]);
		await host.end();
		expect(endParty).toHaveBeenCalledWith('ABCD', 't');
	});

	it('starts a song once however many times play is asked for', async () => {
		const { host, session } = setup([item('a')]);
		host.frame();
		loads[0].resolve();
		await flush();
		host.startNow();
		host.startNow();
		await flush();
		await flush();
		expect(session.plays).toBe(1);
		expect(advance.mock.calls.filter((c) => c[3] === 'playing')).toHaveLength(1);
	});

	it('a failed load of a skipped song does not skip the next one', async () => {
		const { host } = setup([item('a'), item('b', 'queued', 2)]);
		host.frame();
		host.skip();
		await flush();
		host.frame();
		loads[0].reject(new Error('404'));
		await flush();
		expect(host.current?.id).toBe('b');
		expect(advance.mock.calls.filter((c) => c[2] === 'b')).toHaveLength(0);
	});
});
