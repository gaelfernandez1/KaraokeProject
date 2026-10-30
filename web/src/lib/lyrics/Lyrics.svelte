<script lang="ts">
	/*
	 * Animated karaoke lyrics that follow a playback clock. Svelte builds the rows of the groups on
	 * (or about to come on) screen; a requestAnimationFrame loop then only writes opacities and the
	 * fill edge of each row (a clip on a second, sung-colour copy of the text), so a frame never
	 * creates nodes or triggers layout. Everything on screen is a pure function of the clock time,
	 * so seeking and pausing show the right state at once.
	 */
	import type { KaraokeDoc, PlaybackClock, Theme } from '#lib/contracts';
	import type { Attachment } from 'svelte/attachments';
	import { fillSegments, fillX, type FillSegment } from './fill';
	import { buildLayout, type BreakBar, type Dot, type Row } from './layout';
	import { sceneAt } from './scene';
	import { fontFaceFor, metricsFor } from './themes';

	interface Props {
		doc: KaraokeDoc;
		theme: Theme;
		clock: PlaybackClock;
	}

	let { doc, theme, clock }: Props = $props();

	/** Groups are put in the DOM this long before they show, so they are measured in time. */
	const PRELOAD = 2;

	let width = $state(0);
	let height = $state(0);
	const metrics = $derived(metricsFor(theme));
	const layout = $derived(
		width > 0 && height > 0 ? buildLayout(doc, theme, width, height, metrics) : null
	);

	// Raw: compared by identity every frame, so they must not be wrapped in proxies.
	let mounted = $state.raw<number[]>([]);
	let dots = $state.raw<Dot[]>([]);
	let bar = $state.raw<BreakBar | null>(null);
	let barFill = $state<HTMLElement | null>(null);
	let list = $state<HTMLElement | null>(null);

	interface RowView {
		row: Row;
		group: number;
		element: HTMLElement;
		base: HTMLElement;
		sung: HTMLElement;
		segments: FillSegment[] | null;
		alpha: number;
		opacity: number;
		fill: number;
	}
	// Plain Set on purpose: rows register here for the frame loop, which nothing renders from.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	const views = new Set<RowView>();
	/** Set when rows come or go or are measured again: the next frame must draw even if paused. */
	let dirty = true;

	function measure(view: RowView) {
		const parts = view.base.querySelectorAll<HTMLElement>('[data-part]');
		const boxes = Array.from(parts, (p) => ({
			x0: p.offsetLeft,
			x1: p.offsetLeft + p.offsetWidth
		}));
		view.segments = fillSegments(view.row, boxes, theme.animation.fill);
		view.fill = -1;
		dirty = true;
	}

	function rowView(row: Row, group: number): Attachment<HTMLElement> {
		return (element) => {
			const view: RowView = {
				row,
				group,
				element,
				base: element.querySelector('.base') as HTMLElement,
				sung: element.querySelector('.sung') as HTMLElement,
				segments: null,
				alpha: row.role === 'backing' ? theme.backing.opacity : 1,
				opacity: -1,
				fill: -1
			};
			measure(view);
			views.add(view);
			return () => {
				views.delete(view);
				dirty = true;
			};
		};
	}

	// The theme's font: measured rows must be measured again once it arrives.
	$effect(() => {
		const face = fontFaceFor(theme);
		if (!face) return;
		const font = new FontFace(face.family, `url(${face.url})`);
		let cancelled = false;
		font
			.load()
			.then((loaded) => {
				if (cancelled) return;
				document.fonts.add(loaded);
				for (const view of views) measure(view);
			})
			.catch(() => {
				// The fallback font still shows the lyrics; the fill follows its measurements.
			});
		return () => {
			cancelled = true;
		};
	});

	const same = (a: unknown[], b: unknown[]) =>
		a.length === b.length && a.every((x, i) => x === b[i]);

	$effect(() => {
		const current = layout;
		if (!current) return;
		const transition = theme.animation.transition;
		const anticipation = theme.animation.anticipation;
		let lastT = Number.NaN;
		let lastOffset = Number.NaN;
		let frame = requestAnimationFrame(function tick() {
			frame = requestAnimationFrame(tick);
			const t = clock.now() + anticipation;
			if (t === lastT && !dirty) return;
			lastT = t;
			dirty = false;
			const scene = sceneAt(current, t, transition);
			if (list && scene.offset !== lastOffset) {
				lastOffset = scene.offset;
				list.style.transform = `translateY(${scene.offset}px)`;
			}

			const wanted = current.groups
				.filter((g) => g.hide > t && g.show <= t + PRELOAD)
				.map((g) => g.index);
			if (!same(wanted, mounted)) mounted = wanted;
			if (!same(scene.dots, dots)) dots = scene.dots;
			if ((scene.bar?.bar ?? null) !== bar) {
				bar = scene.bar?.bar ?? null;
				// Its fill element only exists after Svelte draws it: fill it on the next frame.
				dirty = true;
			}
			if (scene.bar && barFill) {
				barFill.style.clipPath = `inset(0 ${(1 - scene.bar.progress) * 100}% 0 0)`;
			}

			const opacity = new Map(scene.groups.map((g) => [g.index, g.opacity]));
			for (const view of views) {
				// Backing rows are fainter as a whole, like a single colour in libass.
				const o = (opacity.get(view.group) ?? 0) * view.alpha;
				if (o !== view.opacity) {
					view.opacity = o;
					view.element.style.opacity = String(o);
				}
				if (!view.segments) continue;
				const x = fillX(view.segments, t);
				if (Math.abs(x - view.fill) > 0.05) {
					view.fill = x;
					view.sung.style.setProperty('--fill', `${x}px`);
				}
			}
		});
		return () => cancelAnimationFrame(frame);
	});

	const colors = $derived(theme.colors);
	const shadow = $derived.by(() => {
		const l = theme.layout;
		if (!colors.shadow) return 'none';
		if (l.outline_width > 0 && l.shadow_offset > 0) {
			const o = `${l.shadow_offset}em`;
			return `drop-shadow(${o} ${o} ${l.shadow_blur}em ${colors.shadow})`;
		}
		return 'none';
	});
	const glow = $derived(
		theme.layout.outline_width === 0 && colors.shadow && theme.layout.shadow_blur > 0
			? `0 0 ${2 * theme.layout.shadow_blur}em ${colors.shadow}`
			: 'none'
	);
</script>

{#snippet text(row: Row, marked: boolean)}
	{#each row.words as word, w (w)}<span class="word"
			>{w > 0 ? ' ' : ''}{#each word.parts as part, p (p)}{#if marked}<span data-part
						>{part.text}</span
					>{:else}<span>{part.text}</span>{/if}{/each}</span
		>{/each}
{/snippet}

<div
	class="lyrics"
	role="region"
	aria-label={doc.title}
	bind:clientWidth={width}
	bind:clientHeight={height}
	style:--font={`"${theme.font.family}", system-ui, sans-serif`}
	style:--unsung={colors.unsung}
	style:--outline={colors.box ? 'transparent' : colors.outline}
	style:--stroke={colors.box ? '0' : `${2 * theme.layout.outline_width}em`}
	style:--box={colors.box ?? 'transparent'}
	style:--pad={colors.box ? '0.18em' : '0'}
	style:--shadow={shadow}
	style:--glow={glow}
>
	{#if layout}
		{#key layout}
			<!-- Scroll mode moves this list; in pages mode it stays put. -->
			<div class="list" bind:this={list}>
				{#each layout.groups.filter((g) => mounted.includes(g.index)) as group (group.index)}
					{#each group.rows as row, r (r)}
						<div
							class="row"
							class:backing={row.role === 'backing'}
							data-testid={`row-${row.line_id}-${group.rows.slice(0, r).filter((o) => o.line_id === row.line_id).length}`}
							style:left={`${row.x}px`}
							style:top={`${row.y - row.height / 2}px`}
							style:height={`${row.height}px`}
							style:line-height={`${row.height}px`}
							style:font-size={`${layout.font_px * row.scale}px`}
							style:--sung={row.color}
							style:opacity="0"
							{@attach rowView(row, group.index)}
						>
							<span class="base">{@render text(row, true)}</span>
							<span class="sung" aria-hidden="true">{@render text(row, false)}</span>
						</div>
					{/each}
				{/each}
			</div>
			{#each dots as dot (dot)}
				{@const border = theme.layout.outline_width * layout.font_px}
				<!-- The border goes outside the circle, as libass draws it. -->
				<div
					class="dot"
					style:left={`${dot.x - dot.r - border}px`}
					style:top={`${dot.y - dot.r - border}px`}
					style:width={`${2 * dot.r}px`}
					style:height={`${2 * dot.r}px`}
					style:border-width={`${border}px`}
					style:background={colors.sung}
				></div>
			{/each}
			{#if bar}
				<div
					class="bar"
					style:left={`${bar.x - bar.width / 2}px`}
					style:top={`${bar.y - bar.height / 2}px`}
					style:width={`${bar.width}px`}
					style:height={`${bar.height}px`}
				>
					<div class="bar-fill" style:background={colors.sung} bind:this={barFill}></div>
				</div>
			{/if}
		{/key}
	{/if}
</div>

<style>
	.lyrics {
		position: absolute;
		inset: 0;
		overflow: hidden;
		pointer-events: none;
		font-family: var(--font);
		font-weight: 400;
		font-synthesis: none;
		font-kerning: normal;
		-webkit-font-smoothing: antialiased;
	}

	.list {
		position: absolute;
		inset: 0;
		will-change: transform;
	}

	.row {
		position: absolute;
		transform: translateX(-50%);
		white-space: nowrap;
	}

	.base,
	.sung {
		display: block;
		padding: 0 var(--pad);
		-webkit-text-stroke: var(--stroke) var(--outline);
		paint-order: stroke fill;
	}

	.base {
		color: var(--unsung);
		background: var(--box);
		filter: var(--shadow);
		text-shadow: var(--glow);
	}

	.sung {
		position: absolute;
		inset: 0;
		color: var(--sung);
		/* Everything left of the fill edge, with room for the outline above, below and left. */
		clip-path: inset(-50% calc(100% - var(--fill, 0px)) -50% -50%);
	}

	.dot {
		position: absolute;
		box-sizing: content-box;
		border-radius: 50%;
		border-style: solid;
		border-color: var(--outline);
		background-clip: padding-box;
	}

	.bar {
		position: absolute;
		border-radius: 999px;
		overflow: hidden;
		background: color-mix(in srgb, var(--unsung) 40%, transparent);
	}

	.bar-fill {
		position: absolute;
		inset: 0;
		clip-path: inset(0 100% 0 0);
	}
</style>
