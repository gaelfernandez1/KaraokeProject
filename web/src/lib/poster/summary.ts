import type { SongSummary } from '#lib/api';
import type { KaraokeDoc } from '#lib/contracts';
import { hookOf } from './hook';

/** A song's poster data from its lyrics document, where the library summary is not at hand. */
export function summaryOf(id: string, doc: KaraokeDoc): SongSummary {
	return {
		id,
		title: doc.title,
		artist: doc.artist,
		language: doc.language,
		duration: doc.duration,
		cover: doc.cover ?? null,
		has_video: Boolean(doc.video?.background),
		created_at: '',
		edited: doc.edited,
		lyrics_source: doc.provenance.lyrics_source,
		hook: hookOf(doc)
	};
}
