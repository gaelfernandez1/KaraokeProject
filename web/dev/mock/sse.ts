import type { IncomingMessage, ServerResponse } from 'node:http';

/** Opens a Server-Sent Events stream; returns a sender and calls `onClose` when the client goes. */
export function openStream(
	req: IncomingMessage,
	res: ServerResponse,
	onClose: () => void
): (event: string, data: unknown) => void {
	res.writeHead(200, {
		'Content-Type': 'text/event-stream; charset=utf-8',
		'Cache-Control': 'no-cache, no-transform',
		Connection: 'keep-alive',
		// Proxies must not buffer the stream.
		'X-Accel-Buffering': 'no'
	});
	res.write(': open\n\n');
	// A comment now and then keeps idle connections from being cut by proxies and phones.
	const ping = setInterval(() => res.write(': ping\n\n'), 15_000);
	req.on('close', () => {
		clearInterval(ping);
		onClose();
	});
	return (event, data) => {
		res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
	};
}
