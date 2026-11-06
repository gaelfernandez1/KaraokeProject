import { describe, expect, it } from 'vitest';
import { networkOr } from './fallback';

const saved = new Response('saved');
const later = <T>(value: T, ms: number) => new Promise<T>((r) => setTimeout(() => r(value), ms));

describe('networkOr', () => {
	it('answers from the network when the server does', async () => {
		const answer = await networkOr(Promise.resolve(new Response('live')), async () => saved, 100);
		expect(await answer.text()).toBe('live');
	});

	it('uses what is saved when the network fails or takes too long', async () => {
		expect(await networkOr(Promise.reject(new TypeError('offline')), async () => saved, 100)).toBe(
			saved
		);
		expect(await networkOr(later(new Response('slow'), 200), async () => saved, 10)).toBe(saved);
	});

	it('uses what is saved when the tunnel answers but the server behind it is down', async () => {
		const gateway = new Response('Bad Gateway', { status: 502 });
		expect(await networkOr(Promise.resolve(gateway), async () => saved, 100)).toBe(saved);
	});

	it('keeps the server answer when nothing is saved', async () => {
		const gateway = new Response('Bad Gateway', { status: 502 });
		expect((await networkOr(Promise.resolve(gateway), async () => undefined, 100)).status).toBe(
			502
		);
	});

	it('can refuse any answer that is not a success', async () => {
		const missing = new Response('', { status: 404 });
		const ok = (r: Response) => r.ok;
		expect(await networkOr(Promise.resolve(missing), async () => saved, 100, ok)).toBe(saved);
	});
});
