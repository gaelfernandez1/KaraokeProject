import { describe, expect, it } from 'vitest';
import { nextFocus, type Rect } from './focus';

const box = (x: number, y: number, w = 100, h = 100): Rect => ({ x, y, w, h });

// A 3 × 2 grid of 100 px boxes, 20 px apart.
const GRID = [
	{ id: 'a', rect: box(0, 0) },
	{ id: 'b', rect: box(120, 0) },
	{ id: 'c', rect: box(240, 0) },
	{ id: 'd', rect: box(0, 120) },
	{ id: 'e', rect: box(120, 120) },
	{ id: 'f', rect: box(240, 120) }
];

describe('nextFocus', () => {
	it('moves to the neighbour in the direction pressed', () => {
		expect(nextFocus(GRID[0].rect, GRID, 'right')).toBe('b');
		expect(nextFocus(GRID[0].rect, GRID, 'down')).toBe('d');
		expect(nextFocus(GRID[4].rect, GRID, 'up')).toBe('b');
		expect(nextFocus(GRID[4].rect, GRID, 'left')).toBe('d');
	});

	it('prefers what is in line over what is a little closer but off to the side', () => {
		const items = [
			{ id: 'aligned', rect: box(300, 0) },
			{ id: 'diagonal', rect: box(150, 150) }
		];
		expect(nextFocus(box(0, 0), items, 'right')).toBe('aligned');
	});

	it('keeps to the row: right from a wide name goes to the menu, not to the field below', () => {
		// The top of the library on a TV: the app's name, the menu on its row, the search below.
		const name = box(250, 19, 384, 48);
		const items = [
			{ id: 'search', rect: box(242, 120, 480, 44) },
			{ id: 'songs', rect: box(705, 16, 80, 54) },
			{ id: 'party', rect: box(805, 16, 80, 54) }
		];
		expect(nextFocus(name, items, 'right')).toBe('songs');
	});

	it('still moves off the row when nothing is in line that way', () => {
		const items = [{ id: 'below-right', rect: box(300, 300) }];
		expect(nextFocus(box(0, 0), items, 'right')).toBe('below-right');
	});

	it('stops at the edges', () => {
		expect(nextFocus(GRID[2].rect, GRID, 'right')).toBeNull();
		expect(nextFocus(GRID[0].rect, GRID, 'up')).toBeNull();
	});
});
