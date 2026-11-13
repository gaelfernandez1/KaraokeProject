/*
 * The night map of Galicia as the globe draws it: the raster that scripts/galicia_map.py writes
 * (heights, lights and provinces on a grid uniform in angle; see its docstring for the layout),
 * unpacked into one texture for the graphics card.
 */

export interface GaliciaMap {
	/** Cells along each side of the whole grid; the raster is a crop of it. */
	grid: number;
	left: number;
	top: number;
	width: number;
	height: number;
	/** 0 sea; otherwise 1 + 254 * sqrt(metres / the tallest height). Rows from the north. */
	heights: Uint8Array;
	/** 0 dark; otherwise the logarithm of the people in the cell, 1..255. */
	lights: Uint8Array;
	/** 0 none; otherwise which of the four provinces the cell is in. */
	provinces: Uint8Array;
}

export interface Atlas {
	size: number;
	/**
	 * Four bytes per cell of the whole grid, rows from the north: the stored height, the light
	 * there (the square root of its brightness, 0..255), how far the coast is (128 on it, more
	 * inland, less out at sea, `COAST_STEP` per cell) and whether two provinces meet there (0 or
	 * 255).
	 */
	data: Uint8Array;
}

/** How much brighter a place is for each step of its stored (logarithmic) level of people. */
const LIGHT_CONTRAST = 5.4;
/** What one cell of distance from the coast adds to (or takes from) the atlas's third byte. */
export const COAST_STEP = 6;

export function decodeMap(buffer: ArrayBuffer): GaliciaMap {
	const view = new DataView(buffer);
	const width = view.getUint16(6, true);
	const height = view.getUint16(8, true);
	const cells = width * height;
	return {
		grid: view.getUint16(0, true),
		left: view.getUint16(2, true),
		top: view.getUint16(4, true),
		width,
		height,
		heights: new Uint8Array(buffer, 10, cells),
		lights: new Uint8Array(buffer, 10 + cells, cells),
		provinces: new Uint8Array(buffer, 10 + 2 * cells, cells)
	};
}

/** Metres above the sea of a stored height. */
export function metres(stored: number, tallest: number): number {
	return stored === 0 ? 0 : ((stored - 1) / 254) ** 2 * tallest;
}

/** A fixed pseudo-random number in -0.5..0.5 for an index: the same thing, the same place. */
export function jitter(index: number): number {
	let h = Math.imul(index ^ 0x9e3779b9, 0x85ebca6b);
	h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
	h ^= h >>> 16;
	return (h >>> 0) / 0xffffffff - 0.5;
}

/**
 * For every cell, how many cells away the nearest cell of the other kind is (land for the sea,
 * sea for the land): two sweeps with the 3-4 chamfer, close enough to the true distance.
 */
function distances(land: Uint8Array, size: number, from: 0 | 1): Float32Array {
	const far = 1e6;
	const d = new Float32Array(size * size);
	for (let i = 0; i < d.length; i++) d[i] = land[i] === from ? 0 : far;
	const pass = (start: number, end: number, step: number) => {
		for (let row = start; row !== end; row += step) {
			for (let column = start; column !== end; column += step) {
				const i = row * size + column;
				let best = d[i];
				const beside = column - step;
				const before = row - step;
				if (beside >= 0 && beside < size) best = Math.min(best, d[i - step] + 3);
				if (before >= 0 && before < size) {
					best = Math.min(best, d[before * size + column] + 3);
					if (beside >= 0 && beside < size) best = Math.min(best, d[before * size + beside] + 4);
					const other = column + step;
					if (other >= 0 && other < size) best = Math.min(best, d[before * size + other] + 4);
				}
				d[i] = best;
			}
		}
	};
	pass(0, size, 1);
	pass(size - 1, -1, -1);
	for (let i = 0; i < d.length; i++) d[i] = d[i] / 3;
	return d;
}

/** The whole grid as one texture: relief, lights, the distance to the coast and the borders. */
export function buildAtlas(map: GaliciaMap): Atlas {
	const { grid, left, top, width, height, heights, lights, provinces } = map;
	const data = new Uint8Array(grid * grid * 4);
	const land = new Uint8Array(grid * grid);
	const province = (column: number, row: number) =>
		column < 0 || row < 0 || column >= width || row >= height
			? 0
			: (provinces[row * width + column] ?? 0);
	for (let row = 0; row < height; row++) {
		for (let column = 0; column < width; column++) {
			const cell = row * width + column;
			const out = (top + row) * grid + left + column;
			data[out * 4] = heights[cell] ?? 0;
			if ((heights[cell] ?? 0) > 0) land[out] = 1;
			const here = province(column, row);
			if (here === 0) continue;
			for (const [dx, dy] of [
				[1, 0],
				[-1, 0],
				[0, 1],
				[0, -1]
			] as const) {
				const there = province(column + dx, row + dy);
				if (there !== 0 && there !== here) data[out * 4 + 3] = 255;
			}
		}
	}
	// The stored light is the logarithm of the people: undone, a city outshines a village by
	// far. Each light then spills onto the cells around it, as light does seen from above (and
	// because a hexagon of people is bigger than a cell).
	const bright = new Float32Array(grid * grid);
	for (let row = 0; row < height; row++) {
		for (let column = 0; column < width; column++) {
			const level = (lights[row * width + column] ?? 0) / 255;
			if (level === 0) continue;
			const shine = Math.exp((level - 1) * LIGHT_CONTRAST);
			for (let dy = -1; dy <= 1; dy++) {
				for (let dx = -1; dx <= 1; dx++) {
					const x = left + column + dx;
					const y = top + row + dy;
					if (x < 0 || y < 0 || x >= grid || y >= grid) continue;
					bright[y * grid + x] += shine * (dx === 0 ? 2 : 1) * (dy === 0 ? 2 : 1) * 0.25;
				}
			}
		}
	}
	for (let cell = 0; cell < grid * grid; cell++) {
		data[cell * 4 + 1] = Math.round(255 * Math.sqrt(Math.min(1, bright[cell])));
	}

	const toSea = distances(land, grid, 0);
	const toLand = distances(land, grid, 1);
	for (let cell = 0; cell < grid * grid; cell++) {
		// Half a cell either side of the line between the last land and the first sea.
		const signed = land[cell] === 1 ? toSea[cell] - 0.5 : 0.5 - toLand[cell];
		data[cell * 4 + 2] = Math.min(255, Math.max(0, Math.round(128 + signed * COAST_STEP)));
	}
	return { size: grid, data };
}

/**
 * Where the beams of a lighthouse point within its turn, in radians. A group of flashes
 * ("Fl(4) 20s") is a lens with as many panels a couple of seconds apart, turning once a period.
 */
export function beamOffsets(flashes: number, period: number): number[] {
	const gap = Math.min(2.5, period / (flashes * 2));
	return Array.from({ length: flashes }, (_, i) => (i * 2 * Math.PI * gap) / period);
}

/** Downloads and unpacks the map; null where the browser cannot unzip it. */
export async function loadMap(url: string): Promise<GaliciaMap | null> {
	const response = await fetch(url);
	if (!response.ok) return null;
	const body = await response.arrayBuffer();
	const bytes = new Uint8Array(body, 0, 2);
	// The file is gzip; a server that labels it so has the browser unzip it already.
	if (bytes[0] !== 0x1f || bytes[1] !== 0x8b) return decodeMap(body);
	if (typeof DecompressionStream === 'undefined') return null;
	const stream = new Blob([body]).stream().pipeThrough(new DecompressionStream('gzip'));
	return decodeMap(await new Response(stream).arrayBuffer());
}
