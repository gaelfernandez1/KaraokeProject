import { subscribe, type Subscription } from '#lib/api/events.js';
import { partyEventsUrl } from './client';
import type { PartyCommand, PartyState } from './types';

export interface ConnectionOptions {
	/** Tests pass a fake EventSource. */
	createSource?: (url: string) => EventSource;
	/** Remote control presses; the server sends them only to the host. */
	onCommand?: (command: PartyCommand) => void;
}

/**
 * A live view of one party, for the TV and the phones alike: the server sends the whole state
 * on connecting and after every change. EventSource reconnects by itself, and a snapshot that
 * arrives late (an old connection's, after a reconnect) never overwrites a newer one.
 */
export class PartyConnection {
	/** Replaced whole on every change, never edited, so it need not be deeply reactive. */
	state = $state.raw<PartyState | null>(null);
	connected = $state(false);

	readonly code: string;
	readonly #token: string;
	readonly #options: ConnectionOptions;
	#subscription: Subscription | null = null;
	/** Set on every (re)connection, until its first state arrives. */
	#fresh = false;

	constructor(code: string, token: string, options: ConnectionOptions = {}) {
		this.code = code.toUpperCase();
		this.#token = token;
		this.#options = options;
	}

	start(): void {
		if (this.#subscription) return;
		this.#subscription = subscribe(
			partyEventsUrl(this.code, this.#token),
			{
				state: (data) => this.#apply(data as PartyState),
				command: (data) => this.#options.onCommand?.(data as PartyCommand)
			},
			{
				createSource: this.#options.createSource,
				onOpen: () => {
					this.connected = true;
					this.#fresh = true;
				},
				onError: () => {
					this.connected = false;
				}
			}
		);
	}

	close(): void {
		this.#subscription?.close();
		this.#subscription = null;
		this.connected = false;
	}

	/**
	 * Takes a newer state. The first one after (re)connecting is always taken: a restarted
	 * server counts versions from the start again, and the server sends it whole on connecting.
	 */
	#apply(next: PartyState): void {
		if (!this.#fresh && this.state && next.version <= this.state.version) return;
		this.#fresh = false;
		this.state = next;
	}
}
