/**
 * Live updates from the server as Server-Sent Events. EventSource reconnects by itself; the
 * server sends the full state again on every connection, so nothing is lost while it was away.
 */
export interface Subscription {
	close(): void;
}

export interface SubscribeOptions {
	onOpen?: () => void;
	/** Called when the connection drops; the browser is already retrying. */
	onError?: () => void;
	/** Tests pass a fake. */
	createSource?: (url: string) => EventSource;
}

export function subscribe(
	url: string,
	handlers: Record<string, (data: unknown) => void>,
	options: SubscribeOptions = {}
): Subscription {
	const source = (options.createSource ?? ((u) => new EventSource(u)))(url);
	for (const [event, handler] of Object.entries(handlers)) {
		source.addEventListener(event, (message) => {
			let data: unknown;
			try {
				data = JSON.parse((message as MessageEvent<string>).data);
			} catch {
				return;
			}
			handler(data);
		});
	}
	if (options.onOpen) source.addEventListener('open', options.onOpen);
	if (options.onError) source.addEventListener('error', options.onError);
	return { close: () => source.close() };
}
