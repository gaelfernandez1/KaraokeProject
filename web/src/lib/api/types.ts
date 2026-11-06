/*
 * What the web app exchanges with the karaoke server. The shapes come from the server's
 * OpenAPI description (`schemas/openapi.json`, generated into `./generated/openapi.ts` by
 * `make contracts`); only what the browser itself builds is written here.
 */
import type { components } from './generated/openapi';

type Schemas = components['schemas'];

/** A song in the library, without its lyrics. */
export type SongSummary = Schemas['SongSummary'];

/** `make` turns a song into a karaoke; `export` renders its MP4. */
export type Job = Schemas['Job'];
export type JobStage = Job['stage'];

export type ExportInput = Schemas['ExportRequest'];

/** Addresses of the server: `url` is the home network's, for the party QR code. */
export type ServerInfo = Schemas['ServerInfo'];

/** Whether this device may create, correct and delete songs, and from where it connects. */
export type Me = Schemas['Me'];
export type Device = Schemas['Device'];
export type Pairing = Schemas['PairingOut'];

export interface CreateJobInput {
	file?: File;
	url?: string;
	language: string;
	lyrics?: string;
	lrclib?: boolean;
	title?: string;
	artist?: string;
}
