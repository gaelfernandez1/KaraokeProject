import { describe, expect, it } from 'vitest';
import type { Job, JobStage } from '#lib/api';
import { overallProgress } from './stages';

const job = (stage: JobStage, progress = 0, withLyrics = false): Job => ({
	id: 'j',
	kind: 'make',
	title: 'T',
	stage,
	progress,
	song_id: null,
	file: null,
	error: null,
	with_lyrics: withLyrics,
	created_at: '2026-10-30T10:00:00Z'
});

describe('overallProgress', () => {
	it('grows through the stages and ends at 1', () => {
		const sequence: [JobStage, number][] = [
			['queued', 0],
			['download', 0.5],
			['separate', 0],
			['separate', 0.9],
			['transcribe', 0.3],
			['align', 0.5],
			['audio', 0.5],
			['video', 0.5]
		];
		const values = sequence.map(([stage, p]) => overallProgress(job(stage, p)) as number);
		for (let i = 1; i < values.length; i++) expect(values[i]).toBeGreaterThanOrEqual(values[i - 1]);
		expect(values[0]).toBe(0);
		expect(values.at(-1)).toBeLessThan(1);
		expect(overallProgress(job('done', 1))).toBe(1);
	});

	it('skips the transcription when the lyrics were given', () => {
		const withLyrics = overallProgress(job('align', 0, true)) as number;
		const without = overallProgress(job('align', 0, false)) as number;
		expect(withLyrics).toBeLessThan(without);
	});

	it('has no value for jobs that stopped', () => {
		expect(overallProgress(job('error'))).toBeNull();
		expect(overallProgress(job('cancelled'))).toBeNull();
	});
});

describe('overallProgress of a video export', () => {
	it('starts low when rendering starts and fills while it renders', () => {
		const exporting = (progress: number) => ({
			...job('video', progress, true),
			kind: 'export' as const
		});
		expect(overallProgress(exporting(0))).toBeCloseTo(0.1);
		expect(overallProgress(exporting(0.5))).toBeCloseTo(0.55);
	});
});
