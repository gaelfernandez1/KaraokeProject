import { describe, expect, it } from 'vitest';
import { PlayerSession, STALL_MS, type EngineLike } from './session.svelte';

class FakeEngine implements EngineLike {
	duration = 0;
	playing = false;
	time = 0;
	vocals = 1;
	offset = 0;
	pitchCalls: number[] = [];
	failLoad = false;
	failPitch = false;
	#ended: (() => void)[] = [];

	async load(): Promise<void> {
		if (this.failLoad) throw new Error('HTTP 404');
		this.duration = 120;
	}
	async play() {
		this.playing = true;
	}
	pause() {
		this.playing = false;
	}
	seek(t: number) {
		this.time = t;
	}
	now() {
		return this.time;
	}
	position() {
		return this.time;
	}
	setVocalVolume(v: number) {
		this.vocals = v;
	}
	setManualOffset(s: number) {
		this.offset = s;
	}
	async setPitch(n: number) {
		this.pitchCalls.push(n);
		if (this.failPitch) throw new Error('no worklet');
	}
	onEnded(listener: () => void) {
		this.#ended.push(listener);
	}
	end() {
		this.playing = false;
		for (const l of this.#ended) l();
	}
}

const URLS = { instrumental: 'i.m4a', vocals: 'v.m4a' };

function session(engine = new FakeEngine(), secure = true) {
	return { engine, player: new PlayerSession({ createEngine: () => engine, secure }) };
}

/** A session whose wall clock the test moves by hand. */
function timed(engine = new FakeEngine()) {
	const wall = { ms: 0 };
	const player = new PlayerSession({
		createEngine: () => engine,
		secure: true,
		wallNow: () => wall.ms
	});
	return { engine, player, wall };
}

describe('PlayerSession', () => {
	it('loads, applies the device settings and becomes ready', async () => {
		const { engine, player } = session();
		await player.load(URLS, { vocals: 0.3, latencyMs: 80 });
		expect(player.state).toBe('ready');
		expect(player.duration).toBe(120);
		expect(engine.vocals).toBe(0.3);
		expect(engine.offset).toBeCloseTo(0.08);
	});

	it('a song loaded after another one ended starts fresh, not ended', async () => {
		// The party TV keeps one session for the whole night.
		const { engine, player } = session();
		await player.load(URLS, { vocals: 0, latencyMs: 0 });
		await player.play();
		engine.end();
		player.tick();
		expect(player.state).toBe('ended');
		await player.load({ instrumental: 'b.m4a', vocals: 'bv.m4a' }, { vocals: 0, latencyMs: 0 });
		player.tick();
		expect(player.state).toBe('ready');
	});

	it('reports a failed load and can try again', async () => {
		const { engine, player } = session();
		engine.failLoad = true;
		await player.load(URLS, { vocals: 0, latencyMs: 0 });
		expect(player.state).toBe('error');
		expect(player.error).toBe('audioLoad');
		engine.failLoad = false;
		await player.retry();
		expect(player.state).toBe('ready');
		expect(player.error).toBeNull();
	});

	it('toggles between playing and paused, following the engine', async () => {
		const { engine, player } = session();
		await player.load(URLS, { vocals: 0, latencyMs: 0 });
		await player.toggle();
		player.tick();
		expect(player.state).toBe('playing');
		void player.toggle();
		player.tick();
		expect(engine.playing).toBe(false);
		expect(player.state).toBe('paused');
	});

	it('keeps seeks and skips inside the song', async () => {
		const { engine, player } = session();
		await player.load(URLS, { vocals: 0, latencyMs: 0 });
		player.seek(500);
		expect(engine.time).toBe(120);
		engine.time = 2;
		player.skip(-5);
		expect(engine.time).toBe(0);
	});

	it('ends when the engine ends', async () => {
		const { engine, player } = session();
		await player.load(URLS, { vocals: 0, latencyMs: 0 });
		await player.toggle();
		engine.end();
		player.tick();
		expect(player.state).toBe('ended');
	});

	it('gives up on the key change where it cannot work', async () => {
		const { engine, player } = session();
		await player.load(URLS, { vocals: 0, latencyMs: 0 });
		engine.failPitch = true;
		await player.setPitch(2);
		expect(player.pitch).toBe(0);
		expect(player.pitchAvailable).toBe(false);
	});

	it('does not offer the key change outside a secure context', () => {
		expect(session(new FakeEngine(), false).player.pitchAvailable).toBe(false);
	});

	it('clamps the key and the guide vocals', async () => {
		const { engine, player } = session();
		await player.load(URLS, { vocals: 0, latencyMs: 0 });
		await player.setPitch(20);
		expect(player.pitch).toBe(12);
		expect(engine.pitchCalls.at(-1)).toBe(12);
		player.setVocals(-1);
		expect(player.vocals).toBe(0);
		expect(engine.vocals).toBe(0);
	});
	it('says the browser is not playing sound when the audio clock does not move', async () => {
		const { engine, player, wall } = timed();
		await player.load(URLS, { vocals: 0.15, latencyMs: 0 });
		await player.play();
		wall.ms = STALL_MS - 100;
		player.tick();
		expect(player.state).toBe('playing');
		wall.ms = STALL_MS + 100;
		player.tick();
		expect(player.state).toBe('error');
		expect(player.error).toBe('audioStalled');
		expect(engine.playing).toBe(false);
	});

	it('keeps playing once the audio clock moves', async () => {
		const { engine, player, wall } = timed();
		await player.load(URLS, { vocals: 0.15, latencyMs: 0 });
		await player.play();
		engine.time = 0.4;
		wall.ms = 400;
		player.tick();
		wall.ms = STALL_MS * 3;
		player.tick();
		expect(player.state).toBe('playing');
	});

	it('says so when the engine cannot start the sound at all', async () => {
		const { engine, player } = timed();
		engine.play = async () => {
			throw new Error('the audio did not start');
		};
		await player.load(URLS, { vocals: 0.15, latencyMs: 0 });
		await player.play();
		expect(player.state).toBe('error');
		expect(player.error).toBe('audioStalled');
	});
});
