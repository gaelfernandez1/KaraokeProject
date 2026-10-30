import { beforeEach, describe, expect, it } from 'vitest';
import { AudioEngine, MAX_SEMITONES, START_DELAY, type PitchNode } from './engine';

// A tiny stand-in for the Web Audio API: just what the engine touches, and records of it.
class FakeParam {
	value = 1;
	setTargetAtTime(value: number) {
		this.value = value;
	}
}
class FakeNode {
	connections: FakeNode[] = [];
	connect(node: FakeNode) {
		this.connections.push(node);
		return node;
	}
	disconnect() {
		this.connections = [];
	}
}
class FakeGain extends FakeNode {
	gain = new FakeParam();
}
class FakeBuffer {
	readonly data: Float32Array[];
	constructor(
		readonly numberOfChannels: number,
		readonly length: number,
		readonly sampleRate: number
	) {
		this.data = Array.from({ length: numberOfChannels }, () => new Float32Array(length));
	}
	get duration() {
		return this.length / this.sampleRate;
	}
	getChannelData(channel: number) {
		return this.data[channel];
	}
}
class FakeSource extends FakeNode {
	buffer: FakeBuffer | null = null;
	started: [number, number] | null = null;
	stopped = false;
	onended: (() => void) | null = null;
	start(when: number, offset: number) {
		this.started = [when, offset];
	}
	stop() {
		this.stopped = true;
		this.onended?.();
	}
}
class FakeContext {
	currentTime = 100;
	state = 'suspended';
	outputLatency = 0;
	baseLatency = 0;
	destination = new FakeNode();
	sources: FakeSource[] = [];
	gains: FakeGain[] = [];
	async resume() {
		this.state = 'running';
	}
	createGain() {
		const gain = new FakeGain();
		this.gains.push(gain);
		return gain;
	}
	createBufferSource() {
		const source = new FakeSource();
		this.sources.push(source);
		return source;
	}
	createBuffer(channels: number, length: number, rate: number) {
		return new FakeBuffer(channels, length, rate);
	}
	/** Every byte of the "file" is one second of stereo audio at 100 Hz: left 1, right 0. */
	async decodeAudioData(bytes: ArrayBuffer) {
		const buffer = new FakeBuffer(2, bytes.byteLength * 100, 100);
		buffer.data[0].fill(1);
		return buffer;
	}
}

const files: Record<string, number> = { 'inst.m4a': 180, 'voc.m4a': 180 };
const fetchBytes = async (url: string) => {
	if (!(url in files)) throw new Error(`${url}: HTTP 404`);
	return new ArrayBuffer(files[url]);
};

let context: FakeContext;
let engine: AudioEngine;

beforeEach(async () => {
	context = new FakeContext();
	engine = new AudioEngine(context as unknown as AudioContext, { fetchBytes });
	await engine.load({ instrumental: 'inst.m4a', vocals: 'voc.m4a' });
});

const playing = () => context.sources.filter((s) => s.started && !s.stopped);

describe('AudioEngine', () => {
	it('loads both stems and keeps the guide vocals in mono', () => {
		expect(engine.duration).toBe(180);
		expect(engine.vocalsBuffer?.numberOfChannels).toBe(1);
		expect(engine.vocalsBuffer?.getChannelData(0)[0]).toBeCloseTo(0.5, 6);
	});

	it('starts both stems at the same instant and offset', async () => {
		await engine.play();

		expect(context.state).toBe('running');
		const [a, b] = playing();
		expect(a.started).toEqual([100 + START_DELAY, 0]);
		expect(b.started).toEqual(a.started);
		expect(engine.playing).toBe(true);
	});

	it('resumes after a pause from where it stopped', async () => {
		await engine.play();
		context.currentTime += START_DELAY + 12;
		engine.pause();

		expect(playing()).toHaveLength(0);
		expect(engine.position()).toBeCloseTo(12, 6);
		await engine.play();
		expect(playing().map((s) => s.started?.[1])).toEqual([12, 12]);
	});

	it('seeks while playing by restarting both stems at the new position', async () => {
		await engine.play();
		engine.seek(95);

		expect(playing().map((s) => s.started?.[1])).toEqual([95, 95]);
	});

	it('only moves the position when seeking while paused', () => {
		engine.seek(40);

		expect(playing()).toHaveLength(0);
		expect(engine.now()).toBe(40);
	});

	it('sets the guide vocals volume between 0 and 1', () => {
		engine.setVocalVolume(0.3);
		const vocalGain = context.gains.find((g) => g.gain.value === 0.3);
		expect(vocalGain).toBeDefined();

		engine.setVocalVolume(4);
		expect(vocalGain?.gain.value).toBe(1);
	});

	it('reports the end of the song, but not a pause', async () => {
		let ended = 0;
		engine.onEnded(() => ended++);
		await engine.play();
		engine.pause();
		expect(ended).toBe(0);

		await engine.play();
		context.currentTime += 200;
		playing()[0].onended?.();

		expect(ended).toBe(1);
		expect(engine.playing).toBe(false);
		expect(engine.position()).toBe(180);
	});

	it('plays from the start again after the end', async () => {
		await engine.play();
		context.currentTime += 200;
		playing()[0].onended?.();
		await engine.play();

		expect(playing().map((s) => s.started?.[1])).toEqual([0, 0]);
	});

	it('works without guide vocals', async () => {
		const solo = new AudioEngine(context as unknown as AudioContext, { fetchBytes });
		context.sources = [];
		await solo.load({ instrumental: 'inst.m4a', vocals: null });
		await solo.play();

		expect(playing()).toHaveLength(1);
	});

	it('starts once when play is pressed twice before the audio wakes up', async () => {
		await Promise.all([engine.play(), engine.play()]);

		expect(playing()).toHaveLength(2);
		engine.pause();
		expect(playing()).toHaveLength(0);
	});

	it('stays paused when paused while the audio wakes up', async () => {
		const starting = engine.play();
		engine.pause();
		await starting;

		expect(engine.playing).toBe(false);
		expect(playing()).toHaveLength(0);
	});

	it('does not bring back the old song when seeking during a load', async () => {
		await engine.play();
		const loading = engine.load({ instrumental: 'inst.m4a', vocals: 'voc.m4a' });
		engine.seek(30);
		await loading;

		expect(playing()).toHaveLength(0);
		await engine.play();
		expect(playing()).toHaveLength(2);
	});

	it('keeps the song asked for last when loads overlap', async () => {
		let release = () => {};
		const slow = new Promise<void>((resolve) => (release = resolve));
		const sized: Record<string, number> = { 'a.m4a': 200, 'b.m4a': 50 };
		const picky = new AudioEngine(context as unknown as AudioContext, {
			fetchBytes: async (url) => {
				if (url === 'a.m4a') await slow;
				return new ArrayBuffer(sized[url]);
			}
		});
		const first = picky.load({ instrumental: 'a.m4a' });
		await picky.load({ instrumental: 'b.m4a' });
		release();
		await first;

		expect(picky.duration).toBe(50);
	});

	it('is left empty and paused when a load fails', async () => {
		await engine.play();
		await expect(engine.load({ instrumental: 'missing.m4a' })).rejects.toThrow();

		expect(engine.playing).toBe(false);
		expect(engine.duration).toBe(0);
		await engine.play();
		expect(playing()).toHaveLength(0);
	});

	it('stops the old song when a new one loads', async () => {
		await engine.play();
		await engine.load({ instrumental: 'inst.m4a', vocals: 'voc.m4a' });

		expect(playing()).toHaveLength(0);
		expect(engine.playing).toBe(false);
		expect(engine.position()).toBe(0);
	});
});

// Like signalsmith-stretch, every call is a message to the worklet and answers with a promise.
class FakePitch extends FakeNode {
	scheduled: Record<string, unknown>[] = [];
	running = false;
	async schedule(change: Record<string, unknown>) {
		this.scheduled.push(change);
	}
	async start() {
		this.running = true;
	}
	async stop() {
		this.running = false;
	}
	async latency() {
		return 0.12;
	}
}

describe('AudioEngine pitch', () => {
	let pitch: FakePitch;
	let made: number;

	beforeEach(async () => {
		pitch = new FakePitch();
		made = 0;
		const createPitchNode = async () => {
			made++;
			return pitch as unknown as PitchNode;
		};
		context = new FakeContext();
		engine = new AudioEngine(context as unknown as AudioContext, { fetchBytes, createPitchNode });
		await engine.load({ instrumental: 'inst.m4a', vocals: 'voc.m4a' });
	});

	const master = () => context.gains[0];

	it('plays straight to the speakers while the pitch is untouched', () => {
		expect(master().connections).toEqual([context.destination]);
		expect(made).toBe(0);
	});

	it('routes through the pitch shifter and delays the lyrics by its latency', async () => {
		await engine.setPitch(2);
		await engine.play();
		context.currentTime += START_DELAY + 10;

		expect(master().connections).toEqual([pitch]);
		expect(pitch.connections).toEqual([context.destination]);
		expect(pitch.running).toBe(true);
		expect(pitch.scheduled.at(-1)).toMatchObject({ semitones: 2 });
		expect(engine.now()).toBeCloseTo(10 - 0.12, 6);
	});

	it('creates the shifter once and bypasses it again at zero', async () => {
		await engine.setPitch(-3);
		await engine.setPitch(1);
		await engine.setPitch(0);

		expect(made).toBe(1);
		expect(master().connections).toEqual([context.destination]);
		expect(pitch.running).toBe(false);
	});

	it('applies the last key asked for when changes overlap', async () => {
		await Promise.all([engine.setPitch(2), engine.setPitch(0)]);

		expect(master().connections).toEqual([context.destination]);
		expect(pitch.running).toBe(false);
		await engine.play();
		context.currentTime += START_DELAY + 10;
		expect(engine.now()).toBeCloseTo(10, 6);
	});

	it('can try the shifter again after it failed to load', async () => {
		let attempts = 0;
		const flaky = new AudioEngine(context as unknown as AudioContext, {
			fetchBytes,
			createPitchNode: async () => {
				if (attempts++ === 0) throw new Error('no AudioWorklet here');
				return pitch as unknown as PitchNode;
			}
		});
		await flaky.load({ instrumental: 'inst.m4a' });

		await expect(flaky.setPitch(1)).rejects.toThrow('no AudioWorklet');
		await flaky.setPitch(1);
		expect(pitch.running).toBe(true);
	});

	it('keeps the shift within a sensible range', async () => {
		await engine.setPitch(40);

		expect(pitch.scheduled.at(-1)).toMatchObject({ semitones: MAX_SEMITONES });
	});
});
