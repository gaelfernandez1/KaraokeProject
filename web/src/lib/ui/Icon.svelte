<script lang="ts" module>
	/*
	 * The app's icons, drawn for it on a 24-unit grid with 2-unit round strokes. `songs` is a
	 * lyric sheet with its first line half sung; `party` is a string of festival bulbs.
	 */
	const ICONS = {
		songs:
			'<path d="M4 6h16M4 12h16M4 18h10"/><path d="M4 6h8" stroke="var(--icon-accent, currentColor)" stroke-width="3"/>',
		create: '<path d="M12 5v14M5 12h14"/>',
		party:
			'<path d="M2 5.5q10 8 20 0"/><path d="M6.2 8.6v2.2M12 9.6v2.2M17.8 8.6v2.2" stroke-width="1.6"/><path d="M4.4 12.3a1.8 2.4 0 1 0 3.6 0c0-1-1.8-1.5-1.8-1.5s-1.8.5-1.8 1.5zM10.2 13.3a1.8 2.4 0 1 0 3.6 0c0-1-1.8-1.5-1.8-1.5s-1.8.5-1.8 1.5zM16 12.3a1.8 2.4 0 1 0 3.6 0c0-1-1.8-1.5-1.8-1.5s-1.8.5-1.8 1.5z" fill="currentColor" stroke="none"/>',
		settings:
			'<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
		play: '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/>',
		pause: '<path d="M8 5v14M16 5v14" stroke-width="3"/>',
		back5:
			'<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3"/><path d="M4 3.5v4h4"/><text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="800" fill="currentColor" stroke="none" font-family="var(--font-text)">5</text>',
		forward5:
			'<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M20 3.5v4h-4"/><text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="800" fill="currentColor" stroke="none" font-family="var(--font-text)">5</text>',
		search: '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/>',
		back: '<path d="M15 5l-7 7 7 7"/>',
		close: '<path d="M6 6l12 12M18 6 6 18"/>',
		check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
		edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13 7 4 4"/>',
		download: '<path d="M12 4v11M7 10.5l5 5 5-5M5 20h14"/>',
		fullscreen: '<path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/>',
		exitFullscreen: '<path d="M9 4v5H4M20 9h-5V4M15 20v-5h5M4 15h5v5"/>',
		tv: '<rect x="3" y="5" width="18" height="12" rx="1.5"/><path d="M8 20h8"/>',
		sound:
			'<path d="M4 9.5v5h3.5L12 18V6L7.5 9.5z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
		minus: '<path d="M5 12h14"/>',
		plus: '<path d="M12 5v14M5 12h14"/>',
		upload: '<path d="M12 20V9M7 13.5l5-5 5 5M5 4h14"/>',
		link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
		queue: '<path d="M4 7h11M4 12h11M4 17h7"/><path d="M18 14v6l3-3z" fill="currentColor"/>',
		remote:
			'<rect x="7" y="2.5" width="10" height="19" rx="2.5"/><circle cx="12" cy="8" r="2"/><path d="M10 14h4M10 17h4"/>',
		offline: '<path d="M12 4v10M8 10l4 4 4-4"/><path d="M5 15v4h14v-4"/>',
		skip: '<path d="M6 5.5v13l9-6.5z" fill="currentColor"/><path d="M18 5v14"/>',
		loop: '<path d="M17 4l3 3-3 3"/><path d="M4 12V10a3 3 0 0 1 3-3h13M7 20l-3-3 3-3"/><path d="M20 12v2a3 3 0 0 1-3 3H4"/>',
		undo: '<path d="M9 5 4 10l5 5"/><path d="M4 10h10a6 6 0 0 1 0 12h-3"/>',
		redo: '<path d="m15 5 5 5-5 5"/><path d="M20 10H10a6 6 0 0 0 0 12h3"/>',
		tap: '<circle cx="12" cy="12" r="3" fill="currentColor"/><circle cx="12" cy="12" r="7"/>',
		trash: '<path d="M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13"/>'
	} as const;

	export type IconName = keyof typeof ICONS;
</script>

<script lang="ts">
	interface Props {
		name: IconName;
		/** Size in em, so icons follow the text they sit in. */
		size?: number;
		/** Accessible name; without it the icon is decoration. */
		label?: string;
	}

	let { name, size = 1.5, label }: Props = $props();
</script>

<svg
	class="icon"
	viewBox="0 0 24 24"
	width="{size}em"
	height="{size}em"
	fill="none"
	stroke="currentColor"
	stroke-width="2"
	stroke-linecap="round"
	stroke-linejoin="round"
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
>
	<!-- eslint-disable-next-line svelte/no-at-html-tags -- static, hand-written markup above -->
	{@html ICONS[name]}
</svg>

<style>
	.icon {
		flex: none;
		display: inline-block;
		vertical-align: middle;
	}
</style>
