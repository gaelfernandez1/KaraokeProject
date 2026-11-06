/*
 * Moving the focus with the arrow keys, for the TV screen driven from a keyboard or a
 * presentation clicker: the nearest focusable thing in the direction pressed.
 */

export interface Rect {
	x: number;
	y: number;
	w: number;
	h: number;
}

export type Direction = 'up' | 'down' | 'left' | 'right';

/** The id of the candidate to move to from `from`, or null if there is none that way. */
export function nextFocus(
	from: Rect,
	candidates: readonly { id: string; rect: Rect }[],
	direction: Direction
): string | null {
	const cx = from.x + from.w / 2;
	const cy = from.y + from.h / 2;
	const sideways = direction === 'left' || direction === 'right';
	// Something in line (overlapping across the direction pressed) wins over anything off to the
	// side, however close: right from a wide title goes along its row, not to a field below it.
	const inLine = (rect: Rect) =>
		sideways
			? rect.y < from.y + from.h && rect.y + rect.h > from.y
			: rect.x < from.x + from.w && rect.x + rect.w > from.x;
	let best: string | null = null;
	let bestScore = Infinity;
	let bestInLine: string | null = null;
	let bestInLineScore = Infinity;
	for (const { id, rect } of candidates) {
		const x = rect.x + rect.w / 2;
		const y = rect.y + rect.h / 2;
		const dx = x - cx;
		const dy = y - cy;
		// Distance along the direction pressed, and how far off to the side.
		const [along, across] =
			direction === 'left'
				? [-dx, dy]
				: direction === 'right'
					? [dx, dy]
					: direction === 'up'
						? [-dy, dx]
						: [dy, dx];
		if (along <= 1) continue;
		const score = along + 2 * Math.abs(across);
		if (score < bestScore) {
			bestScore = score;
			best = id;
		}
		if (inLine(rect) && score < bestInLineScore) {
			bestInLineScore = score;
			bestInLine = id;
		}
	}
	return bestInLine ?? best;
}

const KEYS: Record<string, Direction> = {
	ArrowUp: 'up',
	ArrowDown: 'down',
	ArrowLeft: 'left',
	ArrowRight: 'right'
};

const FOCUSABLE =
	'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Arrow keys move the focus between the focusable elements inside `root`. Keys a field or a
 * slider needs are left to it (a one-line field lets up and down out, as on a TV). A focus
 * outside `root` is left alone. With nothing focused, the first arrow goes to `first()` (the
 * main content) or else to the first element. Returns a function that stops it.
 */
export function arrowNavigation(
	root: HTMLElement,
	first?: () => HTMLElement | null | undefined
): () => void {
	const onKey = (event: KeyboardEvent) => {
		const direction = KEYS[event.key];
		if (!direction || event.defaultPrevented) return;
		const active = document.activeElement as HTMLElement | null;
		if (active?.matches('input[type="range"], textarea, select')) return;
		const sideways = direction === 'left' || direction === 'right';
		if (sideways && active?.matches('input[type="text"], input[type="search"]')) return;
		const items = [...root.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
			(el) => el.offsetParent !== null
		);
		if (items.length === 0) return;
		if (!active || active === document.body) {
			(first?.() ?? items[0]).focus();
			event.preventDefault();
			return;
		}
		if (!root.contains(active)) return;
		const rect = (el: HTMLElement): Rect => {
			const r = el.getBoundingClientRect();
			return { x: r.left, y: r.top, w: r.width, h: r.height };
		};
		const others = items
			.filter((el) => el !== active)
			.map((el, i) => ({ id: String(i), el, rect: rect(el) }));
		const id = nextFocus(rect(active), others, direction);
		if (id === null) return;
		event.preventDefault();
		others[Number(id)].el.focus();
	};
	window.addEventListener('keydown', onKey);
	return () => window.removeEventListener('keydown', onKey);
}
