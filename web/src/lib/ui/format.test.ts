import { describe, expect, it } from 'vitest';
import { formatBytes, formatCount, formatDuration, transitionName } from './format';

describe('format', () => {
	it('writes durations like a player does', () => {
		expect(formatDuration(0)).toBe('0:00');
		expect(formatDuration(185.7)).toBe('3:05');
		expect(formatDuration(3723)).toBe('1:02:03');
		expect(formatDuration(-4)).toBe('0:00');
	});

	it('writes sizes with the locale decimal mark', () => {
		expect(formatBytes(1_234_000, 'gl')).toBe('1,2 MB');
		expect(formatBytes(1_234_000, 'en')).toBe('1.2 MB');
		expect(formatBytes(512, 'gl')).toBe('512 B');
	});

	it('groups big counts in threes with a narrow space, the same in every language', () => {
		expect(formatCount(2762451)).toBe('2\u202f762\u202f451');
		expect(formatCount(23410)).toBe('23\u202f410');
		expect(formatCount(999)).toBe('999');
	});

	it('makes transition names CSS can use', () => {
		expect(transitionName('ó pé/1')).toBe('song-__p__1');
	});
});
