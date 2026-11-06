/** Rejects if `promise` has not settled after `ms`. */
export function within<T>(promise: Promise<T>, ms: number): Promise<T> {
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => reject(new Error('The server did not answer in time')), ms);
		promise.then(resolve, reject).finally(() => clearTimeout(timer));
	});
}

/** A server error means the karaoke server is down even if something (a tunnel) answered. */
const serverUp = (response: Response) => response.status < 500;

/**
 * The network's answer if it comes in time and is `usable`; otherwise what `saved()` has, or the
 * network's own answer when nothing is saved. Away from home, Tailscale answers 502 when the
 * laptop is on but the karaoke server is not: that must not hide the songs saved on the phone.
 */
export async function networkOr(
	network: Promise<Response>,
	saved: () => Promise<Response | undefined>,
	timeoutMs: number,
	usable: (response: Response) => boolean = serverUp
): Promise<Response> {
	let answer: Response | undefined;
	try {
		answer = await within(network, timeoutMs);
		if (usable(answer)) return answer;
	} catch (error) {
		network.catch(() => {
			// Answered from the device instead.
		});
		const stored = await saved();
		if (stored) return stored;
		throw error;
	}
	return (await saved()) ?? answer;
}
