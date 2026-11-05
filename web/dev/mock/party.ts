import { randomBytes } from 'node:crypto';
import {
	SINGER_COLORS,
	type Joined,
	type PartyCommand,
	type PartyCreated,
	type PartySettings,
	type PartyState,
	type Playback,
	type QueueItem,
	type QueueItemState
} from '../../src/lib/party/types.ts';
import type { Library } from './library.ts';

/** No vowels, so a code never spells a word. */
const CODE_LETTERS = 'BCDFGHJKLMNPQRSTVWXZ';
const MAX_NAME = 24;

type Listener = (event: 'state' | 'command', data: unknown) => void;

interface Room {
	state: PartyState;
	hostToken: string;
	/** Guest token → guest id. */
	tokens: Map<string, string>;
	listeners: Set<{ token: string | null; listener: Listener }>;
}

const token = () => randomBytes(12).toString('base64url');

/**
 * Party rooms in memory: guests, the queue, what the TV is playing and what guests may do. The
 * server only stores and relays; the turn order is worked out by each client.
 */
export class Parties {
	readonly #library: Library;
	readonly #now: () => number;
	readonly #rooms = new Map<string, Room>();
	#ids = 0;

	constructor(library: Library, now: () => number = Date.now) {
		this.#library = library;
		this.#now = now;
	}

	create(): PartyCreated {
		let code: string;
		do {
			code = Array.from(randomBytes(4), (b) => CODE_LETTERS[b % CODE_LETTERS.length]).join('');
		} while (this.#rooms.has(code));
		const hostToken = token();
		const playback: Playback = {
			item_id: null,
			playing: false,
			position: 0,
			at: this.#now(),
			vocals: 0.15,
			pitch: 0
		};
		this.#rooms.set(code, {
			state: {
				code,
				version: 1,
				guests: [],
				queue: [],
				playback,
				settings: { guests_control: false }
			},
			hostToken,
			tokens: new Map(),
			listeners: new Set()
		});
		return { code, host_token: hostToken };
	}

	get(code: string): PartyState | undefined {
		return this.#rooms.get(code.toUpperCase())?.state;
	}

	/** Joining again with the same name (any case or spacing) is the same guest. */
	join(code: string, name: string): Joined | undefined {
		const room = this.#rooms.get(code.toUpperCase());
		const clean = name.trim().replace(/\s+/g, ' ').slice(0, MAX_NAME);
		if (!room || !clean) return undefined;
		const key = clean.toLocaleLowerCase();
		let guest = room.state.guests.find((g) => g.name.toLocaleLowerCase() === key);
		if (!guest) {
			guest = {
				id: `g${++this.#ids}`,
				name: clean,
				color: SINGER_COLORS[room.state.guests.length % SINGER_COLORS.length],
				joined_at: this.#now()
			};
			room.state.guests.push(guest);
			this.#changed(room);
		}
		const existing = [...room.tokens].find(([, id]) => id === guest.id)?.[0];
		const guestToken = existing ?? token();
		room.tokens.set(guestToken, guest.id);
		return { guest, token: guestToken };
	}

	enqueue(code: string, who: string, songId: string): QueueItem | undefined {
		const room = this.#rooms.get(code.toUpperCase());
		const guestId = room?.tokens.get(who);
		const song = this.#library.summary(songId);
		if (!room || !guestId || !song) return undefined;
		const item: QueueItem = {
			id: `q${++this.#ids}`,
			guest_id: guestId,
			song_id: songId,
			title: song.title,
			artist: song.artist,
			duration: song.duration,
			added_at: this.#now(),
			state: 'queued',
			promoted: false
		};
		room.state.queue.push(item);
		this.#changed(room);
		return item;
	}

	/** A guest removes their own queued songs; the host removes any. */
	remove(code: string, who: string, itemId: string): boolean {
		const room = this.#rooms.get(code.toUpperCase());
		if (!room) return false;
		const index = room.state.queue.findIndex((i) => i.id === itemId && i.state === 'queued');
		if (index === -1) return false;
		const isHost = who === room.hostToken;
		if (!isHost && room.tokens.get(who) !== room.state.queue[index].guest_id) return false;
		room.state.queue.splice(index, 1);
		this.#changed(room);
		return true;
	}

	/**
	 * Sends a command to the TV: always from the host; from a guest if the host allows guests to
	 * control, or if it is that guest's song that is playing.
	 */
	command(code: string, who: string, command: PartyCommand): boolean {
		const room = this.#rooms.get(code.toUpperCase());
		if (!room) return false;
		const guest = room.tokens.get(who);
		const singing = room.state.queue.some((i) => i.state === 'playing' && i.guest_id === guest);
		const allowed =
			who === room.hostToken ||
			(guest !== undefined && (room.state.settings.guests_control || singing));
		if (!allowed) return false;
		for (const { token: t, listener } of room.listeners) {
			if (t === room.hostToken) listener('command', command);
		}
		return true;
	}

	publishPlayback(code: string, who: string, playback: Playback): boolean {
		return this.#asHost(code, who, (room) => {
			room.state.playback = playback;
		});
	}

	/** The host marks a queued song as playing, done or skipped; only one song plays at a time. */
	advance(code: string, who: string, itemId: string, state: QueueItemState): boolean {
		return this.#asHost(code, who, (room) => {
			const item = room.state.queue.find((i) => i.id === itemId);
			if (!item) return false;
			if (state === 'playing') {
				for (const other of room.state.queue) if (other.state === 'playing') other.state = 'done';
			}
			item.state = state;
		});
	}

	promote(code: string, who: string, itemId: string): boolean {
		return this.#asHost(code, who, (room) => {
			const item = room.state.queue.find((i) => i.id === itemId);
			if (!item) return false;
			item.promoted = true;
		});
	}

	updateSettings(code: string, who: string, settings: PartySettings): boolean {
		return this.#asHost(code, who, (room) => {
			room.state.settings = { ...settings };
		});
	}

	/** Sends the current state at once, then every change (and commands, to the host). */
	subscribe(code: string, who: string | null, listener: Listener): (() => void) | undefined {
		const room = this.#rooms.get(code.toUpperCase());
		if (!room) return undefined;
		const entry = { token: who, listener };
		room.listeners.add(entry);
		listener('state', room.state);
		return () => room.listeners.delete(entry);
	}

	isHost(code: string, who: string): boolean {
		return this.#rooms.get(code.toUpperCase())?.hostToken === who;
	}

	#asHost(code: string, who: string, change: (room: Room) => void | false): boolean {
		const room = this.#rooms.get(code.toUpperCase());
		if (!room || who !== room.hostToken) return false;
		if (change(room) === false) return false;
		this.#changed(room);
		return true;
	}

	#changed(room: Room): void {
		room.state.version++;
		for (const { listener } of room.listeners) listener('state', room.state);
	}
}
