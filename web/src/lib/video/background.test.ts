import { describe, expect, test } from 'vitest';
import { BackgroundSync, type VideoLike } from './background';

class FakeVideo implements VideoLike {
	currentTime = 0;
	playbackRate = 1;
	paused = true;
	seeking = false;
	duration = 100;
	plays = 0;
	refuse = false;
	play(): Promise<void> {
		this.plays++;
		if (this.refuse) return Promise.reject(new Error('NotAllowedError'));
		this.paused = false;
		return Promise.resolve();
	}
	pause() {
		this.paused = true;
	}
}

function setup(now: number, playing: boolean) {
	const video = new FakeVideo();
	const clock = { now: () => now, playing };
	const sync = new BackgroundSync(video, clock);
	return { video, clock, sync };
}

describe('BackgroundSync', () => {
	test('starts the video where the song is and plays it', () => {
		const { video, sync } = setup(12, true);

		sync.tick();

		expect(video.currentTime).toBe(12);
		expect(video.paused).toBe(false);
	});

	test('pauses with the clock and stays on the right frame', () => {
		const { video, clock, sync } = setup(12, true);
		sync.tick();
		clock.playing = false;
		clock.now = () => 30;

		sync.tick();

		expect(video.paused).toBe(true);
		expect(video.currentTime).toBe(30);
	});

	test('seeks when it drifts far', () => {
		const { video, clock, sync } = setup(12, true);
		sync.tick();
		clock.now = () => 40;

		sync.tick();

		expect(video.currentTime).toBe(40);
		expect(video.playbackRate).toBe(1);
	});

	test('nudges the rate when it drifts a little', () => {
		const { video, clock, sync } = setup(12, true);
		sync.tick();
		video.currentTime = 12.1; // 0.1 s ahead
		clock.now = () => 12;

		sync.tick();

		expect(video.currentTime).toBe(12.1);
		expect(video.playbackRate).toBeCloseTo(0.95);
	});

	test('the rate goes back to 1 once in step', () => {
		const { video, clock, sync } = setup(12, true);
		sync.tick();
		video.currentTime = 11.9;
		sync.tick();
		expect(video.playbackRate).toBeCloseTo(1.05);
		video.currentTime = 12.01;

		sync.tick();

		expect(video.playbackRate).toBe(1);
		expect(clock.now()).toBe(12);
	});

	test('a video shorter than the song loops', () => {
		const { video, sync } = setup(130, true);

		sync.tick();

		expect(video.currentTime).toBe(30);
	});

	test('waits for the video to know its length', () => {
		const { video, sync } = setup(12, true);
		video.duration = Number.NaN;

		sync.tick();

		expect(video.paused).toBe(true);
	});

	test('leaves a seek in progress alone', () => {
		const { video, clock, sync } = setup(12, true);
		sync.tick();
		video.seeking = true;
		clock.now = () => 12.5;

		sync.tick();

		expect(video.currentTime).toBe(12);
	});

	test('stops trying when the browser refuses to play, until the song stops', async () => {
		const { video, clock, sync } = setup(12, true);
		video.refuse = true;
		sync.tick();
		await Promise.resolve();
		await Promise.resolve();
		clock.now = () => 13;

		sync.tick();
		sync.tick();

		expect(video.plays).toBe(1);
		expect(video.currentTime).toBe(12);
		clock.playing = false;
		sync.tick();
		clock.playing = true;
		video.refuse = false;
		sync.tick();
		expect(video.plays).toBe(2);
	});
});
