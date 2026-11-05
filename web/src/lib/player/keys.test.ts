import { describe, expect, it } from 'vitest';
import { playerAction } from './keys';

const key = (k: string, shiftKey = false) => playerAction({ key: k, shiftKey });

describe('playerAction', () => {
	it('maps the keys of a video player', () => {
		expect(key(' ')).toBe('toggle');
		expect(key('k')).toBe('toggle');
		expect(key('K')).toBe('toggle');
		expect(key('MediaPlayPause')).toBe('toggle');
		expect(key('ArrowLeft')).toBe('back5');
		expect(key('ArrowRight')).toBe('forward5');
		expect(key('ArrowLeft', true)).toBe('prevLine');
		expect(key('ArrowRight', true)).toBe('nextLine');
		expect(key('MediaTrackPrevious')).toBe('prevLine');
		expect(key('MediaTrackNext')).toBe('nextLine');
		expect(key('ArrowDown')).toBe('vocalsDown');
		expect(key('ArrowUp')).toBe('vocalsUp');
		expect(key('-')).toBe('pitchDown');
		expect(key('+')).toBe('pitchUp');
		expect(key('=')).toBe('pitchUp');
		expect(key('f')).toBe('fullscreen');
		expect(key('Escape')).toBe('exit');
	});

	it('ignores everything else', () => {
		expect(key('a')).toBeNull();
		expect(key('Enter')).toBeNull();
	});
});
