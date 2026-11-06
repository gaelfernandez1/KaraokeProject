interface LoadableFace {
	load(): Promise<unknown>;
}

const loading = new Map<string, Promise<unknown>>();

/**
 * Loads a theme font and adds it to the page once. The party TV mounts the lyrics again for
 * every song: a new FontFace each time would pile up copies of the same font all night.
 */
export function loadFontOnce(
	family: string,
	url: string,
	make: (family: string, source: string) => LoadableFace = (f, s) => new FontFace(f, s),
	fonts: { add(face: never): unknown } = document.fonts
): Promise<unknown> {
	const key = `${family}\n${url}`;
	let promise = loading.get(key);
	if (!promise) {
		promise = make(family, `url(${url})`)
			.load()
			.then((face) => {
				fonts.add(face as never);
				return face;
			});
		// A failed load may work later (back online): it is not kept.
		promise.catch(() => loading.delete(key));
		loading.set(key, promise);
	}
	return promise;
}
