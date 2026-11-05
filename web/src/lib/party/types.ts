/*
 * Party mode: one TV (the host) plays the songs, guests' phones request songs and act as remote
 * controls. The server keeps this state and relays it; every client works out the turn order
 * from it with the same function (`upcoming` in rotation.ts).
 */

export interface Guest {
	id: string;
	name: string;
	/** One of the singer colours: it stands for this person on every screen. */
	color: string;
	/** Milliseconds since the epoch. */
	joined_at: number;
}

export type QueueItemState = 'queued' | 'playing' | 'done' | 'skipped';

export interface QueueItem {
	id: string;
	guest_id: string;
	song_id: string;
	title: string;
	artist: string | null;
	/** Seconds, for wait estimates. */
	duration: number;
	/** Milliseconds since the epoch. */
	added_at: number;
	state: QueueItemState;
	/** Put first by the host. */
	promoted: boolean;
}

/** What the TV is playing, published by the TV so phones can show it. */
export interface Playback {
	item_id: string | null;
	playing: boolean;
	/** Song position in seconds at `at` (milliseconds since the epoch). */
	position: number;
	at: number;
	vocals: number;
	pitch: number;
}

export interface PartySettings {
	/** Whether guests may pause, skip and change the sound, or only request songs. */
	guests_control: boolean;
}

export interface PartyState {
	code: string;
	/** Goes up with every change; a client ignores a state older than the one it has. */
	version: number;
	guests: Guest[];
	queue: QueueItem[];
	playback: Playback;
	settings: PartySettings;
}

export type PartyCommand =
	| { type: 'play' }
	| { type: 'pause' }
	| { type: 'skip' }
	| { type: 'vocals'; value: number }
	| { type: 'pitch'; value: number };

export interface PartyCreated {
	code: string;
	host_token: string;
}

export interface Joined {
	guest: Guest;
	token: string;
}

/** A guest's colour; the first is orange, not the lyric amber, which means "sung". */
export const SINGER_COLORS = ['#FF8A3D', '#4FD1FF', '#FF6FB5', '#7CE38B'] as const;
