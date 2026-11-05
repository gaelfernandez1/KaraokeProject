import type { Guest, PartyState, QueueItem } from './types';

/** Seconds between songs: the next singer finds the microphone, the TV loads the song. */
export const CHANGEOVER = 20;

/** The song on the TV now, if any. */
export function nowPlaying(state: PartyState): QueueItem | null {
	return state.queue.find((item) => item.state === 'playing') ?? null;
}

/** Who asked for a song; undefined if that guest is no longer listed. */
export function guestOf(state: PartyState, item: QueueItem): Guest | undefined {
	return state.guests.find((guest) => guest.id === item.guest_id);
}

const byAddedAt = (a: QueueItem, b: QueueItem) =>
	a.added_at - b.added_at || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);

/**
 * The turn order of the songs still to sing. Promoted songs go first. Then turns go round the
 * guests: whoever has sung less goes first, and within a round it is first come, first served,
 * so one guest queueing ten songs cannot keep the others waiting. Every screen runs this on the
 * same state, so they all show the same order.
 */
export function upcoming(state: PartyState): QueueItem[] {
	const queued = state.queue.filter((item) => item.state === 'queued').sort(byAddedAt);
	const promoted = queued.filter((item) => item.promoted);

	// A promoted song counts as sung: it will have been by the time the guest's next one is due,
	// and the order then stays the same when it starts playing.
	const turns = new Map<string, number>();
	const count = (guestId: string) => turns.set(guestId, (turns.get(guestId) ?? 0) + 1);
	for (const item of state.queue) if (item.state !== 'queued') count(item.guest_id);
	for (const item of promoted) count(item.guest_id);

	const rest: { item: QueueItem; round: number }[] = [];
	for (const item of queued) {
		if (item.promoted) continue;
		rest.push({ item, round: turns.get(item.guest_id) ?? 0 });
		count(item.guest_id);
	}
	rest.sort((a, b) => a.round - b.round || byAddedAt(a.item, b.item));
	return [...promoted, ...rest.map(({ item }) => item)];
}

/**
 * Seconds until each upcoming song starts, by item id: what is left of the song playing, the
 * songs before it and a changeover before each. `now` is in milliseconds since the epoch.
 */
export function waitEstimate(state: PartyState, now: number): Map<string, number> {
	let wait = 0;
	const playing = nowPlaying(state);
	if (playing) {
		const { playback } = state;
		let position = 0;
		// Until the TV publishes its position for this song, assume it has just started.
		if (playback.item_id === playing.id) {
			position = playback.position + (playback.playing ? (now - playback.at) / 1000 : 0);
		}
		wait = Math.max(0, playing.duration - position);
	}
	const waits = new Map<string, number>();
	for (const item of upcoming(state)) {
		wait += CHANGEOVER;
		waits.set(item.id, wait);
		wait += item.duration;
	}
	return waits;
}
