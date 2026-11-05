import { describe, expect, it } from 'vitest';
import type { Guest, PartyState, Playback, QueueItem, QueueItemState } from './types';
import { CHANGEOVER, guestOf, nowPlaying, upcoming, waitEstimate } from './rotation';

const guest = (id: string): Guest => ({ id, name: id, color: '#FFC531', joined_at: 0 });

function item(
	id: string,
	guestId: string,
	addedAt: number,
	extra: { state?: QueueItemState; promoted?: boolean; duration?: number } = {}
): QueueItem {
	return {
		id,
		guest_id: guestId,
		song_id: `song-${id}`,
		title: id,
		artist: null,
		duration: extra.duration ?? 180,
		added_at: addedAt,
		state: extra.state ?? 'queued',
		promoted: extra.promoted ?? false
	};
}

const IDLE: Playback = {
	item_id: null,
	playing: false,
	position: 0,
	at: 0,
	vocals: 0.15,
	pitch: 0
};

function party(queue: QueueItem[], playback: Playback = IDLE): PartyState {
	const guests = [...new Set(queue.map((i) => i.guest_id))].map(guest);
	return {
		code: 'BCDF',
		version: 1,
		guests,
		queue,
		playback,
		settings: { guests_control: false }
	};
}

const ids = (state: PartyState) => upcoming(state).map((i) => i.id);

describe('upcoming', () => {
	it('is empty without queued songs', () => {
		expect(upcoming(party([]))).toEqual([]);
	});

	it('takes turns between guests instead of first come, first served', () => {
		const state = party([
			item('A1', 'A', 1),
			item('A2', 'A', 2),
			item('A3', 'A', 3),
			item('B1', 'B', 4)
		]);
		expect(ids(state)).toEqual(['A1', 'B1', 'A2', 'A3']);
	});

	it('puts those who have sung less first', () => {
		const state = party([
			item('A1', 'A', 1, { state: 'done' }),
			item('A2', 'A', 2),
			item('A3', 'A', 3),
			item('B1', 'B', 5),
			item('C1', 'C', 10)
		]);
		expect(ids(state)).toEqual(['B1', 'C1', 'A2', 'A3']);
	});

	it('puts promoted songs first', () => {
		const state = party([
			item('A1', 'A', 1),
			item('B1', 'B', 2),
			item('C1', 'C', 3, { promoted: true })
		]);
		expect(ids(state)).toEqual(['C1', 'A1', 'B1']);
	});

	it('counts a promoted song as sung, so the order holds once it plays', () => {
		const before = party([
			item('A1', 'A', 1),
			item('A2', 'A', 2, { promoted: true }),
			item('B1', 'B', 3)
		]);
		expect(ids(before)).toEqual(['A2', 'B1', 'A1']);
		const after = party([
			item('A1', 'A', 1),
			item('A2', 'A', 2, { state: 'playing', promoted: true }),
			item('B1', 'B', 3)
		]);
		expect(ids(after)).toEqual(['B1', 'A1']);
	});

	it('leaves out songs that are playing, done or skipped', () => {
		const state = party([
			item('A1', 'A', 1, { state: 'playing' }),
			item('B1', 'B', 2, { state: 'done' }),
			item('C1', 'C', 3, { state: 'skipped' }),
			item('D1', 'D', 4)
		]);
		expect(ids(state)).toEqual(['D1']);
	});
});

describe('waitEstimate', () => {
	const queue = [
		item('P', 'A', 1, { state: 'playing', duration: 200 }),
		item('Q1', 'B', 2, { duration: 100 }),
		item('Q2', 'C', 3, { duration: 100 })
	];

	it('adds what is left of the current song, the songs before and the changeovers', () => {
		const state = party(queue, { ...IDLE, item_id: 'P', playing: false, position: 50, at: 0 });
		const wait = waitEstimate(state, 99_000);
		expect(wait.get('Q1')).toBe(150 + CHANGEOVER);
		expect(wait.get('Q2')).toBe(150 + CHANGEOVER + 100 + CHANGEOVER);
		expect(wait.has('P')).toBe(false);
	});

	it('counts the time since the TV published its position while it plays', () => {
		const state = party(queue, { ...IDLE, item_id: 'P', playing: true, position: 50, at: 1_000 });
		expect(waitEstimate(state, 11_000).get('Q1')).toBe(140 + CHANGEOVER);
	});

	it('never counts less than nothing for a song that has run over', () => {
		const state = party(queue, { ...IDLE, item_id: 'P', playing: true, position: 190, at: 0 });
		expect(waitEstimate(state, 60_000).get('Q1')).toBe(CHANGEOVER);
	});

	it('starts from a changeover when nothing plays', () => {
		const state = party(queue.slice(1));
		expect(waitEstimate(state, 0).get('Q1')).toBe(CHANGEOVER);
	});
});

describe('helpers', () => {
	it('find the song playing and who asked for it', () => {
		const state = party([
			item('A1', 'A', 1, { state: 'done' }),
			item('B1', 'B', 2, { state: 'playing' })
		]);
		expect(nowPlaying(state)?.id).toBe('B1');
		expect(guestOf(state, state.queue[1])?.id).toBe('B');
		expect(nowPlaying(party([item('A1', 'A', 1)]))).toBeNull();
		expect(guestOf(party([]), item('X', 'nobody', 1))).toBeUndefined();
	});
});
