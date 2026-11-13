/**
 * The globe's heavy half (the WebGL engine and the reader of the map), fetched only when a
 * screen asks for the globe.
 */
export async function loadGlobe() {
	// Both at once; the two imports below then resolve from the module cache.
	await Promise.all([import('./engine'), import('./map')]);
	const { createScene } = await import('./engine');
	const { buildAtlas, loadMap } = await import('./map');
	return { createScene, buildAtlas, loadMap };
}
