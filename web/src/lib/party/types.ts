/*
 * Party mode: one TV (the host) plays the songs, guests' phones request songs and act as remote
 * controls. The server keeps this state and relays it; every client works out the turn order
 * from it with the same function (`upcoming` in rotation.ts).
 */

import type { components } from '#lib/api/generated/openapi.js';

type Schemas = components['schemas'];

export type Guest = Schemas['Guest'];
export type QueueItemState = Schemas['QueueItem']['state'];
export type QueueItem = Schemas['QueueItem'];
/** What the TV is playing, published by the TV so phones can show it. */
export type Playback = Schemas['Playback'];
export type PartySettings = Schemas['PartySettings'];
/** `version` goes up with every change; a client ignores a state older than the one it has. */
export type PartyState = Schemas['PartyState'];
export type PartyCommand = Schemas['SimpleCommand'] | Schemas['ValueCommand'];
export type PartyCreated = Schemas['PartyCreated'];
export type Joined = Schemas['Joined'];

/** A guest's colour; the first is orange, not the lyric amber, which means "sung". */
export const SINGER_COLORS = ['#FF8A3D', '#4FD1FF', '#FF6FB5', '#7CE38B'] as const;
