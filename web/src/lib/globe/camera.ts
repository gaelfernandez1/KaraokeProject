/*
 * The camera of the globe: an eye at a fixed distance looking at a sphere of radius 1, whose
 * picture is then slid and sized so the sphere sits wherever the page wants it (a frame in
 * pixels). Matrices are column-major, as WebGL takes them.
 */

/** How far the eye is from the centre of the globe, in radii. */
export const DISTANCE = 3.4;
/** The tangent of the angle between the centre of the globe and its edge, seen from the eye. */
const EDGE = 1 / Math.sqrt(DISTANCE ** 2 - 1);

export interface Frame {
	/** The viewport, in pixels. */
	width: number;
	height: number;
	/** Where the centre of the globe goes, and how big its silhouette is. */
	cx: number;
	cy: number;
	radius: number;
}

/** Pixels that one radius measures at the centre of the globe. */
export function pixelsPerUnit(radius: number): number {
	return (radius * Math.sqrt(DISTANCE ** 2 - 1)) / DISTANCE;
}

/** Projection times view, with the globe's centre at (cx, cy) and its edge `radius` away. */
export function viewProjection(frame: Frame, out: Float32Array): Float32Array {
	const focal = frame.radius / (frame.height / 2) / EDGE;
	const aspect = frame.width / frame.height;
	const near = 0.5;
	const far = 90;
	const a = (far + near) / (near - far);
	const b = (2 * far * near) / (near - far);
	const ox = frame.cx / (frame.width / 2) - 1;
	const oy = 1 - frame.cy / (frame.height / 2);
	out.fill(0);
	out[0] = focal / aspect;
	out[5] = focal;
	out[8] = -ox;
	out[9] = -oy;
	out[10] = a;
	out[11] = -1;
	out[12] = ox * DISTANCE;
	out[13] = oy * DISTANCE;
	out[14] = b - a * DISTANCE;
	out[15] = DISTANCE;
	return out;
}

/** Where a point of the world lands on the viewport, in pixels; `w` is its depth from the eye. */
export function project(
	matrix: Float32Array,
	x: number,
	y: number,
	z: number,
	frame: Frame
): { x: number; y: number; w: number } {
	const cx = matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12];
	const cy = matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13];
	const w = matrix[3] * x + matrix[7] * y + matrix[11] * z + matrix[15];
	return {
		x: ((cx / w + 1) / 2) * frame.width,
		y: ((1 - cy / w) / 2) * frame.height,
		w
	};
}

/**
 * The globe's own turn: `yaw` about its axis (east and west), then `tilt` tipping the north
 * away from the eye, as a map seen from the south. A 3 by 3 matrix.
 */
export function rotation(yaw: number, tilt: number, out: Float32Array): Float32Array {
	const cy = Math.cos(yaw);
	const sy = Math.sin(yaw);
	const ca = Math.cos(tilt);
	const sa = -Math.sin(tilt);
	// Adding zero turns a negative zero into a plain one.
	out[0] = cy;
	out[1] = sy * sa + 0;
	out[2] = -sy * ca + 0;
	out[3] = 0;
	out[4] = ca;
	out[5] = sa + 0;
	out[6] = sy;
	out[7] = -cy * sa + 0;
	out[8] = cy * ca;
	return out;
}

/** The point of the sphere at an angle east (`theta`) and north (`phi`) of Galicia's centre. */
export function direction(theta: number, phi: number): [number, number, number] {
	return [Math.cos(phi) * Math.sin(theta), Math.sin(phi), Math.cos(phi) * Math.cos(theta)];
}

/** A turn about any axis (normalised), as a 3 by 3 matrix. */
export function turn(
	ax: number,
	ay: number,
	az: number,
	angle: number,
	out: Float32Array
): Float32Array {
	const c = Math.cos(angle);
	const s = Math.sin(angle);
	const t = 1 - c;
	out[0] = t * ax * ax + c;
	out[1] = t * ax * ay + s * az;
	out[2] = t * ax * az - s * ay;
	out[3] = t * ax * ay - s * az;
	out[4] = t * ay * ay + c;
	out[5] = t * ay * az + s * ax;
	out[6] = t * ax * az + s * ay;
	out[7] = t * ay * az - s * ax;
	out[8] = t * az * az + c;
	return out;
}
