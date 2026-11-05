import { DEFAULT_THEME, THEMES } from '#lib/lyrics';

/** What this device remembers between visits. */
export interface Settings {
	/** Lyrics theme id. */
	theme: string;
	/** Guide vocals when a song starts, 0–1. */
	vocals: number;
	/** This device's sound delay beyond what the browser reports, in ms (calibration). */
	latencyMs: number;
}

export const DEFAULT_SETTINGS: Settings = { theme: DEFAULT_THEME, vocals: 0.15, latencyMs: 0 };

const KEY = 'foliada.settings';

type Store = Pick<Storage, 'getItem' | 'setItem'>;

export function loadSettings(storage: Store | null): Settings {
	let raw: unknown;
	try {
		raw = JSON.parse(storage?.getItem(KEY) ?? 'null');
	} catch {
		return { ...DEFAULT_SETTINGS };
	}
	const stored = (typeof raw === 'object' && raw !== null ? raw : {}) as Partial<
		Record<keyof Settings, unknown>
	>;
	const number = (value: unknown, fallback: number) =>
		typeof value === 'number' && Number.isFinite(value) ? value : fallback;
	return {
		theme:
			typeof stored.theme === 'string' && stored.theme in THEMES
				? stored.theme
				: DEFAULT_SETTINGS.theme,
		vocals: Math.min(1, Math.max(0, number(stored.vocals, DEFAULT_SETTINGS.vocals))),
		latencyMs: Math.round(Math.min(1000, Math.max(-500, number(stored.latencyMs, 0))))
	};
}

export function saveSettings(settings: Settings, storage: Store | null): void {
	try {
		storage?.setItem(KEY, JSON.stringify(settings));
	} catch {
		// Private windows can refuse storage; the settings still hold for this visit.
	}
}
