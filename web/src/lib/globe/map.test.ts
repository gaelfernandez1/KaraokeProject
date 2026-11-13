import { describe, expect, it } from 'vitest';
import { beamOffsets, buildAtlas, decodeMap, metres } from './map';

/** A raster as the script writes it: a 4 by 3 crop at column 2, row 1 of an 8 by 8 grid. */
function raster(): ArrayBuffer {
	const heights = [
		[0, 0, 0, 0],
		[0, 128, 255, 0],
		[0, 1, 64, 0]
	];
	const lights = [
		[0, 0, 0, 0],
		[0, 40, 255, 0],
		[0, 0, 9, 3]
	];
	const provinces = [
		[0, 0, 0, 0],
		[0, 1, 2, 0],
		[0, 1, 2, 0]
	];
	const bytes = new Uint8Array(10 + 36);
	const view = new DataView(bytes.buffer);
	[8, 2, 1, 4, 3].forEach((value, i) => view.setUint16(i * 2, value, true));
	bytes.set(heights.flat(), 10);
	bytes.set(lights.flat(), 22);
	bytes.set(provinces.flat(), 34);
	return bytes.buffer;
}

describe('decodeMap', () => {
	it('reads the header and the three layers', () => {
		const map = decodeMap(raster());
		expect(map).toMatchObject({ grid: 8, left: 2, top: 1, width: 4, height: 3 });
		expect(Array.from(map.heights.slice(4, 8))).toEqual([0, 128, 255, 0]);
		expect(Array.from(map.lights.slice(8, 12))).toEqual([0, 0, 9, 3]);
		expect(Array.from(map.provinces.slice(4, 8))).toEqual([0, 1, 2, 0]);
	});

	it('turns a stored height back into metres', () => {
		expect(metres(0, 2200)).toBe(0);
		expect(metres(1, 2200)).toBe(0);
		expect(metres(255, 2200)).toBeCloseTo(2200);
		expect(metres(128, 2200)).toBeCloseTo(2200 * (127 / 254) ** 2);
	});
});

describe('buildAtlas', () => {
	const atlas = buildAtlas(decodeMap(raster()));
	const at = (column: number, row: number) =>
		Array.from(atlas.data.slice((row * 8 + column) * 4, (row * 8 + column) * 4 + 4));

	it('covers the whole grid, four bytes a cell', () => {
		expect(atlas.size).toBe(8);
		expect(atlas.data.length).toBe(8 * 8 * 4);
	});

	it('keeps each height in its cell', () => {
		// The tallest cell: column 2 + 2, row 1 + 1 of the grid.
		expect(at(4, 2)[0]).toBe(255);
		expect(at(3, 2)[0]).toBe(128);
		expect(at(0, 0)[0]).toBe(0);
	});

	it('turns the people of each cell into light that spills a little around', () => {
		// The most populated cell shines the most; a village beside it far less; far away, dark.
		expect(at(4, 2)[1]).toBeGreaterThan(200);
		expect(at(3, 2)[1]).toBeLessThan(at(4, 2)[1]);
		expect(at(3, 2)[1]).toBeGreaterThan(0);
		// The cell above the brightest has nobody, but the glow reaches it.
		expect(at(4, 1)[1]).toBeGreaterThan(0);
		expect(at(0, 7)[1]).toBe(0);
	});

	it('says how far the coast is: above the middle on land, below it at sea, less further out', () => {
		expect(at(3, 2)[2]).toBeGreaterThan(128);
		expect(at(2, 2)[2]).toBeLessThan(128);
		expect(at(0, 2)[2]).toBeLessThan(at(2, 2)[2]);
		expect(at(0, 7)[2]).toBeLessThan(at(0, 2)[2]);
	});

	it('marks where two provinces meet', () => {
		expect(at(3, 2)[3]).toBe(255);
		expect(at(4, 3)[3]).toBe(255);
		expect(at(0, 0)[3]).toBe(0);
	});
});

describe('beamOffsets', () => {
	it('gives a single flash one beam', () => {
		expect(beamOffsets(1, 5)).toEqual([0]);
	});

	it('spreads a group of flashes a couple of seconds apart', () => {
		const offsets = beamOffsets(4, 20);
		expect(offsets).toHaveLength(4);
		// 2.5 s apart in a turn of 20 s: an eighth of a turn.
		expect(offsets[1] - offsets[0]).toBeCloseTo(Math.PI / 4);
	});

	it('never lets a group take more than half the turn', () => {
		const offsets = beamOffsets(2, 3);
		expect(offsets[1] - offsets[0]).toBeCloseTo(Math.PI / 2);
	});
});
