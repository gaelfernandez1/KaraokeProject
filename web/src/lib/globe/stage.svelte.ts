/*
 * The night globe is one picture for the whole app: a canvas behind every screen, drawn by
 * `Stage.svelte`. A screen says where it wants the globe by placing an anchor
 * (`GlobeAnchor.svelte`); going from one screen to another, the globe glides between them.
 */

/** What the globe is doing: at rest, a party, a karaoke being made, or the settings. */
export type Mood = 'calm' | 'party' | 'scan' | 'tech';

export interface Anchor {
	element: HTMLElement;
	/** How the globe rests there, in radians: turned to the east, and its north tipped away. */
	yaw: number;
	tilt: number;
	/** The sphere's radius, as a part of half the anchor's smaller side. */
	fit: number;
	/** Whether the names of the cities and the seas show. */
	names: boolean;
}

const STILL_KEY = 'noite.quieta';

/** The colours of the people of a party, as light (0..1 red, green, blue). */
export const SINGER_LIGHTS: readonly [number, number, number][] = [
	[1, 0.45, 0.66],
	[0.37, 0.89, 0.61],
	[1, 0.6, 0.3],
	[0.78, 0.91, 0.35]
];

function storedStill(): boolean {
	try {
		return localStorage.getItem(STILL_KEY) === '1';
	} catch {
		return false;
	}
}

class Stage {
	/** The anchors on screen; the last one placed is where the globe goes. */
	anchors = $state.raw<Anchor[]>([]);
	/** The globe is being drawn: anchors hide their still drawing. */
	live = $state(false);
	/** The visitor stopped it; remembered on this device. */
	still = $state(typeof localStorage === 'undefined' ? false : storedStill());
	mood = $state<Mood>('calm');
	/** From 0 to 1 while a karaoke is being made: the lights come on up to there. */
	progress = $state<number | null>(null);
	/** A place the page points at (a lighthouse, a town), as angles from the centre. */
	mark = $state.raw<{ theta: number; phi: number } | null>(null);
	/** The visitor's hand on the globe: how far it was turned from rest, and how fast. */
	drag = { yaw: 0, tilt: 0, speedYaw: 0, speedTilt: 0, held: false };
	/** Rockets waiting to go up. */
	rockets: [number, number, number][] = [];

	get anchor(): Anchor | null {
		return this.anchors.at(-1) ?? null;
	}

	/** Places an anchor; the function it returns takes it away. */
	place(anchor: Anchor): () => void {
		this.anchors = [...this.anchors, anchor];
		return () => {
			this.anchors = this.anchors.filter((other) => other !== anchor);
		};
	}

	firework(color: [number, number, number]): void {
		if (this.rockets.length < 12) this.rockets.push(color);
	}

	toggleStill(): void {
		this.still = !this.still;
		try {
			localStorage.setItem(STILL_KEY, this.still ? '1' : '0');
		} catch {
			// Without storage the choice holds for this visit only.
		}
	}
}

export const stage = new Stage();
