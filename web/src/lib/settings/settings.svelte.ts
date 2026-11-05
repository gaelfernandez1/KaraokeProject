import { loadSettings, saveSettings, type Settings } from './store';

function storage(): Storage | null {
	try {
		return localStorage;
	} catch {
		return null;
	}
}

/** This device's settings, shared by every screen; change them with `updateSettings`. */
export const settings: Settings = $state(loadSettings(storage()));

export function updateSettings(change: Partial<Settings>): void {
	Object.assign(settings, change);
	saveSettings({ ...settings }, storage());
}
