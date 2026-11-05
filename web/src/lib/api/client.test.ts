import { describe, expect, it } from 'vitest';
import { ApiError, createJob, getDoc, listSongs, mediaUrl } from './client';

interface Call {
	url: string;
	init?: RequestInit;
}

function fakeFetch(body: unknown, status = 200) {
	const calls: Call[] = [];
	const impl = async (url: string | URL | Request, init?: RequestInit) => {
		calls.push({ url: String(url), init });
		return new Response(JSON.stringify(body), {
			status,
			headers: { 'Content-Type': 'application/json' }
		});
	};
	return { calls, impl: impl as typeof fetch };
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
