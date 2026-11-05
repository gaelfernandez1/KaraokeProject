import type { SongSummary } from '#lib/api';

export interface LibraryFilter {
	query: string;
	/** A language code, or 'all'. */
	language: string;
	/** Only these ids (the songs saved on this device), or null for all. */
	saved: ReadonlySet<string> | null;
}

/** Lower case without accents, so "o pe" finds "Ó pé". */
export function fold(text: string): string {
	return text.normalize('NFD').replace(/\p{M}/gu, '').toLocaleLowerCase('gl');
}

/** Songs that match every filter, newest first. */
export function filterSongs(songs: readonly SongSummary[], filter: LibraryFilter): SongSummary[] {
	const terms = fold(filter.query).split(/\s+/).filter(Boolean);
	return songs
		.filter((song) => {
			if (filter.language !== 'all' && song.language !== filter.language) return false;
			if (filter.saved && !filter.saved.has(song.id)) return false;
			const haystack = fold(`${song.title} ${song.artist ?? ''}`);
			return terms.every((term) => haystack.includes(term));
		})
		.sort((a, b) => b.created_at.localeCompare(a.created_at));
}

/** The languages of the library: Galician first, then the most common. */
export function languagesOf(songs: readonly SongSummary[]): string[] {
	const counts = new Map<string, number>();
	for (const song of songs) counts.set(song.language, (counts.get(song.language) ?? 0) + 1);
	return [...counts.keys()].sort((a, b) => {
		if (a === 'gl') return -1;
		if (b === 'gl') return 1;
		return (counts.get(b) ?? 0) - (counts.get(a) ?? 0) || a.localeCompare(b);
	});
}
