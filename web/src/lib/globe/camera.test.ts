import { describe, expect, it } from 'vitest';
import { DISTANCE, direction, pixelsPerUnit, project, rotation, viewProjection } from './camera';

const frame = { width: 1440, height: 900, cx: 1000, cy: 430, radius: 380 };

describe('viewProjection', () => {
	const matrix = viewProjection(frame, new Float32Array(16));

	it('puts the centre of the globe where the frame says', () => {
		const centre = project(matrix, 0, 0, 0, frame);
		expect(centre.x).toBeCloseTo(1000, 3);
		expect(centre.y).toBeCloseTo(430, 3);
	});

	it('makes the silhouette of the sphere as big as the frame says', () => {
		// Where a line from the eye touches the sphere.
		const rho = Math.sqrt(1 - 1 / DISTANCE ** 2);
		const edge = project(matrix, rho, 0, 1 / DISTANCE, frame);
		expect(edge.x - 1000).toBeCloseTo(380, 2);
		const top = project(matrix, 0, rho, 1 / DISTANCE, frame);
		expect(430 - top.y).toBeCloseTo(380, 2);
	});

	it('says how many pixels a unit is at the centre of the globe', () => {
		const side = project(matrix, 0.01, 0, 0, frame);
		expect((side.x - 1000) / 0.01).toBeCloseTo(pixelsPerUnit(380), 1);
	});
});

describe('rotation', () => {
	it('leaves the globe as it is with no turn and no tilt', () => {
		expect(Array.from(rotation(0, 0, new Float32Array(9)))).toEqual([1, 0, 0, 0, 1, 0, 0, 0, 1]);
	});

	it('tilts the north away from the eye', () => {
		const m = rotation(0, 0.3, new Float32Array(9));
		// The north pole (0, 1, 0), column-major.
		expect(m[5]).toBeLessThan(0);
	});

	it('turns the east towards the eye', () => {
		const m = rotation(0.3, 0, new Float32Array(9));
		// The east (1, 0, 0) gains depth towards the camera's side... or loses it: it must move.
		expect(Math.abs(m[2])).toBeGreaterThan(0.2);
	});
});

describe('direction', () => {
	it('puts the centre of Galicia at the front and the north up', () => {
		expect(direction(0, 0)).toEqual([0, 0, 1]);
		const [x, y, z] = direction(0, 0.5);
		expect(x).toBeCloseTo(0);
		expect(y).toBeCloseTo(Math.sin(0.5));
		expect(z).toBeCloseTo(Math.cos(0.5));
		expect(direction(0.5, 0)[0]).toBeCloseTo(Math.sin(0.5));
	});
});
