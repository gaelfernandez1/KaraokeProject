<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAnchorAttributes, HTMLButtonAttributes } from 'svelte/elements';
	import Icon, { type IconName } from './Icon.svelte';

	type Common = {
		variant?: 'primary' | 'quiet' | 'ghost' | 'danger';
		size?: 'm' | 'l';
		icon?: IconName;
		/** Only the icon shows; the children become its accessible name. */
		iconOnly?: boolean;
		children: Snippet;
	};

	type Props = Common &
		(
			| (Omit<HTMLButtonAttributes, 'children'> & { href?: undefined })
			| (Omit<HTMLAnchorAttributes, 'children'> & { href: string })
		);

	let {
		variant = 'quiet',
		size = 'm',
		icon,
		iconOnly = false,
		children,
		class: className = '',
		...rest
	}: Props = $props();
</script>

{#snippet content()}
	{#if icon}<Icon name={icon} size={size === 'l' ? 1.5 : 1.25} />{/if}
	{#if iconOnly}<span class="visually-hidden">{@render children()}</span>{:else}<span class="label"
			>{@render children()}</span
		>{/if}
{/snippet}

{#if rest.href !== undefined}
	<a
		class="button {variant} {size} {className}"
		class:icon-only={iconOnly}
		{...rest as HTMLAnchorAttributes}>{@render content()}</a
	>
{:else}
	<button
		type="button"
		class="button {variant} {size} {className}"
		class:icon-only={iconOnly}
		{...rest as HTMLButtonAttributes}>{@render content()}</button
	>
{/if}

<style>
	.button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--s-2);
		min-height: var(--target);
		padding: 0 var(--s-5);
		border: 1px solid transparent;
		border-radius: var(--radius-pill);
		font-family: var(--font-text);
		font-size: var(--t-0);
		font-weight: 650;
		line-height: 1.1;
		text-decoration: none;
		white-space: nowrap;
		cursor: pointer;
		transition:
			background-color var(--dur-1) var(--ease),
			border-color var(--dur-1) var(--ease),
			color var(--dur-1) var(--ease),
			transform var(--dur-1) var(--ease);
	}

	.button:active:not(:disabled) {
		transform: scale(0.97);
	}

	/* Disabled reads as "not yet", not as a dimmed colour. */
	.button:disabled,
	.button[aria-disabled='true'] {
		cursor: not-allowed;
		background: transparent;
		border: 1px solid var(--raia);
		color: color-mix(in oklch, var(--texto) 45%, transparent);
	}

	.l {
		min-height: 3.5rem;
		padding: 0 var(--s-6);
		font-size: var(--t-1);
	}

	.primary {
		background: var(--accion);
		color: var(--accion-texto);
		font-weight: 700;
	}

	.quiet {
		background: var(--panel-claro);
		border-color: var(--raia-forte);
		color: var(--texto);
	}

	.ghost {
		background: transparent;
		color: var(--texto);
		padding: 0 var(--s-3);
	}

	.danger {
		background: transparent;
		border-color: color-mix(in oklch, var(--erro) 55%, transparent);
		color: var(--erro);
	}

	/* Only where a pointer can hover: on touch the colour would stay after the tap. */
	@media (hover: hover) {
		.primary:hover:not(:disabled) {
			background: color-mix(in oklch, var(--accion), var(--ceo) 22%);
		}

		.quiet:hover:not(:disabled) {
			background: rgb(255 255 255 / 0.1);
			border-color: var(--ceo);
		}

		.ghost:hover:not(:disabled) {
			background: color-mix(in oklch, var(--texto) 9%, transparent);
		}

		.danger:hover:not(:disabled) {
			background: color-mix(in oklch, var(--erro) 12%, transparent);
		}
	}

	.icon-only {
		width: var(--target);
		padding: 0;
	}

	.icon-only.l {
		width: 3.5rem;
	}

	.label {
		overflow: hidden;
		text-overflow: ellipsis;
	}
</style>
