import { describe, expect, it } from 'vitest';
import {
	ApiError,
	createJob,
	deleteExport,
	downloadUrl,
	getDoc,
	getMe,
	listDevices,
	listExports,
	listSongs,
	mediaUrl,
	pairDevice,
	revokeDevice,
	retryJob,
	startPairing
} from './client';

interface Call {
	url: string;
	init?: RequestInit;
}

function fakeFetch(body: unknown, status = 200) {
	const calls: Call[] = [];
	const impl = async (url: string | URL | Request, init?: RequestInit) => {
		calls.push({ url: url instanceof Request ? url.url : url.toString(), init });
		return new Response(JSON.stringify(body), {
			status,
			headers: { 'Content-Type': 'application/json' }
		});
	};
	return { calls, impl: impl };
}

describe('api client', () => {
	it('lists the songs', async () => {
		const { calls, impl } = fakeFetch([{ id: 'a' }]);
		expect(await listSongs(impl)).toEqual([{ id: 'a' }]);
		expect(calls[0].url).toBe('/api/songs');
	});

	it('turns an error status into an ApiError that keeps the status', async () => {
		const { impl } = fakeFetch({ detail: 'nope' }, 404);
		const error = await listSongs(impl).catch((e: unknown) => e);
		expect(error).toBeInstanceOf(ApiError);
		expect((error as ApiError).status).toBe(404);
	});

	it('sends a new job as a form with the file and the options', async () => {
		const { calls, impl } = fakeFetch({ id: 'j1' });
		const file = new File(['x'], 'song.m4a', { type: 'audio/mp4' });
		await createJob({ file, language: 'gl', lyrics: 'Ola', lrclib: true }, impl);
		const { url, init } = calls[0];
		expect(url).toBe('/api/jobs');
		expect(init?.method).toBe('POST');
		const form = init?.body as FormData;
		expect(form.get('language')).toBe('gl');
		expect(form.get('lyrics')).toBe('Ola');
		expect(form.get('lrclib')).toBe('true');
		expect((form.get('file') as File).name).toBe('song.m4a');
		expect(form.has('url')).toBe(false);
	});

	it('lists and deletes the videos of a song', async () => {
		const { calls, impl } = fakeFetch([{ file: 'exports/a-16x9-clasico.mp4' }]);
		expect(await listExports('a b', impl)).toEqual([{ file: 'exports/a-16x9-clasico.mp4' }]);
		await deleteExport('a b', 'exports/a-16x9-clasico.mp4', impl);
		expect(calls.map((c) => `${c.init?.method ?? 'GET'} ${c.url}`)).toEqual([
			'GET /api/songs/a%20b/exports',
			'DELETE /api/songs/a%20b/exports/a-16x9-clasico.mp4'
		]);
	});

	it('asks the server to save a file under a readable name', () => {
		expect(downloadUrl('a b', 'exports/a.mp4', 'Uxía - Mar (karaoke).mp4')).toBe(
			'/media/a%20b/exports/a.mp4?download=1&name=Ux%C3%ADa%20-%20Mar%20(karaoke).mp4'
		);
	});

	it('escapes ids in media URLs', () => {
		expect(mediaUrl('a b', 'cover.jpg')).toBe('/media/a%20b/cover.jpg');
	});

	it('reads documents of schema 1.0.0 as lead lines', async () => {
		const doc = {
			schema_version: '1.0.0',
			id: 's',
			title: 'T',
			artist: null,
			language: 'gl',
			duration: 10,
			audio: { instrumental: 'i.m4a', vocals: null, loudness_lufs: null },
			video: null,
			cover: null,
			singers: [{ id: 's1', name: null, color: null }],
			lines: [
				{
					id: 'l1',
					start: 1,
					end: 2,
					singer: 's1',
					words: [{ text: 'Ola', start: 1, end: 2, confidence: null, parts: [] }]
				}
			],
			provenance: {
				lyrics_source: 'user',
				separation_model: null,
				asr_model: null,
				align_model: null,
				engine_version: '0',
				language_fallbacks: []
			},
			edited: false
		};
		const { calls, impl } = fakeFetch(doc);
		const loaded = await getDoc('s', impl);
		expect(calls[0].url).toBe('/media/s/karaoke.json');
		expect(loaded.lines[0].role).toBe('lead');
	});
});

describe('api client, server additions', () => {
	it('keeps the error code the server sends', async () => {
		const { impl } = fakeFetch(
			{ detail: 'Only a paired device can do this', code: 'not_owner' },
			403
		);
		const error = (await listSongs(impl).catch((e: unknown) => e)) as ApiError;
		expect(error.status).toBe(403);
		expect(error.code).toBe('not_owner');
	});

	it('has no code when the server sends none', async () => {
		const { impl } = fakeFetch({ detail: 'nope' }, 404);
		const error = (await listSongs(impl).catch((e: unknown) => e)) as ApiError;
		expect(error.code).toBeNull();
	});

	it('retries a job on the server', async () => {
		const { calls, impl } = fakeFetch({ id: 'j1', stage: 'queued' });
		await retryJob('j 1', impl);
		expect(calls[0].url).toBe('/api/jobs/j%201/retry');
		expect(calls[0].init?.method).toBe('POST');
	});

	it('pairs a device with a code', async () => {
		const { calls, impl } = fakeFetch({ id: 'd1', name: 'iPhone · Safari' });
		await pairDevice('BCDF GHJK', impl);
		expect(calls[0].url).toBe('/api/devices/pair');
		expect(JSON.parse(calls[0].init?.body as string)).toEqual({ code: 'BCDF GHJK' });
	});

	it('asks who it is, starts a pairing and manages devices', async () => {
		const { calls, impl } = fakeFetch({});
		await getMe(impl);
		await startPairing(impl);
		await listDevices(impl);
		await revokeDevice('d1', impl);
		expect(calls.map((c) => `${c.init?.method ?? 'GET'} ${c.url}`)).toEqual([
			'GET /api/me',
			'POST /api/devices/pairing',
			'GET /api/devices',
			'DELETE /api/devices/d1'
		]);
	});
});
