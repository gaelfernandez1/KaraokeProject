<script lang="ts">
	// Said where the server refused because this device is not paired: what to do about it.
	import { resolve } from '$app/paths';
	import { i18n } from '#lib/i18n';

	let { text }: { text: string } = $props();
</script>

<p class="notice" role="alert">
	{text}
	<a href={resolve('/axustes#aparello')}>{i18n.t.device.goPair}</a>
</p>

<style>
	.notice {
		max-width: 40rem;
		font-weight: 700;
	}

	a {
		color: var(--farol);
		white-space: nowrap;
	}
</style>
