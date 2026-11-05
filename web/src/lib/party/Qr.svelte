<script lang="ts">
	// A QR code drawn as one SVG path: sharp at any size, from a phone to a 4K TV.
	import { generate } from 'lean-qr';
	import { toSvgPath } from 'lean-qr/extras/svg';

	interface Props {
		text: string;
		label: string;
	}

	let { text, label }: Props = $props();
	const code = $derived(generate(text));
	const path = $derived(toSvgPath(code));
</script>

<svg
	class="qr"
	viewBox="-3 -3 {code.size + 6} {code.size + 6}"
	role="img"
	aria-label={label}
	shape-rendering="crispEdges"
>
	<rect x="-3" y="-3" width={code.size + 6} height={code.size + 6} fill="var(--papel)" />
	<path d={path} fill="var(--noite)" />
</svg>

<style>
	.qr {
		display: block;
		width: 100%;
		height: auto;
	}
</style>
