import { describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS, loadSettings, saveSettings } from './store';

function memory(initial: Record<string, string> = {}) {
	const data = new Map(Object.entries(initial));
	return {
		getItem: (key: string) => data.get(key) ?? null,
		setItem: (key: string, value: string) => void data.set(key, value)
	};
}

describe('settings', () => {
	it('start from the defaults without storage', () => {
		expect(loadSettings(null)).toEqual(DEFAULT_SETTINGS);
		expect(DEFAULT_SETTINGS.theme).toBe('clasico');
	});

	it('round-trip through storage', () => {
		const storage = memory();
		saveSettings({ theme: 'moderno', vocals: 0.4, latencyMs: 120 }, storage);
		expect(loadSettings(storage)).toEqual({ theme: 'moderno', vocals: 0.4, latencyMs: 120 });
	});

	it('survive corrupt or out-of-range values', () => {
		expect(loadSettings(memory({ 'foliada.settings': '{oops' }))).toEqual(DEFAULT_SETTINGS);
		const odd = loadSettings(
			memory({ 'foliada.settings': JSON.stringify({ theme: 'nope', vocals: 7, latencyMs: 'x' }) })
		);
		expect(odd).toEqual({ ...DEFAULT_SETTINGS, vocals: 1 });
	});

	it('survive storage that throws', () => {
		const broken = {
			getItem: () => {
				throw new Error('denied');
			},
			setItem: () => {
				throw new Error('denied');
			}
		};
		expect(loadSettings(broken)).toEqual(DEFAULT_SETTINGS);
		expect(() => saveSettings(DEFAULT_SETTINGS, broken)).not.toThrow();
	});
});
