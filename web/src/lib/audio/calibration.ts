/**
 * Latency calibration by tapping along to clicks. The page plays clicks at known audio times;
 * the user taps when they hear each one. People tapping to a steady beat anticipate it, so the
 * typical gap between a tap and its click is the delay of the output (speakers, HDMI,
 * Bluetooth) rather than reaction time.
 */

/** Audio times of `count` clicks every `interval` seconds, starting `leadIn` after `start`. */
export function clickTimes(start: number, count: number, interval: number, leadIn = 1): number[] {
	return Array.from({ length: count }, (_, i) => start + leadIn + i * interval);
}

const MIN_TAPS = 4;
/** Taps further than this from the typical delay are strays. */
const TOLERANCE = 0.08;
/** Share of the taps that must agree for the estimate to count. */
const MIN_AGREEMENT = 0.6;

/**
 * Typical delay (seconds) from each click to the tap nearest it, or null when the taps are too
 * few or too scattered to trust. Both lists use the audio clock.
 */
export function estimateLatency(clicks: readonly number[], taps: readonly number[]): number | null {
	if (clicks.length === 0 || taps.length < MIN_TAPS) return null;
	const delays = taps.map((tap) => {
		const nearest = clicks.reduce((best, click) =>
			Math.abs(tap - click) < Math.abs(tap - best) ? click : best
		);
		return tap - nearest;
	});
	const typical = median(delays);
	const agreeing = delays.filter((delay) => Math.abs(delay - typical) < TOLERANCE);
	if (agreeing.length < MIN_TAPS || agreeing.length < MIN_AGREEMENT * delays.length) return null;
	return median(agreeing);
}

/** The part of the measured latency the browser does not already report. */
export function manualOffset(measured: number, reported: number): number {
	return measured - reported;
}

function median(values: readonly number[]): number {
	const sorted = [...values].sort((a, b) => a - b);
	const mid = Math.floor(sorted.length / 2);
	return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}
