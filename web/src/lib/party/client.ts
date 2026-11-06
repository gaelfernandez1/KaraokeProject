import { apiRequest, jsonBody } from '#lib/api/client.js';
import type {
	Joined,
	PartyCommand,
	PartyCreated,
	PartySettings,
	PartyState,
	Playback,
	QueueItem,
	QueueItemState
} from './types';

type Fetch = typeof fetch;

/** Codes are typed by hand on phones, so any case works. */
const partyUrl = (code: string) => `/api/parties/${encodeURIComponent(code.toUpperCase())}`;

/** Who is asking: the host token or a guest token. */
function withToken(token: string, init: RequestInit = {}): RequestInit {
	return {
		...init,
		headers: { ...(init.headers as Record<string, string>), Authorization: `Bearer ${token}` }
	};
}

export function createParty(fetchImpl?: Fetch): Promise<PartyCreated> {
	return apiRequest('/api/parties', { method: 'POST' }, fetchImpl);
}

export function getParty(code: string, fetchImpl?: Fetch): Promise<PartyState> {
	return apiRequest(partyUrl(code), {}, fetchImpl);
}

/** Host only: ends the party; the phones are told and stop following it. */
export function endParty(code: string, token: string, fetchImpl?: Fetch): Promise<void> {
	return apiRequest(partyUrl(code), withToken(token, { method: 'DELETE' }), fetchImpl);
}

/** Joining again with the same name gives back the same guest and token. */
export function joinParty(code: string, name: string, fetchImpl?: Fetch): Promise<Joined> {
	return apiRequest(`${partyUrl(code)}/guests`, jsonBody('POST', { name }), fetchImpl);
}

export function enqueue(
	code: string,
	token: string,
	songId: string,
	fetchImpl?: Fetch
): Promise<QueueItem> {
	return apiRequest(
		`${partyUrl(code)}/queue`,
		withToken(token, jsonBody('POST', { song_id: songId })),
		fetchImpl
	);
}

/** Guests remove their own queued songs; the host removes any. */
export function removeItem(
	code: string,
	token: string,
	itemId: string,
	fetchImpl?: Fetch
): Promise<void> {
	return apiRequest(
		`${partyUrl(code)}/queue/${encodeURIComponent(itemId)}`,
		withToken(token, { method: 'DELETE' }),
		fetchImpl
	);
}

/** Host only: the song goes before every turn. */
export function promote(
	code: string,
	token: string,
	itemId: string,
	fetchImpl?: Fetch
): Promise<void> {
	return apiRequest(
		`${partyUrl(code)}/promote/${encodeURIComponent(itemId)}`,
		withToken(token, { method: 'POST' }),
		fetchImpl
	);
}

/** Host only: a song starts, ends or is skipped. */
export function advance(
	code: string,
	token: string,
	itemId: string,
	state: Exclude<QueueItemState, 'queued'>,
	fetchImpl?: Fetch
): Promise<void> {
	return apiRequest(
		`${partyUrl(code)}/advance`,
		withToken(token, jsonBody('PUT', { item_id: itemId, state })),
		fetchImpl
	);
}

/** A remote control press, relayed to the TV; guests need the host's permission. */
export function sendCommand(
	code: string,
	token: string,
	command: PartyCommand,
	fetchImpl?: Fetch
): Promise<void> {
	return apiRequest(
		`${partyUrl(code)}/commands`,
		withToken(token, jsonBody('POST', command)),
		fetchImpl
	);
}

/** Host only: what the TV plays, so phones can show it. */
export function publishPlayback(
	code: string,
	token: string,
	playback: Playback,
	fetchImpl?: Fetch
): Promise<void> {
	return apiRequest(
		`${partyUrl(code)}/playback`,
		withToken(token, jsonBody('PUT', playback)),
		fetchImpl
	);
}

export function updateSettings(
	code: string,
	token: string,
	settings: PartySettings,
	fetchImpl?: Fetch
): Promise<void> {
	return apiRequest(
		`${partyUrl(code)}/settings`,
		withToken(token, jsonBody('PUT', settings)),
		fetchImpl
	);
}

/** EventSource cannot send headers, so the token goes in the URL. */
export function partyEventsUrl(code: string, token: string): string {
	return `${partyUrl(code)}/events?token=${encodeURIComponent(token)}`;
}

// Credentials are remembered per party, so a phone that reloads or comes back from sleep
// rejoins as the same guest, and the TV keeps being the host.

type Store = Pick<Storage, 'getItem' | 'setItem'>;

function browserStorage(): Store | null {
	try {
		return localStorage;
	} catch {
		return null;
	}
}

const guestKey = (code: string) => `foliada.party.${code.toUpperCase()}`;
const hostKey = (code: string) => `foliada.party-host.${code.toUpperCase()}`;

function save(storage: Store | null, key: string, value: unknown): void {
	try {
		storage?.setItem(key, JSON.stringify(value));
	} catch {
		// Private windows can refuse storage; rejoining by name gives the same guest back.
	}
}

function load(storage: Store | null, key: string): Record<string, unknown> | null {
	try {
		const value: unknown = JSON.parse(storage?.getItem(key) ?? 'null');
		return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null;
	} catch {
		return null;
	}
}

export function rememberGuest(
	code: string,
	joined: Joined,
	storage: Store | null = browserStorage()
): void {
	save(storage, guestKey(code), joined);
}

export function rememberedGuest(
	code: string,
	storage: Store | null = browserStorage()
): Joined | null {
	const stored = load(storage, guestKey(code));
	const guest = stored?.guest as Record<string, unknown> | null | undefined;
	const valid =
		typeof stored?.token === 'string' &&
		typeof guest === 'object' &&
		guest !== null &&
		typeof guest.id === 'string' &&
		typeof guest.name === 'string';
	return valid ? (stored as unknown as Joined) : null;
}

export function rememberHost(
	created: PartyCreated,
	storage: Store | null = browserStorage()
): void {
	save(storage, hostKey(created.code), {
		code: created.code.toUpperCase(),
		host_token: created.host_token
	});
}

export function rememberedHost(
	code: string,
	storage: Store | null = browserStorage()
): PartyCreated | null {
	const stored = load(storage, hostKey(code));
	return typeof stored?.code === 'string' && typeof stored.host_token === 'string'
		? { code: stored.code, host_token: stored.host_token }
		: null;
}
