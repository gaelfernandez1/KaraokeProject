import { describe, expect, it } from 'vitest';
import type { SongSummary } from '#lib/api';
import { filterSongs, languagesOf } from './filter';

const song = (
	id: string,
	title: string,
	artist: string | null,
	language: string,
	created: string
): SongSummary => ({
	id,
	title,
	artist,
	language,
	duration: 200,
	cover: null,
	has_video: false,
	created_at: created,
	edited: false,
	lyrics_source: 'user',
	hook: null
});

const SONGS = [
	song('a', 'Ó pé da Ponte Vella', 'Fillas de Cassandra', 'gl', '2026-10-01T10:00:00Z'),
	song('b', 'La Favorita', '9Louro', 'gl', '2026-10-03T10:00:00Z'),
	song('c', 'Feel', 'Cortez', 'en', '2026-10-02T10:00:00Z')
];

describe('filterSongs', () => {
	it('lists everything, newest first, with no filters', () => {
		expect(
			filterSongs(SONGS, { query: '', language: 'all', saved: null }).map((s) => s.id)
		).toEqual(['b', 'c', 'a']);
	});

	it('matches title or artist ignoring accents and case', () => {
		const ids = (query: string) =>
			filterSongs(SONGS, { query, language: 'all', saved: null }).map((s) => s.id);
		expect(ids('ponte vella')).toEqual(['a']);
		expect(ids('ó pe')).toEqual(['a']);
		expect(ids('O PÉ')).toEqual(['a']);
		expect(ids('cassandra')).toEqual(['a']);
		expect(ids('9louro')).toEqual(['b']);
		expect(ids('nada')).toEqual([]);
	});

	it('filters by language and by saved songs', () => {
		expect(filterSongs(SONGS, { query: '', language: 'en', saved: null }).map((s) => s.id)).toEqual(
			['c']
		);
		expect(
			filterSongs(SONGS, { query: '', language: 'all', saved: new Set(['a']) }).map((s) => s.id)
		).toEqual(['a']);
	});
});

describe('languagesOf', () => {
	it('lists the languages present, Galician first, then by number of songs', () => {
		expect(
			languagesOf([
				...SONGS,
				song('d', 'X', null, 'en', '2026-01-01T00:00:00Z'),
				song('e', 'Y', null, 'es', '2026-01-01T00:00:00Z')
			])
		).toEqual(['gl', 'en', 'es']);
	});
});
