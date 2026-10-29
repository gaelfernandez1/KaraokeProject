import { describe, expect, it } from 'vitest';
import { clickTimes, estimateLatency, manualOffset } from './calibration';

describe('clickTimes', () => {
	it('schedules evenly spaced clicks after a lead-in', () => {
		expect(clickTimes(10, 4, 0.5, 1)).toEqual([11, 11.5, 12, 12.5]);
	});
});

describe('estimateLatency', () => {
	const clicks = clickTimes(0, 8, 0.6, 0);

	it('is the median delay of the taps behind the clicks', () => {
		const taps = clicks.map((c, i) => c + 0.12 + (i % 2 ? 0.01 : -0.01));

		expect(estimateLatency(clicks, taps)).toBeCloseTo(0.12, 2);
	});

	it('handles taps that land before the click they belong to', () => {
		const taps = clicks.map((c) => c - 0.05);

		expect(estimateLatency(clicks, taps)).toBeCloseTo(-0.05, 6);
	});

	it('ignores stray taps and double taps', () => {
		const taps = [...clicks.map((c) => c + 0.2), 3.0, 0.21];

		expect(estimateLatency(clicks, taps)).toBeCloseTo(0.2, 6);
	});

	it('needs enough taps to be trusted', () => {
		expect(estimateLatency(clicks, [0.1, 0.7])).toBeNull();
	});

	it('gives up when the taps do not follow the clicks', () => {
		const taps = [0.05, 0.9, 1.0, 2.6, 2.7, 4.4];

		expect(estimateLatency(clicks, taps)).toBeNull();
	});
});

describe('manualOffset', () => {
	it('is what the browser does not report', () => {
		expect(manualOffset(0.25, 0.04)).toBeCloseTo(0.21, 6);
	});
});
