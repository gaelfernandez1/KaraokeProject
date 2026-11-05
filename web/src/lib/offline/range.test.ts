import { describe, expect, it } from 'vitest';
import { byteRange, rangeResponse } from './range';

const SIZE = 1000;
// Every byte differs from its neighbours, so a slice taken from the wrong place shows.
const BODY = Uint8Array.from({ length: SIZE }, (_, i) => (i * 7) % 251);

const full = () => new Response(BODY, { status: 200, headers: { 'Content-Type': 'video/mp4' } });

async function bytes(response: Response): Promise<number[]> {
	return Array.from(new Uint8Array(await response.arrayBuffer()));
}

describe('rangeResponse', () => {
	it('answers the whole file as it is without a Range header', async () => {
		const response = await rangeResponse(full(), null);
		expect(response.status).toBe(200);
		expect(await bytes(response)).toEqual(Array.from(BODY));
	});

	it('answers a closed range with 206 and the matching headers', async () => {
		const response = await rangeResponse(full(), 'bytes=100-199');
		expect(response.status).toBe(206);
		expect(response.headers.get('Content-Range')).toBe('bytes 100-199/1000');
		expect(response.headers.get('Content-Length')).toBe('100');
		expect(response.headers.get('Accept-Ranges')).toBe('bytes');
		expect(response.headers.get('Content-Type')).toBe('video/mp4');
		expect(await bytes(response)).toEqual(Array.from(BODY.slice(100, 200)));
	});

	it('answers an open range up to the end', async () => {
		const response = await rangeResponse(full(), 'bytes=990-');
		expect(response.status).toBe(206);
		expect(response.headers.get('Content-Range')).toBe('bytes 990-999/1000');
		expect(await bytes(response)).toEqual(Array.from(BODY.slice(990)));
	});

	it('answers the first byte, as media elements ask for first', async () => {
		const response = await rangeResponse(full(), 'bytes=0-');
		expect(response.status).toBe(206);
		expect(response.headers.get('Content-Range')).toBe('bytes 0-999/1000');
		expect(response.headers.get('Content-Length')).toBe('1000');
	});

	it('answers a suffix range with the last bytes', async () => {
		const response = await rangeResponse(full(), 'bytes=-10');
		expect(response.status).toBe(206);
		expect(response.headers.get('Content-Range')).toBe('bytes 990-999/1000');
		expect(await bytes(response)).toEqual(Array.from(BODY.slice(990)));
	});

	it('clamps a range or suffix longer than the file', async () => {
		const end = await rangeResponse(full(), 'bytes=900-5000');
		expect(end.headers.get('Content-Range')).toBe('bytes 900-999/1000');
		const suffix = await rangeResponse(full(), 'bytes=-5000');
		expect(suffix.headers.get('Content-Range')).toBe('bytes 0-999/1000');
		expect((await bytes(suffix)).length).toBe(SIZE);
	});

	it('answers 416 with the size when the range starts past the end', async () => {
		for (const header of ['bytes=1000-', 'bytes=2000-3000', 'bytes=-0']) {
			const response = await rangeResponse(full(), header);
			expect(response.status, header).toBe(416);
			expect(response.headers.get('Content-Range')).toBe('bytes */1000');
		}
	});

	it('ignores a Range header it cannot read, as servers may', async () => {
		for (const header of ['items=0-10', 'bytes=abc', 'bytes=20-10', 'bytes=0-1,5-6']) {
			const response = await rangeResponse(full(), header);
			expect(response.status, header).toBe(200);
		}
	});

	it('leaves a response that is not a 200 alone', async () => {
		const missing = new Response('nope', { status: 404 });
		expect((await rangeResponse(missing, 'bytes=0-1')).status).toBe(404);
	});
});

describe('byteRange', () => {
	it('reads the three forms of a single range', () => {
		expect(byteRange('bytes=0-99', 1000)).toEqual({ start: 0, end: 99 });
		expect(byteRange('bytes=900-', 1000)).toEqual({ start: 900, end: 999 });
		expect(byteRange('bytes=-100', 1000)).toEqual({ start: 900, end: 999 });
	});

	it('clamps a suffix longer than the resource and an end past it', () => {
		expect(byteRange('bytes=-5000', 1000)).toEqual({ start: 0, end: 999 });
		expect(byteRange('bytes=10-5000', 1000)).toEqual({ start: 10, end: 999 });
	});

	it('tells apart no range and a range past the end', () => {
		expect(byteRange(null, 1000)).toBeNull();
		expect(byteRange('bytes=-', 1000)).toBeNull();
		expect(byteRange('bytes=1000-', 1000)).toBe('unsatisfiable');
	});
});
