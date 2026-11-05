import { describe, expect, it } from 'vitest';
import { peaks } from './peaks';

const RATE = 16000;

function sine(seconds: number, amplitude: number, hz = 220): Float32Array {
	return Float32Array.from(
		{ length: seconds * RATE },
		(_, i) => Math.sin((2 * Math.PI * hz * i) / RATE) * amplitude
	);
}

describe('peaks', () => {
	it('finds the amplitude of a sine in every column', () => {
		const columns = peaks(sine(2, 0.5), RATE, 0.5, 1.5, 100);
		expect(columns).toHaveLength(100);
		for (const peak of columns) expect(peak).toBeCloseTo(0.5, 2);
	});

	it('is zero for silence', () => {
		expect([...peaks(new Float32Array(RATE), RATE, 0, 1, 40)]).toEqual(Array(40).fill(0));
	});

	it('is zero outside the audio', () => {
		expect([...peaks(sine(1, 0.5), RATE, 2, 3, 10)]).toEqual(Array(10).fill(0));
		const straddling = peaks(sine(1, 0.5), RATE, 0.5, 1.5, 10);
		expect(straddling[4]).toBeCloseTo(0.5, 2);
		expect([...straddling.slice(5)]).toEqual(Array(5).fill(0));
		expect(peaks(sine(1, 0.5), RATE, -1, 0, 4)).toEqual(new Float32Array(4));
	});

	it('takes the absolute value', () => {
		const samples = new Float32Array(RATE).fill(0.1);
		samples[RATE / 2] = -0.8;
		const columns = peaks(samples, RATE, 0, 1, 4);
		expect([...columns].map((p) => +p.toFixed(3))).toEqual([0.1, 0.1, 0.8, 0.1]);
	});

	it('still draws columns narrower than a sample', () => {
		const columns = peaks(sine(1, 0.5), RATE, 0.1, 0.1 + 10 / RATE, 100);
		expect(columns.some((p) => p > 0)).toBe(true);
	});

	it('returns nothing for zero columns', () => {
		expect(peaks(sine(1, 0.5), RATE, 0, 1, 0)).toHaveLength(0);
	});
});
