import {
	scrollFocus,
	scrollOffset,
	scrollOpacity,
	type BreakBar,
	type Dot,
	type Layout
} from './layout';

export interface SceneState {
	/** Groups on screen with their opacity (fades in and out like ASS `\fad`). */
	groups: { index: number; opacity: number }[];
	/** Countdown dots still lit. */
	dots: Dot[];
	/** The break bar on screen, if any, and how full it is (0–1). */
	bar: { bar: BreakBar; progress: number } | null;
	/** Scroll mode: how far down the list is drawn (px); 0 in pages mode. */
	offset: number;
}

/**
 * What is on screen at song time `t` (already including the anticipation). Pure: it depends only
 * on `t`, so seeking or pausing shows the right state at once.
 */
export function sceneAt(layout: Layout, t: number, transition: number): SceneState {
	const groups: SceneState['groups'] = [];
	const plan = layout.scroll;
	const focus = plan ? scrollFocus(plan, t) : 0;
	for (const g of layout.groups) {
		if (t < g.show || t >= g.hide) continue;
		let opacity: number;
		if (plan) {
			// Scroll mode: the further from the line being sung, the fainter.
			opacity = scrollOpacity(g.index - focus, plan.visible);
		} else {
			const fade = Math.min(transition, (g.hide - g.show) / 2);
			opacity = fade > 0 ? Math.min(1, (t - g.show) / fade, (g.hide - t) / fade) : 1;
		}
		groups.push({ index: g.index, opacity });
	}
	const dots: Dot[] = [];
	for (const c of layout.countdowns) {
		if (t < c.start || t >= c.end) continue;
		for (const d of c.dots) if (t < d.off) dots.push(d);
	}
	let bar: SceneState['bar'] = null;
	for (const b of layout.bars) {
		if (t >= b.start && t < b.end) bar = { bar: b, progress: (t - b.start) / (b.end - b.start) };
	}
	return { groups, dots, bar, offset: plan ? scrollOffset(plan, t) : 0 };
}
