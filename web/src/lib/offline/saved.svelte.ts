import type { SongSummary } from '#lib/api';
import { offlineAvailable, removeSong, saveSong, savedSongs, type SavedSong } from './store';

/**
 * The songs saved on this device, for the screens to show and change. One instance for the
 * whole app, so the library, the player and the settings agree.
 */
class Saved {
	list = $state.raw<SavedSong[]>([]);
	/** Song id → save progress (0–1) while it downloads. */
	progress = $state<Record<string, number>>({});
	readonly available: boolean;

	constructor() {
		this.available = typeof window !== 'undefined' && offlineAvailable();
		if (this.available) this.list = savedSongs();
	}

	get ids(): Set<string> {
		return new Set(this.list.map((song) => song.id));
	}

	has(id: string): boolean {
		return this.list.some((song) => song.id === id);
	}

	/** Downloads a song for offline use; resolves with why it failed, or null. */
	async save(song: SongSummary): Promise<'insecure' | 'quota' | 'network' | null> {
		this.progress = { ...this.progress, [song.id]: 0 };
		const result = await saveSong(song, (fraction) => {
			this.progress = { ...this.progress, [song.id]: fraction };
		});
		const progress = { ...this.progress };
		delete progress[song.id];
		this.progress = progress;
		this.list = savedSongs();
		return result.ok ? null : result.reason;
	}

	async remove(id: string): Promise<void> {
		await removeSong(id);
		this.list = savedSongs();
	}
}

export const saved = new Saved();
