/**
 * The loudest sample (absolute value) in each of `columns` equal slices of [from, to) seconds,
 * to draw a waveform of the guide vocals under a line. Slices outside the audio are 0.
 */
export function peaks(
	samples: Float32Array,
	sampleRate: number,
	from: number,
	to: number,
	columns: number
): Float32Array {
	const out = new Float32Array(Math.max(0, Math.floor(columns)));
	if (out.length === 0 || !(sampleRate > 0) || !(to > from) || !Number.isFinite(to - from)) {
		return out;
	}
	const step = (to - from) / out.length;
	for (let c = 0; c < out.length; c++) {
		// Both edges come from the same expression, so neighbouring columns share them exactly.
		const a = (from + c * step) * sampleRate;
		const b = (from + (c + 1) * step) * sampleRate;
		let first = Math.max(0, Math.ceil(a));
		let last = Math.min(samples.length, Math.ceil(b));
		if (first >= last) {
			// Zoomed in past one sample per column: show the sample the column falls on.
			first = Math.floor(a);
			last = first + 1;
			if (first < 0 || first >= samples.length) continue;
		}
		let peak = 0;
		for (let i = first; i < last; i++) peak = Math.max(peak, Math.abs(samples[i]));
		out[c] = peak;
	}
	return out;
}
