<script lang="ts">
	// Settings, «This device»: what it may do and, on the owner's devices, pairing another one.
	import {
		ApiError,
		listDevices,
		pairDevice,
		revokeDevice,
		startPairing,
		type Device,
		type Pairing
	} from '#lib/api';
	import { i18n } from '#lib/i18n';
	import Qr from '#lib/party/Qr.svelte';
	import Button from '#lib/ui/Button.svelte';
	import { owner } from './owner.svelte.js';

	const t = $derived(i18n.t.device);
	let pairing = $state<Pairing | null>(null);
	let devices = $state<Device[]>([]);
	let code = $state('');
	let busy = $state(false);
	let message = $state<string | null>(null);

	const status = $derived.by(() => {
		const me = owner.me;
		if (!me) return null;
		if (me.zone === 'local') return t.local;
		if (me.owner) return t.owner;
		return me.zone === 'home' ? t.home : t.remote;
	});

	async function loadDevices() {
		if (!owner.isOwner) return;
		try {
			devices = await listDevices();
		} catch {
			devices = [];
		}
	}

	$effect(() => {
		void owner.refresh().then(loadDevices);
	});

	async function newPairing() {
		busy = true;
		try {
			pairing = await startPairing();
		} catch {
			message = i18n.t.errors.generic;
		} finally {
			busy = false;
		}
	}

	async function pair(event: SubmitEvent) {
		event.preventDefault();
		if (!code.trim()) return;
		busy = true;
		message = null;
		try {
			await pairDevice(code);
			code = '';
			message = t.paired;
			await owner.refresh();
			await loadDevices();
		} catch (error) {
			message =
				error instanceof ApiError && error.code === 'locked'
					? t.locked
					: error instanceof ApiError && error.status === 0
						? i18n.t.errors.network
						: t.badCode;
		} finally {
			busy = false;
		}
	}

	async function unpair(device: Device) {
		await revokeDevice(device.id).catch(() => {});
		await owner.refresh();
		await loadDevices();
	}

	const time = (iso: string) =>
		new Date(iso).toLocaleTimeString(i18n.locale, { hour: '2-digit', minute: '2-digit' });
	const day = (iso: string) =>
		new Date(iso).toLocaleDateString(i18n.locale, { day: 'numeric', month: 'long' });
</script>

<!-- Figures go in tabular numerals, as every count of the app: split the sentence. -->
{#snippet withNumber(sentence: (value: string) => string, value: string)}
	{@const [before, after] = sentence('\u0001').split('\u0001')}
	{before}<span class="num">{value}</span>{after}
{/snippet}

<section aria-labelledby="aparello" id="aparello" class="device">
	<h2>{t.title}</h2>
	{#if status}<p class="hint">{status}</p>{/if}

	{#if owner.isOwner}
		{#if pairing}
			<div class="pairing">
				<p class="hint">
					{pairing.urls.home || pairing.urls.remote ? t.pairIntro : t.pairIntroTyped}
				</p>
				<p class="code data" aria-label={t.code}>{pairing.code}</p>
				<p class="hint">{@render withNumber(t.expires, time(pairing.expires_at))}</p>
				<div class="qrs">
					{#each [[t.atHome, pairing.urls.home], [t.away, pairing.urls.remote]] as [label, url] (label)}
						{#if url}
							<figure>
								<div class="qr"><Qr text={url} label={t.qrLabel} /></div>
								<figcaption>{label}</figcaption>
							</figure>
						{/if}
					{/each}
				</div>
			</div>
		{:else}
			<div><Button icon="plus" onclick={newPairing} disabled={busy}>{t.pairOther}</Button></div>
		{/if}

		<h3>{t.devices}</h3>
		{#if devices.length === 0}
			<p class="hint">{t.noDevices}</p>
		{:else}
			<ul class="devices">
				{#each devices as device (device.id)}
					<li>
						<span class="name">
							{device.name}
							{#if owner.me?.device?.id === device.id}<span class="this">({t.thisOne})</span>{/if}
						</span>
						<span class="seen">{@render withNumber(t.lastSeen, day(device.last_seen))}</span>
						<Button variant="ghost" iconOnly icon="trash" onclick={() => unpair(device)}
							>{t.unpair} {device.name}</Button
						>
					</li>
				{/each}
			</ul>
		{/if}
	{:else if owner.me}
		<form class="enter" onsubmit={pair}>
			<label for="pairing-code">{t.code}</label>
			<p class="hint" id="pairing-hint">{t.codeHint}</p>
			<div class="row">
				<input
					id="pairing-code"
					type="text"
					autocomplete="one-time-code"
					autocapitalize="characters"
					spellcheck="false"
					aria-describedby="pairing-hint"
					bind:value={code}
				/>
				<Button variant="primary" type="submit" disabled={busy}>{busy ? t.pairing : t.pair}</Button>
			</div>
		</form>
	{/if}
	{#if message}<p class="message" role="status">{message}</p>{/if}
</section>

<style>
	.device {
		display: grid;
		gap: var(--s-2);
	}

	h2 {
		margin-bottom: var(--s-2);
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 650;
		line-height: 1;
	}

	h3 {
		margin-top: var(--s-4);
		font-size: var(--t-0);
		font-weight: 650;
	}

	.hint {
		max-width: 40rem;
		color: var(--texto-2);
	}

	.pairing {
		display: grid;
		gap: var(--s-2);
	}

	/* Read aloud or typed on a phone: big, in dots of light, like the party's room code. */
	.code {
		font-size: var(--t-4);
		letter-spacing: 0.1em;
		line-height: 1;
		color: var(--ouro);
	}

	.qrs {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-5);
		margin-top: var(--s-2);
	}

	figure {
		display: grid;
		gap: var(--s-2);
		margin: 0;
	}

	.qr {
		width: min(14rem, 60vw);
	}

	figcaption {
		font-weight: 650;
	}

	/* The paired devices: a board, one row each. */
	.devices {
		display: grid;
		max-width: 40rem;
		margin: 0;
		padding: 0;
		list-style: none;
		border-top: 1px solid var(--raia);
	}

	.devices li {
		display: grid;
		grid-template-columns: 1fr auto auto;
		align-items: center;
		gap: var(--s-4);
		padding-left: var(--s-3);
		border-bottom: 1px solid var(--raia);
	}

	.name {
		font-weight: 650;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.this,
	.seen {
		font-weight: 400;
		color: var(--texto-2);
	}

	.enter {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-2);
		max-width: 30rem;
	}

	label {
		font-weight: 650;
	}

	.row {
		display: flex;
		gap: var(--s-3);
	}

	/* The code as it is typed: the same dots of light as when it is shown. */
	input {
		flex: 1;
		min-width: 0;
		min-height: var(--target);
		padding: var(--s-1) var(--s-4);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-control);
		background: var(--fondo-2);
		color: var(--texto);
		font-family: var(--font-data);
		font-size: var(--t-2);
		font-weight: 650;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		transition:
			border-color var(--dur-1) ease,
			box-shadow var(--dur-1) ease;
	}

	input:focus {
		outline: none;
		border-color: var(--ceo);
		box-shadow: 0 0 0 1px var(--ceo);
	}

	.message {
		font-weight: 650;
	}

	@media (max-width: 30em) {
		.devices li {
			grid-template-columns: 1fr auto;
		}

		.seen {
			display: none;
		}
	}
</style>
