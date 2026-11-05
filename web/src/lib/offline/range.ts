/*
 * Byte ranges over a stored response. The Cache API only keeps whole files, but `<video>`
 * seeks with Range requests and Safari will not play media that does not answer them with 206.
 */

const RANGE = /^bytes=(\d*)-(\d*)$/;

/**
 * The bytes a `Range` header asks for in a resource of `size` bytes: null when there is no
 * usable single range (the whole resource is the answer), 'unsatisfiable' when it starts past
 * the end.
 */
export function byteRange(
	rangeHeader: string | null,
	size: number
): { start: number; end: number } | 'unsatisfiable' | null {
	const match = rangeHeader ? RANGE.exec(rangeHeader.trim()) : null;
	if (!match) return null;
	const [, first, last] = match;
	if (!first && !last) return null;
	if (first && last && Number(first) > Number(last)) return null;
	// `bytes=-n` is the last n bytes; otherwise from `first` to `last` (or the end).
	const start = first ? Number(first) : Math.max(0, size - Number(last));
	const end = first && last ? Math.min(Number(last), size - 1) : size - 1;
	if (start >= size) return 'unsatisfiable';
	return { start, end };
}

/**
 * The part of `full` that `rangeHeader` asks for: 206 with that slice, 416 when it starts past
 * the end, or `full` itself when there is no header or one that cannot be read (servers may
 * ignore those, and a single range is all media elements send).
 */
export async function rangeResponse(full: Response, rangeHeader: string | null): Promise<Response> {
	if (full.status !== 200 || byteRange(rangeHeader, Number.MAX_SAFE_INTEGER) === null) return full;
	const blob = await full.blob();
	const size = blob.size;
	const type = full.headers.get('Content-Type');
	const headers = (extra: Record<string, string>) => {
		const result = new Headers(extra);
		result.set('Accept-Ranges', 'bytes');
		if (type) result.set('Content-Type', type);
		return result;
	};
	const range = byteRange(rangeHeader, size);
	if (range === null) return new Response(blob, { status: 200, headers: headers({}) });
	if (range === 'unsatisfiable') {
		return new Response(null, {
			status: 416,
			statusText: 'Range Not Satisfiable',
			headers: headers({ 'Content-Range': `bytes */${size}` })
		});
	}
	const { start, end } = range;
	return new Response(blob.slice(start, end + 1), {
		status: 206,
		statusText: 'Partial Content',
		headers: headers({
			'Content-Range': `bytes ${start}-${end}/${size}`,
			'Content-Length': String(end - start + 1)
		})
	});
}
