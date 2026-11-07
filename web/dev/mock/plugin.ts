import { createReadStream, statSync } from 'node:fs';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { networkInterfaces } from 'node:os';
import { extname, resolve } from 'node:path';
import type { Plugin } from 'vite';
import type { KaraokeDoc } from '../../src/lib/contracts/generated/karaoke.ts';
import type { ExportInput } from '../../src/lib/api/types.ts';
import type {
	PartyCommand,
	PartySettings,
	Playback,
	QueueItemState
} from '../../src/lib/party/types.ts';
import { Jobs } from './jobs.ts';
import { Library, MEDIA_TYPES } from './library.ts';
import { Parties } from './party.ts';
import { openStream } from './sse.ts';
import { byteRange } from '../../src/lib/offline/range.ts';

export interface MockOptions {
	/** Package folders; default: KARAOKE_PACKAGES (colon-separated) or the repo's examples. */
	dirs?: string[];
	/** How long a pretend job takes; default: KARAOKE_MOCK_JOB_SECONDS or 12. */
	jobSeconds?: number;
}

type Req = IncomingMessage;
type Res = ServerResponse;

function send(res: Res, status: number, body?: unknown): void {
	res.statusCode = status;
	if (body === undefined) {
		res.end();
		return;
	}
	res.setHeader('Content-Type', 'application/json; charset=utf-8');
	res.end(JSON.stringify(body));
}

const notFound = (res: Res) => send(res, 404, { detail: 'Not found' });

async function readJson<T>(req: Req): Promise<T> {
	const chunks: Buffer[] = [];
	for await (const chunk of req) chunks.push(chunk as Buffer);
	return JSON.parse(Buffer.concat(chunks).toString('utf8') || 'null') as T;
}

/** Parses a multipart (or urlencoded) body with the platform's own Request. */
async function readForm(req: Req): Promise<FormData> {
	const request = new Request('http://mock.local/', {
		method: 'POST',
		headers: req.headers as Record<string, string>,
		body: req as unknown as ReadableStream,
		duplex: 'half'
	} as RequestInit);
	return request.formData();
}

/** Serves a file, with byte ranges: browsers seek in videos with them. */
function serveFile(req: Req, res: Res, path: string): void {
	const size = statSync(path).size;
	res.setHeader('Content-Type', MEDIA_TYPES[extname(path)] ?? 'application/octet-stream');
	res.setHeader('Accept-Ranges', 'bytes');
	res.setHeader('Cache-Control', 'no-cache');
	const range = byteRange(req.headers.range ?? null, size);
	if (range === 'unsatisfiable') {
		res.statusCode = 416;
		res.setHeader('Content-Range', `bytes */${size}`);
		res.end();
		return;
	}
	if (range) {
		res.statusCode = 206;
		res.setHeader('Content-Range', `bytes ${range.start}-${range.end}/${size}`);
		res.setHeader('Content-Length', range.end - range.start + 1);
		createReadStream(path, range).pipe(res);
		return;
	}
	res.setHeader('Content-Length', size);
	createReadStream(path).pipe(res);
}

function lanAddress(): string {
	for (const addresses of Object.values(networkInterfaces())) {
		for (const address of addresses ?? []) {
			if (address.family === 'IPv4' && !address.internal) return address.address;
		}
	}
	return 'localhost';
}

/**
 * The stand-in has no pairing of its own: every browser is the owner, except one carrying the
 * `karaoke_mock_visitor` cookie (tests set it), until it pairs with the code below.
 */
const MOCK_PAIRING_CODE = 'BCDFGHJK';
const visitor = (req: Req): boolean =>
	/(?:^|;\s*)karaoke_mock_visitor=1/.test(req.headers.cookie ?? '');
const notOwner = (res: Res) =>
	send(res, 403, { detail: 'Only a paired device can do this', code: 'not_owner' });

const bearer = (req: Req, url: URL): string =>
	(req.headers.authorization ?? '').replace(/^Bearer /, '') || url.searchParams.get('token') || '';

/**
 * Dev-server stand-in for the karaoke server: the same /api and /media routes the web app uses,
 * over the package folders on disk, with pretend jobs and party rooms in memory. Dev only.
 */
export function mockApi(options: MockOptions = {}): Plugin {
	return {
		name: 'karaoke-mock-api',
		configureServer(server) {
			// Vitest starts a Vite server too; tests use the stores directly.
			if (process.env.VITEST) return;
			const root = resolve(server.config.root, '..');
			const dirs =
				options.dirs ??
				(process.env.KARAOKE_PACKAGES
					? process.env.KARAOKE_PACKAGES.split(':')
					: [resolve(root, 'fixtures/packages'), resolve(root, 'bench/data/paquetes')]);
			const library = new Library(dirs);
			const jobs = new Jobs(library, {
				seconds: options.jobSeconds ?? (Number(process.env.KARAOKE_MOCK_JOB_SECONDS) || 12)
			});
			const parties = new Parties(library);
			const timer = setInterval(() => jobs.tick(), 200);
			timer.unref();
			server.httpServer?.on('close', () => clearInterval(timer));

			server.middlewares.use('/media', (req, res, next) => {
				const url = new URL(req.url ?? '/', 'http://mock.local');
				const [id, ...rest] = decodeURIComponent(url.pathname).split('/').filter(Boolean);
				const file = rest.join('/');
				if (!id || !file) return next();
				// As the server: `download` saves the file, under `name` if given.
				if (url.searchParams.has('download')) {
					const name = url.searchParams.get('name') || file.split('/').pop() || file;
					res.setHeader(
						'Content-Disposition',
						`attachment; filename*=utf-8''${encodeURIComponent(name)}`
					);
				}
				if (file === 'karaoke.json') {
					const doc = library.doc(id);
					return doc ? send(res, 200, doc) : notFound(res);
				}
				const path = file.startsWith('exports/')
					? library.exportFile(id, file)
					: library.filePath(id, file);
				return path ? serveFile(req, res, path) : notFound(res);
			});

			server.middlewares.use('/api', async (req, res, next) => {
				const url = new URL(req.url ?? '/', 'http://mock.local');
				const parts = url.pathname.split('/').filter(Boolean).map(decodeURIComponent);
				const method = req.method ?? 'GET';
				try {
					const writes = method !== 'GET' && ['songs', 'jobs'].includes(parts[0]);
					if (writes && visitor(req)) return notOwner(res);
					if (parts[0] === 'me' && method === 'GET') {
						return send(res, 200, {
							owner: !visitor(req),
							zone: visitor(req) ? 'home' : 'local',
							device: null
						});
					}
					// /api/devices…
					if (parts[0] === 'devices') {
						if (parts[1] === 'pairing' && method === 'POST') {
							if (visitor(req)) return notOwner(res);
							const address = server.httpServer?.address();
							const port = typeof address === 'object' && address ? address.port : 5173;
							return send(res, 200, {
								code: MOCK_PAIRING_CODE,
								expires_at: new Date(Date.now() + 600_000).toISOString(),
								urls: {
									home: `http://${lanAddress()}:${port}/vincular?code=${MOCK_PAIRING_CODE}`,
									remote: null
								}
							});
						}
						if (parts[1] === 'pair' && method === 'POST') {
							const { code } = await readJson<{ code: string }>(req);
							if ((code ?? '').replace(/[\s-]/g, '').toUpperCase() !== MOCK_PAIRING_CODE) {
								return send(res, 422, { detail: 'That code is wrong', code: 'bad_code' });
							}
							res.setHeader('Set-Cookie', 'karaoke_mock_visitor=; Max-Age=0; Path=/');
							const now = new Date().toISOString();
							return send(res, 200, { id: 'd1', name: 'Device', created_at: now, last_seen: now });
						}
						if (parts.length === 1 && method === 'GET') return send(res, 200, []);
						if (parts.length === 2 && method === 'DELETE') return send(res, 204);
					}
					// /api/songs…
					if (parts[0] === 'songs') {
						if (parts.length === 1 && method === 'GET') return send(res, 200, library.list());
						const id = parts[1];
						if (parts.length === 2 && method === 'DELETE') {
							return library.delete(id) ? send(res, 204) : notFound(res);
						}
						if (parts[2] === 'doc' && method === 'PUT') {
							if (!library.doc(id)) return notFound(res);
							return send(res, 200, library.saveDoc(id, await readJson<KaraokeDoc>(req)));
						}
						if (parts[2] === 'exports') {
							if (!library.doc(id)) return notFound(res);
							if (parts.length === 3 && method === 'GET') {
								return send(res, 200, library.exports(id));
							}
							if (parts.length === 3 && method === 'POST') {
								return send(
									res,
									201,
									jobs.createExport(id, await readJson<Partial<ExportInput>>(req))
								);
							}
							if (parts.length === 4 && method === 'DELETE') {
								return library.deleteExport(id, parts[3]) ? send(res, 204) : notFound(res);
							}
						}
					}
					// /api/jobs…
					if (parts[0] === 'jobs') {
						if (parts.length === 1 && method === 'GET') return send(res, 200, jobs.list());
						if (parts.length === 1 && method === 'POST') {
							const form = await readForm(req);
							const file = form.get('file');
							const text = (key: string) => {
								const value = form.get(key);
								return typeof value === 'string' && value.trim() ? value : undefined;
							};
							const language = text('language');
							if (!language || (!text('url') && !(file instanceof File))) {
								return send(res, 422, { detail: 'language and a file or a url are required' });
							}
							const job = jobs.create({
								url: text('url'),
								fileName: file instanceof File ? file.name : undefined,
								language,
								lyrics: text('lyrics'),
								lrclib: text('lrclib') === 'true',
								title:
									text('title') ??
									(file instanceof File ? file.name.replace(/\.[^.]+$/, '') : undefined),
								artist: text('artist')
							});
							return send(res, 201, job);
						}
						const job = jobs.get(parts[1]);
						if (!job) return notFound(res);
						if (parts.length === 2 && method === 'GET') return send(res, 200, job);
						if (parts[2] === 'retry' && method === 'POST') {
							const again = jobs.retry(job.id);
							return again
								? send(res, 200, again)
								: send(res, 409, { detail: 'Cannot retry', code: 'not_retryable' });
						}
						if (parts.length === 2 && method === 'DELETE') {
							jobs.cancel(job.id);
							return send(res, 204);
						}
						if (parts[2] === 'events') {
							let stop = () => {};
							const emit = openStream(req, res, () => stop());
							emit('job', job);
							stop = jobs.subscribe(job.id, (changed) => emit('job', changed));
							return;
						}
					}
					// /api/parties…
					if (parts[0] === 'parties') {
						if (parts.length === 1 && method === 'POST') return send(res, 201, parties.create());
						const code = parts[1];
						const state = parties.get(code);
						if (!state) return notFound(res);
						const who = bearer(req, url);
						const ok = (done: unknown) =>
							done ? send(res, 204) : send(res, 403, { detail: 'Not allowed' });
						if (parts.length === 2 && method === 'GET') return send(res, 200, state);
						if (parts.length === 2 && method === 'DELETE') return ok(parties.end(code, who));
						switch (`${method} ${parts[2]}`) {
							case 'GET events': {
								const unsubscribe: (() => void)[] = [];
								const emit = openStream(req, res, () => unsubscribe.forEach((stop) => stop()));
								const stop = parties.subscribe(code, who || null, (event, data) => {
									emit(event, data);
									if (event === 'ended') res.end();
								});
								if (stop) unsubscribe.push(stop);
								return;
							}
							case 'POST guests': {
								const { name } = await readJson<{ name: string }>(req);
								const joined = parties.join(code, name ?? '');
								return joined
									? send(res, 201, joined)
									: send(res, 422, { detail: 'A name is needed' });
							}
							case 'POST queue': {
								const { song_id } = await readJson<{ song_id: string }>(req);
								const item = parties.enqueue(code, who, song_id);
								return item ? send(res, 201, item) : send(res, 403, { detail: 'Not allowed' });
							}
							case 'DELETE queue':
								return ok(parties.remove(code, who, parts[3]));
							case 'POST promote':
								return ok(parties.promote(code, who, parts[3]));
							case 'PUT advance': {
								const body = await readJson<{ item_id: string; state: QueueItemState }>(req);
								return ok(parties.advance(code, who, body.item_id, body.state));
							}
							case 'POST commands':
								return ok(parties.command(code, who, await readJson<PartyCommand>(req)));
							case 'PUT playback':
								return ok(parties.publishPlayback(code, who, await readJson<Playback>(req)));
							case 'PUT settings':
								return ok(parties.updateSettings(code, who, await readJson<PartySettings>(req)));
						}
					}
					if (parts[0] === 'server' && method === 'GET') {
						const address = server.httpServer?.address();
						const port = typeof address === 'object' && address ? address.port : 5173;
						const url = `http://${lanAddress()}:${port}`;
						return send(res, 200, { url, home_url: url, remote_url: null, home_reachable: true });
					}
				} catch (error) {
					return send(res, 400, { detail: String(error) });
				}
				next();
			});
		}
	};
}
