import { describe, expect, it } from 'vitest';
import { ApiError } from '#lib/api/client.js';
import {
	advance,
	createParty,
	enqueue,
	getParty,
	joinParty,
	partyEventsUrl,
	promote,
	publishPlayback,
	rememberGuest,
	rememberHost,
	rememberedGuest,
	rememberedHost,
	removeItem,
	sendCommand,
	updateSettings
} from './client';
import type { Joined, Playback } from './types';

interface Call {
	url: string;
	method: string;
	headers: Headers;
	body: unknown;
}

function fakeFetch(body: unknown = null, status = 200) {
	const calls: Call[] = [];
	const impl = async (url: string | URL | Request, init: RequestInit = {}) => {
		calls.push({
			url: String(url),
			method: init.method ?? 'GET',
			headers: new Headers(init.headers),
			body: typeof init.body === 'string' ? JSON.parse(init.body) : init.body
		});
		if (status === 204) return new Response(null, { status });
		return new Response(JSON.stringify(body), {
			status,
			headers: { 'Content-Type': 'application/json' }
		});
	};
	return { calls, impl: impl as typeof fetch };
}

function memory() {
	const data = new Map<string, string>();
	return {
		data,
		getItem: (key: string) => data.get(key) ?? null,
		setItem: (key: string, value: string) => void data.set(key, value)
	};
}

const broken = {
	getItem: (): string | null => {
		throw new Error('denied');
	},
	setItem: () => {
		throw new Error('denied');
	}
};

const JOINED: Joined = {
	guest: { id: 'g1', name: 'Uxía', color: '#FFC531', joined_at: 5 },
	token: 'guest-token'
};

describe('party client', () => {
	it('creates a party', async () => {
		const { calls, impl } = fakeFetch({ code: 'BCDF', host_token: 'h' }, 201);
		expect(await createParty(impl)).toEqual({ code: 'BCDF', host_token: 'h' });
		expect(calls[0]).toMatchObject({ url: '/api/parties', method: 'POST' });
	});

	it('reads a party by its code, upper-cased and escaped', async () => {
		const { calls, impl } = fakeFetch({ code: 'BCDF', version: 3 });
		expect(await getParty('bcdf', impl)).toEqual({ code: 'BCDF', version: 3 });
		expect(calls[0]).toMatchObject({ url: '/api/parties/BCDF', method: 'GET' });
		await getParty('a/b c', impl);
		expect(calls[1].url).toBe('/api/parties/A%2FB%20C');
	});

	it('joins with a name and no token', async () => {
		const { calls, impl } = fakeFetch(JOINED, 201);
		expect(await joinParty('bcdf', 'Uxía', impl)).toEqual(JOINED);
		expect(calls[0]).toMatchObject({
			url: '/api/parties/BCDF/guests',
			method: 'POST',
			body: { name: 'Uxía' }
		});
		expect(calls[0].headers.get('Content-Type')).toBe('application/json');
		expect(calls[0].headers.has('Authorization')).toBe(false);
	});

	it('requests a song with the guest token', async () => {
		const { calls, impl } = fakeFetch({ id: 'q1' }, 201);
		expect(await enqueue('bcdf', 'tok', 'song-1', impl)).toEqual({ id: 'q1' });
		expect(calls[0]).toMatchObject({
			url: '/api/parties/BCDF/queue',
			method: 'POST',
			body: { song_id: 'song-1' }
		});
		expect(calls[0].headers.get('Authorization')).toBe('Bearer tok');
		expect(calls[0].headers.get('Content-Type')).toBe('application/json');
	});

	it('removes and promotes queue items', async () => {
		const { calls, impl } = fakeFetch(null, 204);
		expect(await removeItem('bcdf', 'tok', 'q 1', impl)).toBeUndefined();
		await promote('bcdf', 'host', 'q2', impl);
		expect(calls[0]).toMatchObject({ url: '/api/parties/BCDF/queue/q%201', method: 'DELETE' });
		expect(calls[0].headers.get('Authorization')).toBe('Bearer tok');
		expect(calls[1]).toMatchObject({ url: '/api/parties/BCDF/promote/q2', method: 'POST' });
		expect(calls[1].headers.get('Authorization')).toBe('Bearer host');
	});

	it('sends what the host and the remotes change', async () => {
		const { calls, impl } = fakeFetch(null, 204);
		const playback: Playback = {
			item_id: 'q1',
			playing: true,
			position: 12.5,
			at: 1000,
			vocals: 0.2,
			pitch: -1
		};
		await advance('bcdf', 'host', 'q1', 'playing', impl);
		await sendCommand('bcdf', 'tok', { type: 'vocals', value: 0.5 }, impl);
		await publishPlayback('bcdf', 'host', playback, impl);
		await updateSettings('bcdf', 'host', { guests_control: true }, impl);
		expect(calls.map(({ method, url, body }) => ({ method, url, body }))).toEqual([
			{
				method: 'PUT',
				url: '/api/parties/BCDF/advance',
				body: { item_id: 'q1', state: 'playing' }
			},
			{
				method: 'POST',
				url: '/api/parties/BCDF/commands',
				body: { type: 'vocals', value: 0.5 }
			},
			{ method: 'PUT', url: '/api/parties/BCDF/playback', body: playback },
			{ method: 'PUT', url: '/api/parties/BCDF/settings', body: { guests_control: true } }
		]);
		expect(calls.map((c) => c.headers.get('Authorization'))).toEqual([
			'Bearer host',
			'Bearer tok',
			'Bearer host',
			'Bearer host'
		]);
	});

	it('turns an error status into an ApiError that keeps the status', async () => {
		const missing = await getParty('nope', fakeFetch({ detail: 'Not found' }, 404).impl).catch(
			(e: unknown) => e
		);
		expect(missing).toBeInstanceOf(ApiError);
		expect((missing as ApiError).status).toBe(404);
		const refused = await sendCommand(
			'bcdf',
			'tok',
			{ type: 'skip' },
			fakeFetch({ detail: 'Not allowed' }, 403).impl
		).catch((e: unknown) => e);
		expect((refused as ApiError).status).toBe(403);
		expect((refused as ApiError).message).toBe('Not allowed');
	});

	it('passes the token in the events URL, since EventSource cannot send headers', () => {
		expect(partyEventsUrl('bcdf', 'a+b/c')).toBe('/api/parties/BCDF/events?token=a%2Bb%2Fc');
	});
});

describe('remembered credentials', () => {
	it('round-trip a guest by party code', () => {
		const storage = memory();
		rememberGuest('bcdf', JOINED, storage);
		expect([...storage.data.keys()]).toEqual(['foliada.party.BCDF']);
		expect(rememberedGuest('BCDF', storage)).toEqual(JOINED);
		expect(rememberedGuest('XZXZ', storage)).toBeNull();
	});

	it('round-trip the host token by party code', () => {
		const storage = memory();
		rememberHost({ code: 'bcdf', host_token: 'h' }, storage);
		expect([...storage.data.keys()]).toEqual(['foliada.party-host.BCDF']);
		expect(rememberedHost('bcdf', storage)).toEqual({ code: 'BCDF', host_token: 'h' });
		expect(rememberedHost('XZXZ', storage)).toBeNull();
	});

	it('ignore corrupt entries', () => {
		const storage = memory();
		storage.setItem('foliada.party.BCDF', '{oops');
		storage.setItem('foliada.party-host.BCDF', JSON.stringify({ code: 'BCDF' }));
		expect(rememberedGuest('BCDF', storage)).toBeNull();
		expect(rememberedHost('BCDF', storage)).toBeNull();
		storage.setItem('foliada.party.BCDF', JSON.stringify({ token: 't', guest: null }));
		expect(rememberedGuest('BCDF', storage)).toBeNull();
	});

	it('survive storage that throws or is missing', () => {
		expect(() => rememberGuest('BCDF', JOINED, broken)).not.toThrow();
		expect(() => rememberHost({ code: 'BCDF', host_token: 'h' }, broken)).not.toThrow();
		expect(rememberedGuest('BCDF', broken)).toBeNull();
		expect(rememberedHost('BCDF', broken)).toBeNull();
		expect(() => rememberGuest('BCDF', JOINED, null)).not.toThrow();
		expect(rememberedGuest('BCDF', null)).toBeNull();
	});
});
