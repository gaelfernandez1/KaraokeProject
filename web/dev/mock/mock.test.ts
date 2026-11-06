import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { Jobs } from './jobs.ts';
import { Library } from './library.ts';
import { hookOf } from '../../src/lib/poster/hook.ts';
import { Parties } from './party.ts';

function doc(id: string, extra: Record<string, unknown> = {}) {
	return {
		schema_version: '1.1.0',
		id,
		title: `Title ${id}`,
		artist: 'Artist',
		language: 'gl',
		duration: 30,
		audio: { instrumental: 'instrumental.wav', vocals: 'vocals.wav', loudness_lufs: -14 },
		video: null,
		cover: null,
		singers: [],
		lines: [],
		provenance: {
			lyrics_source: 'user',
			separation_model: null,
			asr_model: null,
			align_model: null,
			engine_version: '0',
			language_fallbacks: []
		},
		edited: false,
		...extra
	};
}

function libraryDir(): string {
	const dir = mkdtempSync(join(tmpdir(), 'mock-library-'));
	for (const [id, extra] of [
		['demo-sintetico', {}],
		['with-video', { video: { background: 'background.mp4' }, cover: 'cover.jpg' }]
	] as const) {
		mkdirSync(join(dir, id));
		writeFileSync(join(dir, id, 'karaoke.json'), JSON.stringify(doc(id, extra)));
	}
	mkdirSync(join(dir, 'not-a-package'));
	return dir;
}

describe('library', () => {
	it('lists the folders that hold a karaoke.json, with their summary', () => {
		const library = new Library([libraryDir()]);
		const songs = library.list();
		expect(songs.map((s) => s.id).sort()).toEqual(['demo-sintetico', 'with-video']);
		const video = songs.find((s) => s.id === 'with-video')!;
		expect(video.has_video).toBe(true);
		expect(video.cover).toBe('cover.jpg');
		expect(video.title).toBe('Title with-video');
		expect(library.find('nope')).toBeUndefined();
	});

	it('keeps edited documents in memory', () => {
		const library = new Library([libraryDir()]);
		const edited = { ...library.doc('demo-sintetico')!, title: 'Changed' };
		library.saveDoc('demo-sintetico', edited);
		expect(library.doc('demo-sintetico')!.title).toBe('Changed');
		expect(library.doc('demo-sintetico')!.edited).toBe(true);
		expect(new Library(library.dirs).doc('demo-sintetico')!.title).toBe('Title demo-sintetico');
	});
});

describe('jobs', () => {
	it('go through their stages and add the song to the library when done', () => {
		const library = new Library([libraryDir()]);
		let now = 0;
		const jobs = new Jobs(library, { seconds: 10, now: () => now });
		const seen: string[] = [];
		const job = jobs.create({ url: 'https://example.com/v', language: 'gl', title: 'Nova' });
		jobs.subscribe(job.id, (j) => seen.push(j.stage));
		for (now = 0; now <= 11_000; now += 500) jobs.tick();
		const done = jobs.get(job.id)!;
		expect(done.stage).toBe('done');
		expect(seen).toContain('download');
		expect(seen).toContain('transcribe');
		expect(new Set(seen).size).toBeGreaterThan(4);
		expect(library.list().some((s) => s.id === done.song_id && s.title === 'Nova')).toBe(true);
	});

	it('skip the transcription when the lyrics are given', () => {
		const library = new Library([libraryDir()]);
		let now = 0;
		const jobs = new Jobs(library, { seconds: 4, now: () => now });
		const job = jobs.create({ language: 'gl', lyrics: 'Ola', title: 'Con letra' });
		const seen: string[] = [];
		jobs.subscribe(job.id, (j) => seen.push(j.stage));
		for (now = 0; now <= 5000; now += 100) jobs.tick();
		expect(seen).not.toContain('transcribe');
		expect(seen).not.toContain('download');
	});

	it('can be cancelled', () => {
		const library = new Library([libraryDir()]);
		let now = 0;
		const jobs = new Jobs(library, { seconds: 4, now: () => now });
		const job = jobs.create({ language: 'gl', title: 'X' });
		jobs.cancel(job.id);
		now = 10_000;
		jobs.tick();
		expect(jobs.get(job.id)!.stage).toBe('cancelled');
	});
});

describe('parties', () => {
	it('end when the host says so, telling every phone, like the server', () => {
		const parties = new Parties(new Library([]));
		const { code, host_token } = parties.create();
		const events: string[] = [];
		parties.subscribe(code, null, (event) => events.push(event));
		const guest = parties.join(code, 'Ana')!;
		expect(parties.end(code, guest.token)).toBe(false);
		expect(parties.end(code, host_token)).toBe(true);
		expect(events.at(-1)).toBe('ended');
		expect(parties.get(code)).toBeUndefined();
	});

	const setup = () => {
		const library = new Library([libraryDir()]);
		const parties = new Parties(library);
		const { code, host_token } = parties.create();
		return { parties, code, host_token };
	};

	it('makes four-letter codes', () => {
		const { code } = setup();
		expect(code).toMatch(/^[BCDFGHJKLMNPQRSTVWXZ]{4}$/);
	});

	it('gives a guest who joins again with the same name the same identity', () => {
		const { parties, code } = setup();
		const first = parties.join(code, 'Ana')!;
		const again = parties.join(code, ' ana ')!;
		expect(again.guest.id).toBe(first.guest.id);
		expect(again.guest.color).toBe(first.guest.color);
	});

	it('hands out the singer colours in order and starts over after four', () => {
		const { parties, code } = setup();
		const colors = ['A', 'B', 'C', 'D', 'E'].map((n) => parties.join(code, n)!.guest.color);
		expect(colors).toEqual(['#FF8A3D', '#4FD1FF', '#FF6FB5', '#7CE38B', '#FF8A3D']);
	});

	it('bumps the version with each change and tells the subscribers', () => {
		const { parties, code } = setup();
		const states: number[] = [];
		parties.subscribe(code, null, (event, data) => {
			if (event === 'state') states.push((data as { version: number }).version);
		});
		const { token } = parties.join(code, 'Ana')!;
		const item = parties.enqueue(code, token, 'demo-sintetico')!;
		expect(item.title).toBe('Title demo-sintetico');
		parties.remove(code, token, item.id);
		expect(states.length).toBe(4);
		expect(states).toEqual([...states].sort((a, b) => a - b));
		expect(parties.get(code)!.queue).toEqual([]);
	});

	it('only lets a guest remove their own songs', () => {
		const { parties, code, host_token } = setup();
		const ana = parties.join(code, 'Ana')!;
		const brais = parties.join(code, 'Brais')!;
		const item = parties.enqueue(code, ana.token, 'demo-sintetico')!;
		expect(parties.remove(code, brais.token, item.id)).toBe(false);
		expect(parties.remove(code, host_token, item.id)).toBe(true);
	});

	it('lets the guest whose song is playing control it even when guests may not', () => {
		const { parties, code, host_token } = setup();
		const ana = parties.join(code, 'Ana')!;
		const brais = parties.join(code, 'Brais')!;
		const item = parties.enqueue(code, ana.token, 'demo-sintetico')!;
		parties.advance(code, host_token, item.id, 'playing');
		expect(parties.command(code, ana.token, { type: 'pause' })).toBe(true);
		expect(parties.command(code, brais.token, { type: 'pause' })).toBe(false);
	});

	it('passes guest commands to the host only when the host allows it', () => {
		const { parties, code, host_token } = setup();
		const commands: unknown[] = [];
		parties.subscribe(code, host_token, (event, data) => {
			if (event === 'command') commands.push(data);
		});
		const { token } = parties.join(code, 'Ana')!;
		expect(parties.command(code, token, { type: 'pause' })).toBe(false);
		parties.updateSettings(code, host_token, { guests_control: true });
		expect(parties.command(code, token, { type: 'pause' })).toBe(true);
		expect(commands).toEqual([{ type: 'pause' }]);
	});
});

describe('hookOf', () => {
	const line = (text: string, role = 'lead') => ({
		id: text,
		start: 0,
		end: 1,
		singer: null,
		role,
		words: text.split(' ').map((w) => ({ text: w, start: 0, end: 1, confidence: null, parts: [] }))
	});
	const withLines = (texts: ReturnType<typeof line>[]) =>
		({ ...doc('x'), lines: texts }) as unknown as Parameters<typeof hookOf>[0];

	it('picks the lead line sung most often, ignoring case and punctuation', () => {
		const lines = [
			line('Primeira liña do verso'),
			line('Quero bailar contigo,'),
			line('Outra cousa'),
			line('quero bailar contigo')
		];
		expect(hookOf(withLines(lines))).toBe('Quero bailar contigo');
	});

	it('falls back to the first line of three words or more', () => {
		expect(hookOf(withLines([line('Ai'), line('Ola mar de Vigo')]))).toBe('Ola mar de Vigo');
	});

	it('ignores backing vocals and copes with no lines', () => {
		expect(
			hookOf(
				withLines([
					line('eh eh eh', 'backing'),
					line('eh eh eh', 'backing'),
					line('Canta comigo agora')
				])
			)
		).toBe('Canta comigo agora');
		expect(hookOf(withLines([]))).toBeNull();
	});
});
