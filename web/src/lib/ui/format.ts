/** 3:05, 12:40, 1:02:03. */
export function formatDuration(seconds: number): string {
	const total = Math.max(0, Math.floor(seconds));
	const h = Math.floor(total / 3600);
	const m = Math.floor((total % 3600) / 60);
	const s = String(total % 60).padStart(2, '0');
	return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`;
}

/** 1.2 GB, 340 MB, 12 kB, in the reader's locale. */
export function formatBytes(bytes: number, locale: string): string {
	const units = ['B', 'kB', 'MB', 'GB'];
	let value = bytes;
	let unit = 0;
	while (value >= 1000 && unit < units.length - 1) {
		value /= 1000;
		unit++;
	}
	const digits = value < 10 && unit > 0 ? 1 : 0;
	return `${new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value)} ${units[unit]}`;
}

/** A CSS-safe name for a view transition of a song. */
export function transitionName(id: string): string {
	return `song-${id.replace(/[^a-zA-Z0-9_-]/g, '_')}`;
}
