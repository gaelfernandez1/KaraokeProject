import { describe, expect, it } from 'vitest';
import { SongClock, type TimeSource } from './clock';

/** An audio clock that only moves when told to, like AudioContext.currentTime in quanta. */
class FakeTime implements TimeSource {
	context = 10;
	perf = 5000;
	latency = 0;

	contextTime(): number {
		return this.context;
	}
	perfNow(): number {
		return this.perf;
	}
	reportedLatency(): number {
		return this.latency;
	}
	/** Advances both clocks together by `seconds`. */
	tick(seconds: number): void {
		this.context += seconds;
		this.perf += seconds * 1000;
	}
}

const clockAt = (time: FakeTime, duration = 100) => new SongClock(time, duration);

describe('SongClock', () => {
	it('stays put while paused', () => {
		const time = new FakeTime();
		const clock = clockAt(time);
		clock.seek(12);
		time.tick(3);

		expect(clock.now()).toBe(12);
		expect(clock.position()).toBe(12);
	});

	it('follows the audio clock while playing', () => {
		const time = new FakeTime();
		const clock = clockAt(time);
		clock.play(20);
		time.tick(1.5);

		expect(clock.now()).toBeCloseTo(21.5, 6);
	});

	it('takes the output latency off what is heard, not off the transport', () => {
		const time = new FakeTime();
		time.latency = 0.2;
		const clock = clockAt(time);
		clock.play(0);
		time.tick(1);

		expect(clock.position()).toBeCloseTo(1, 6);
		expect(clock.now()).toBeCloseTo(0.8, 6);
	});

	it('holds the start position until the first sound reaches the speaker', () => {
		const time = new FakeTime();
		time.latency = 0.3;
		const clock = clockAt(time);
		clock.play(42);
		time.tick(0.1);

		expect(clock.now()).toBe(42);
	});

	it('adds the manual offset and the extra latency of effects', () => {
		const time = new FakeTime();
		time.latency = 0.1;
		const clock = clockAt(time);
		clock.setManualOffset(0.15);
		clock.setExtraLatency(0.05);
		clock.play(0);
		time.tick(2);

		expect(clock.now()).toBeCloseTo(1.7, 6);
	});

	it('accepts a negative manual offset for outputs that report too much latency', () => {
		const time = new FakeTime();
		time.latency = 0.3;
		const clock = clockAt(time);
		clock.setManualOffset(-0.1);
		clock.play(0);
		time.tick(1);

		expect(clock.now()).toBeCloseTo(0.8, 6);
	});

	it('interpolates between the steps of the audio clock', () => {
		const time = new FakeTime();
		const clock = clockAt(time);
		clock.play(0);
		time.tick(1);
		clock.now();
		// The audio clock has not moved yet, but 8 ms of real time have passed.
		time.perf += 8;

		expect(clock.now()).toBeCloseTo(1.008, 6);
	});

	it('does not run ahead when the audio clock stalls', () => {
		const time = new FakeTime();
		const clock = clockAt(time);
		clock.play(0);
		time.tick(1);
		clock.now();
		time.perf += 2000;

		expect(clock.now()).toBeLessThanOrEqual(1.05 + 1e-9);
	});

	it('never goes backwards while playing', () => {
		const time = new FakeTime();
		const clock = clockAt(time);
		clock.play(0);
		time.tick(1);
		clock.now();
		time.perf += 20;
		const ahead = clock.now();
		// The audio clock catches up a little less than the interpolation guessed.
		time.context += 0.01;

		expect(clock.now()).toBeGreaterThanOrEqual(ahead);
	});

	it('pauses where the transport is, so resuming does not skip or repeat', () => {
		const time = new FakeTime();
		time.latency = 0.2;
		const clock = clockAt(time);
		clock.play(5);
		time.tick(2);
		clock.pause();

		expect(clock.position()).toBeCloseTo(7, 6);
		expect(clock.now()).toBeCloseTo(7, 6);
		expect(clock.playing).toBe(false);
	});

	it('restarts from the new position on a seek while playing', () => {
		const time = new FakeTime();
		const clock = clockAt(time);
		clock.play(5);
		time.tick(2);
		clock.seek(60);
		time.tick(1);

		expect(clock.now()).toBeCloseTo(61, 6);
	});

	it('counts from the scheduled start, not from the call', () => {
		const time = new FakeTime();
		const clock = clockAt(time);
		clock.play(30, time.context + 0.05);
		time.tick(0.03);

		expect(clock.position()).toBe(30);
		expect(clock.now()).toBe(30);
		time.tick(0.07);
		expect(clock.position()).toBeCloseTo(30.05, 6);
	});

	it('never passes the end of the song or goes below zero', () => {
		const time = new FakeTime();
		const clock = clockAt(time, 10);
		clock.play(9);
		time.tick(5);

		expect(clock.now()).toBe(10);
		expect(clock.ended()).toBe(true);
		clock.seek(-3);
		expect(clock.now()).toBe(0);
	});
});
