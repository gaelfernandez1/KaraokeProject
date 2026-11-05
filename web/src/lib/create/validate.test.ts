import { describe, expect, it } from 'vitest';
import { MAX_BYTES, guessTitle, validateCreate, type CreateForm } from './validate';

const file = (name: string, type = '', size = 10) => {
	const f = new File(['x'], name, { type });
	Object.defineProperty(f, 'size', { value: size });
	return f;
};

const form = (change: Partial<CreateForm> = {}): CreateForm => ({
	file: null,
	url: '',
	language: 'gl',
	lyrics: '',
	lrclib: false,
	title: '',
	artist: '',
	...change
});

describe('validateCreate', () => {
	it('needs exactly one source', () => {
		expect(validateCreate(form())).toEqual({ ok: false, error: 'errorSourceMissing' });
		expect(
			validateCreate(form({ url: 'https://youtu.be/x', file: file('a.mp3', 'audio/mpeg') }))
		).toEqual({ ok: false, error: 'errorSourceBoth' });
	});

	it('accepts only web links', () => {
		expect(validateCreate(form({ url: 'ftp://x/y' }))).toEqual({ ok: false, error: 'errorUrl' });
		expect(validateCreate(form({ url: 'youtube' }))).toEqual({ ok: false, error: 'errorUrl' });
		const ok = validateCreate(form({ url: '  https://youtu.be/abc  ' }));
		expect(ok.ok && ok.value.url).toBe('https://youtu.be/abc');
	});

	it('accepts audio and video files by type or by extension, up to 2 GB', () => {
		expect(validateCreate(form({ file: file('song.txt', 'text/plain') }))).toEqual({
			ok: false,
			error: 'errorFile'
		});
		expect(validateCreate(form({ file: file('song.opus') })).ok).toBe(true);
		expect(validateCreate(form({ file: file('clip', 'video/mp4') })).ok).toBe(true);
		expect(validateCreate(form({ file: file('big.mkv', '', MAX_BYTES + 1) }))).toEqual({
			ok: false,
			error: 'errorFileSize'
		});
	});

	it('leaves out empty lyrics, and LRCLIB when lyrics are given', () => {
		const empty = validateCreate(form({ url: 'https://x.y/z', lyrics: '  \n ', lrclib: true }));
		expect(empty.ok && empty.value.lyrics).toBeUndefined();
		expect(empty.ok && empty.value.lrclib).toBe(true);
		const given = validateCreate(form({ url: 'https://x.y/z', lyrics: 'Ola\n', lrclib: true }));
		expect(given.ok && given.value.lyrics).toBe('Ola');
		expect(given.ok && given.value.lrclib).toBe(false);
	});

	it('passes title and artist only when written', () => {
		const result = validateCreate(
			form({ url: 'https://x.y/z', title: ' La Favorita ', artist: ' ' })
		);
		expect(result.ok && result.value.title).toBe('La Favorita');
		expect(result.ok && result.value.artist).toBeUndefined();
	});
});

describe('guessTitle', () => {
	it('reads "Artist - Title" file names', () => {
		expect(guessTitle('9Louro - La Favorita.m4a')).toEqual({
			title: 'La Favorita',
			artist: '9Louro'
		});
		expect(guessTitle('Fillas de Cassandra – Ó pé da Ponte (Official Video).mp4')).toEqual({
			title: 'Ó pé da Ponte',
			artist: 'Fillas de Cassandra'
		});
	});

	it('uses the whole name otherwise, tidied', () => {
		expect(guessTitle('mar_de_vigo.wav')).toEqual({ title: 'mar de vigo', artist: null });
	});
});
