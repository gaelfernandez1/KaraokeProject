<script lang="ts">
	/*
	 * The lyrics editor: fix a word or a timing in seconds, without processing the song again.
	 * Pick a line, listen to it (once or on a loop), click a word to retype it, nudge or drag its
	 * edges, or tap the rhythm with the space bar to retime the whole line.
	 */
	import { splitTitle } from '#lib/poster/fit.js';
	import { beforeNavigate, goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { ApiError, deleteSong, getDoc, mediaUrl, saveDoc } from '#lib/api';
	import { explain, needsPairing } from '#lib/devices/explain.js';
	import PairingNotice from '#lib/devices/PairingNotice.svelte';
	import type { KaraokeDoc } from '#lib/contracts';
	import { History } from '#lib/editor/history.svelte.js';
	import { checkDoc, moveWordEdge, retimeLine, setWordText, shiftLine } from '#lib/editor/ops.js';
	import Waveform from '#lib/editor/Waveform.svelte';
	import { i18n } from '#lib/i18n';
	import { saved as offline } from '#lib/offline/saved.svelte.js';
	import { PlayerSession } from '#lib/player/session.svelte.js';
	import { settings } from '#lib/settings/settings.svelte.js';
	import Button from '#lib/ui/Button.svelte';

	/** Words the aligner was unsure about are marked for a second look (as in the engine's checks). */
	const DOUBTFUL = 0.3;
	/** Listening to a line starts this long before it and runs this long after it. */
	const LEAD = 0.6;

	const id = $derived(page.params.id ?? '');
	let history = $state.raw<History<KaraokeDoc> | null>(null);
	let saved = $state.raw<KaraokeDoc | null>(null);
	let missing = $state(false);
	let failure = $state<string | null>(null);
	let notice = $state<string | null>(null);
	let saving = $state(false);
	/** Deleting the song: asked once, then done; a failure says why (and how to pair if needed). */
	let confirmDelete = $state(false);
	let deleting = $state(false);
	let deleteFailure = $state<string | null>(null);
	let deleteUnpaired = $state(false);
	let deleted = false;
	/** How long the server keeps a deleted song (karaoke_server.library.Library.purge_trash). */
	const TRASH_DAYS = '30';
	let lineIndex = $state(0);
	let wordIndex = $state(0);
	let mode = $state<'idle' | 'line' | 'loop' | 'tap'>('idle');
	let taps = $state<number[]>([]);
	let editing = $state<string | null>(null);
	/** The document while a word edge is being dragged; it joins the history only when let go. */
	let dragging = $state.raw<KaraokeDoc | null>(null);
	let detail = $state<HTMLElement | null>(null);
	let linesOpen = $state(false);

	const session = new PlayerSession();
	const t = $derived(i18n.t.editor);
	const doc = $derived(dragging ?? history?.current ?? null);
	const line = $derived(doc?.lines[lineIndex] ?? null);
	const word = $derived(line?.words[wordIndex] ?? null);
	const dirty = $derived(doc !== null && doc !== saved);
	const from = $derived(line ? Math.max(0, line.start - LEAD) : 0);
	const to = $derived(line ? line.end + LEAD : 1);
	/** Every word the aligner was unsure about, in order, to review them one by one. */
	const doubtful = $derived(
		doc
			? doc.lines.flatMap((l, i) =>
					l.words.flatMap((w, j) => ((w.confidence ?? 1) < DOUBTFUL ? [{ line: i, word: j }] : []))
				)
			: []
	);

	function nextDoubtful() {
		if (doubtful.length === 0) return;
		const after =
			doubtful.find((d) => d.line > lineIndex || (d.line === lineIndex && d.word > wordIndex)) ??
			doubtful[0];
		if (after.line !== lineIndex) selectLine(after.line);
		wordIndex = after.word;
	}

	$effect(() => {
		const songId = id;
		getDoc(songId)
			.then((loaded) => {
				history = new History(loaded);
				saved = loaded;
				return session.load(
					{
						instrumental: mediaUrl(songId, loaded.audio.instrumental),
						vocals: loaded.audio.vocals ? mediaUrl(songId, loaded.audio.vocals) : null
					},
					// The singer's voice up: it is what the timings follow.
					{ vocals: 1, latencyMs: settings.latencyMs }
				);
			})
			.catch((error: unknown) => {
				if (error instanceof ApiError && error.status === 404) missing = true;
				else failure = i18n.t.errors.generic;
			});
		return () => session.destroy();
	});

	$effect(() => {
		let frame = requestAnimationFrame(function loop() {
			session.tick();
			follow();
			frame = requestAnimationFrame(loop);
		});
		return () => cancelAnimationFrame(frame);
	});

	beforeNavigate(({ cancel }) => {
		if (!deleted && dirty && !confirm(t.leave)) cancel();
	});

	/** Stops (or loops) at the end of the line being listened to. */
	function follow() {
		if (!line || mode === 'idle' || !session.playing) return;
		if (session.time > line.end + LEAD) {
			if (mode === 'loop') session.seek(from);
			else if (mode === 'tap') finishTap();
			else {
				session.pause();
				mode = 'idle';
			}
		}
	}

	function apply(next: KaraokeDoc) {
		history?.push(next);
		notice = null;
	}

	function selectLine(index: number) {
		if (!doc) return;
		lineIndex = Math.max(0, Math.min(doc.lines.length - 1, index));
		wordIndex = 0;
		editing = null;
		linesOpen = false;
		if (mode === 'tap') mode = 'idle';
		if (matchMedia('(max-width: 59.99em)').matches) detail?.scrollIntoView({ behavior: 'smooth' });
	}

	async function listen(loop: boolean) {
		if (!line) return;
		if (session.playing && (mode === 'line' || mode === 'loop') && (mode === 'loop') === loop) {
			session.pause();
			mode = 'idle';
			return;
		}
		mode = loop ? 'loop' : 'line';
		session.seek(from);
		await session.play();
	}

	async function startTap() {
		if (!line) return;
		// The button that started it must not catch the space bar meant for tapping.
		if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
		taps = [];
		mode = 'tap';
		session.seek(Math.max(0, line.start - 1.5));
		await session.play();
	}

	function tap() {
		if (!line) return;
		taps = [...taps, session.time];
		if (taps.length >= line.words.length) finishTap();
	}

	function finishTap() {
		if (doc && taps.length > 0) apply(retimeLine(doc, lineIndex, taps));
		taps = [];
		mode = 'idle';
		session.pause();
	}

	function nudge(edge: 'start' | 'end', delta: number) {
		if (doc) apply(moveWordEdge(doc, { line: lineIndex, word: wordIndex }, edge, delta));
	}

	/** `delta` is measured from where the drag began; null when the drag was cancelled. */
	function onDrag(index: number, edge: 'start' | 'end', delta: number | null, done: boolean) {
		const base = history?.current;
		if (!base) return;
		if (delta === null) {
			dragging = null;
			return;
		}
		const next = moveWordEdge(base, { line: lineIndex, word: index }, edge, delta);
		if (done) {
			dragging = null;
			apply(next);
		} else {
			dragging = next;
		}
	}

	function commitText(event?: Event) {
		event?.preventDefault();
		if (!doc || editing === null) return;
		if (!editing.trim()) {
			notice = t.emptyWord;
			return;
		}
		apply(setWordText(doc, { line: lineIndex, word: wordIndex }, editing));
		editing = null;
	}

	async function save() {
		if (!doc || saving) return;
		if (checkDoc(doc).length > 0) {
			notice = t.invalid;
			return;
		}
		saving = true;
		const sent = doc;
		try {
			const stored = await saveDoc(id, sent);
			// Edits made while the save was on its way stay, still to be saved.
			saved = history && !history.settle(sent, stored) ? sent : stored;
			notice = t.saved;
		} catch (error) {
			notice = explain(error, t.saveError, i18n.t);
		} finally {
			saving = false;
		}
	}

	async function remove() {
		if (deleting) return;
		deleting = true;
		deleteFailure = null;
		deleteUnpaired = false;
		try {
			await deleteSong(id);
			deleted = true;
			// A copy kept on this device for singing offline goes too.
			if (offline.has(id)) await offline.remove(id).catch(() => {});
			await goto(resolve('/'));
		} catch (error) {
			deleteUnpaired = needsPairing(error);
			deleteFailure = explain(error, t.deleteError, i18n.t);
		} finally {
			deleting = false;
		}
	}

	function onKey(event: KeyboardEvent) {
		if (!doc || !line) return;
		// While tapping, space is always a tap, even if a button (the one that started it) has focus.
		if (mode === 'tap' && event.key === ' ') {
			event.preventDefault();
			tap();
			return;
		}
		const target = event.target instanceof Element ? event.target : document.body;
		if (target.matches('input, textarea')) return;
		const mod = event.ctrlKey || event.metaKey;
		if (mod && event.key.toLowerCase() === 'z') {
			event.preventDefault();
			if (event.shiftKey) history?.redo();
			else history?.undo();
			return;
		}
		if (mod && event.key.toLowerCase() === 's') {
			event.preventDefault();
			void save();
			return;
		}
		if (mod || (target.matches('button, a') && (event.key === ' ' || event.key === 'Enter')))
			return;
		const words = line.words.length;
		const step = (fine: number) => (event.shiftKey ? 0.05 : fine);
		const handled: Record<string, () => void> = {
			ArrowLeft: () => (wordIndex = Math.max(0, wordIndex - 1)),
			ArrowRight: () => (wordIndex = Math.min(words - 1, wordIndex + 1)),
			ArrowUp: () => selectLine(lineIndex - 1),
			ArrowDown: () => selectLine(lineIndex + 1),
			'[': () => nudge('start', -0.01),
			']': () => nudge('start', 0.01),
			'{': () => nudge('start', -0.05),
			'}': () => nudge('start', 0.05),
			',': () => nudge('end', -step(0.01)),
			'.': () => nudge('end', step(0.01)),
			'<': () => nudge('end', -0.05),
			'>': () => nudge('end', 0.05),
			' ': () => (mode === 'tap' ? tap() : void listen(false)),
			l: () => void listen(true),
			t: () => (mode === 'tap' ? finishTap() : void startTap()),
			Enter: () => (mode === 'tap' ? finishTap() : (editing = word?.text ?? null))
		};
		const action = handled[event.key.length === 1 ? event.key.toLowerCase() : event.key];
		if (!action) return;
		event.preventDefault();
		action();
	}

	const precise = (seconds: number) => {
		const m = Math.floor(seconds / 60);
		const s = (seconds % 60).toFixed(2).padStart(5, '0');
		return `${m}:${s}`;
	};
</script>

<svelte:head
	><title>{doc ? t.title(doc.title) : t.help} · Proxecto Karaoke en Galego</title></svelte:head
>
<svelte:window onkeydown={onKey} onbeforeunload={(e) => dirty && e.preventDefault()} />

<div class="editor">
	<header class="bar">
		<Button variant="ghost" iconOnly icon="back" href={resolve('/cantar/[id]', { id })}
			>{t.toPlayer}</Button
		>
		<h1>{doc ? t.title(splitTitle(doc.title).main) : ''}</h1>
		{#if dirty}<p class="status">{t.unsaved}</p>{/if}
		<Button variant="primary" icon="check" disabled={!dirty || saving} onclick={save}
			>{t.save}</Button
		>
	</header>

	{#if notice}<p class="notice" role="status">{notice}</p>{/if}

	{#if missing}
		<p class="message">{i18n.t.player.notFound}</p>
	{:else if failure}
		<p class="message" role="alert">{failure}</p>
	{:else if doc}
		<div class="layout">
			<nav class="lines" class:open={linesOpen} aria-label={t.lines}>
				<ol>
					{#each doc.lines as l, i (l.id)}
						<li>
							<button
								type="button"
								class:current={i === lineIndex}
								class:backing={l.role === 'backing'}
								aria-current={i === lineIndex ? 'true' : undefined}
								onclick={() => selectLine(i)}
							>
								<span class="time num">{precise(l.start)}</span>
								<span class="text"
									>{#each l.words as w, j (j)}{j > 0 ? ' ' : ''}<span
											class:doubtful={(w.confidence ?? 1) < DOUBTFUL}>{w.text}</span
										>{/each}</span
								>
							</button>
						</li>
					{/each}
				</ol>
			</nav>

			{#if line}
				<section class="detail" bind:this={detail} aria-label={t.word}>
					<div class="line-bar">
						<button
							type="button"
							class="lines-toggle"
							aria-expanded={linesOpen}
							onclick={() => (linesOpen = !linesOpen)}
						>
							{i18n.t.party.lineOf(lineIndex + 1, doc.lines.length)}
						</button>
						{#if doubtful.length > 0}
							<p class="doubts">
								<span>{t.doubtfulCount(doubtful.length)}.</span>
								<button type="button" class="link" onclick={nextDoubtful}>{t.nextDoubtful}</button>
							</p>
						{/if}
					</div>
					<div class="words" role="listbox" aria-label={t.word}>
						{#each line.words as w, j (j)}
							<button
								type="button"
								role="option"
								aria-selected={j === wordIndex}
								class:doubtful={(w.confidence ?? 1) < DOUBTFUL}
								class:tapped={mode === 'tap' && j < taps.length}
								class:next={mode === 'tap' && j === taps.length}
								onclick={() => {
									wordIndex = j;
									editing = null;
								}}
								ondblclick={() => (editing = w.text)}>{w.text}</button
							>
						{/each}
					</div>

					<Waveform
						buffer={session.vocalsBuffer}
						{from}
						{to}
						words={line.words.map((w) => ({
							text: w.text,
							start: w.start,
							end: w.end,
							doubtful: (w.confidence ?? 1) < DOUBTFUL
						}))}
						selected={wordIndex}
						time={session.time}
						onseek={(s) => session.seek(s)}
						onselect={(j) => (wordIndex = j)}
						ondrag={onDrag}
					/>

					<div class="listen">
						<Button
							icon={mode === 'line' && session.playing ? 'pause' : 'play'}
							onclick={() => listen(false)}>{t.playLine}</Button
						>
						<Button
							icon="loop"
							variant={mode === 'loop' ? 'primary' : 'quiet'}
							aria-pressed={mode === 'loop'}
							onclick={() => listen(true)}>{t.loop}</Button
						>
						<Button
							icon="tap"
							variant={mode === 'tap' ? 'primary' : 'quiet'}
							aria-pressed={mode === 'tap'}
							onclick={() => (mode === 'tap' ? finishTap() : startTap())}>{t.tap}</Button
						>
						<span class="history">
							<Button
								variant="ghost"
								iconOnly
								icon="undo"
								disabled={!history?.canUndo}
								onclick={() => history?.undo()}>{t.undo}</Button
							>
							<Button
								variant="ghost"
								iconOnly
								icon="redo"
								disabled={!history?.canRedo}
								onclick={() => history?.redo()}>{t.redo}</Button
							>
						</span>
						{#if mode === 'tap'}
							<p class="tapping" aria-live="polite">
								{t.tapping(Math.min(taps.length + 1, line.words.length), line.words.length)}
								<span>{t.tapHint}</span>
							</p>
							<button type="button" class="tap-pad" onpointerdown={tap}>{t.tap}</button>
						{/if}
					</div>

					{#if word}
						<div class="word-tools">
							{#if editing !== null}
								<form class="edit" onsubmit={commitText}>
									<label for="word-text" class="visually-hidden">{t.editWord}</label>
									<!-- svelte-ignore a11y_autofocus -->
									<input
										id="word-text"
										bind:value={editing}
										autofocus
										spellcheck="false"
										onkeydown={(e) => e.key === 'Escape' && (editing = null)}
									/>
									<Button variant="primary" type="submit" icon="check">{i18n.t.common.save}</Button>
									<Button variant="ghost" onclick={() => (editing = null)}
										>{i18n.t.common.cancel}</Button
									>
								</form>
							{:else}
								<Button icon="edit" onclick={() => (editing = word.text)}>{t.editWord}</Button>
							{/if}

							<div class="edges">
								{#each [['start', t.start, word.start], ['end', t.end, word.end]] as const as [edge, label, value] (edge)}
									<div class="edge" role="group" aria-label={label}>
										<span class="edge-label">{label}</span>
										<Button iconOnly icon="minus" onclick={() => nudge(edge, -0.01)}
											>{t.earlier}</Button
										>
										<output class="num">{precise(value)}</output>
										<Button iconOnly icon="plus" onclick={() => nudge(edge, 0.01)}>{t.later}</Button
										>
									</div>
								{/each}
								<div class="edge" role="group" aria-label={t.moveLine}>
									<span class="edge-label">{t.moveLine}</span>
									<Button
										iconOnly
										icon="minus"
										onclick={() => doc && apply(shiftLine(doc, lineIndex, -0.1))}
										>{t.earlier}</Button
									>
									<output class="num">{precise(line.start)}</output>
									<Button
										iconOnly
										icon="plus"
										onclick={() => doc && apply(shiftLine(doc, lineIndex, 0.1))}>{t.later}</Button
									>
								</div>
							</div>
							{#if (word.confidence ?? 1) < DOUBTFUL}<p class="doubtful-note">{t.doubtful}</p>{/if}
						</div>
					{/if}

					<details class="help">
						<summary>{t.help}</summary>
						<dl>
							{#each t.keys as [keys, what] (keys)}
								<div>
									<dt><kbd>{keys}</kbd></dt>
									<dd>{what}</dd>
								</div>
							{/each}
						</dl>
					</details>

					<div class="delete">
						{#if confirmDelete}
							<!-- The figure in the poster face, as everywhere (the text face slashes its zero). -->
							{@const [before, after] = t.deleteConfirm('\u0001').split('\u0001')}
							<p>{before}<span class="num">{TRASH_DAYS}</span>{after}</p>
							<div class="row">
								<Button variant="danger" icon="trash" disabled={deleting} onclick={remove}
									>{t.deleteYes}</Button
								>
								<Button onclick={() => (confirmDelete = false)}>{i18n.t.common.cancel}</Button>
							</div>
						{:else}
							<Button variant="ghost" icon="trash" onclick={() => (confirmDelete = true)}
								>{t.deleteSong}</Button
							>
						{/if}
						{#if deleteFailure && deleteUnpaired}
							<PairingNotice text={deleteFailure} />
						{:else if deleteFailure}
							<p class="failed" role="alert">{deleteFailure}</p>
						{/if}
					</div>
				</section>
			{:else}
				<p class="message">{t.chooseLine}</p>
			{/if}
		</div>
	{/if}
</div>

<style>
	.editor {
		min-height: 100dvh;
		display: grid;
		grid-template-rows: auto auto 1fr;
		grid-template-columns: minmax(0, 1fr);
	}

	.bar {
		position: sticky;
		top: 0;
		z-index: 3;
		display: flex;
		align-items: center;
		gap: var(--s-3);
		padding: var(--s-3) var(--page-x);
		background: var(--noite);
		border-bottom: 1px solid var(--linha);
	}

	h1 {
		flex: 1;
		min-width: 0;
		font-family: var(--font-display);
		font-size: var(--t-2);
		font-weight: 900;
		line-height: 1;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		overflow: hidden;
	}

	@media (max-width: 44.99em) {
		h1 {
			font-size: 1.25rem;
		}

		/* No room in the bar: the enabled Save says it; screen readers still hear it. */
		.status {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip-path: inset(50%);
		}
	}

	.status {
		font-size: var(--t--1);
		color: var(--farol);
		font-weight: 700;
	}

	/* Last in the song's page, apart from the editing, as in a contact card. */
	.delete {
		display: grid;
		justify-items: start;
		gap: var(--s-3);
		margin-top: var(--s-6);
		padding-top: var(--s-4);
		border-top: 1px solid var(--linha);
	}

	.delete p {
		max-width: 38rem;
		color: var(--papel-suave);
	}

	.delete .row {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-3);
	}

	.delete .failed {
		font-weight: 700;
		color: var(--erro);
	}

	.notice {
		margin: var(--s-3) var(--page-x) 0;
		padding: var(--s-2) var(--s-4);
		border-left: 4px solid var(--farol);
		background: var(--noite-alta);
		font-weight: 600;
	}

	.message {
		padding: var(--s-6) var(--page-x);
		color: var(--papel-suave);
	}

	.layout {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--s-5);
		padding: var(--s-4) var(--page-x) var(--s-8);
		min-height: 0;
	}

	@media (min-width: 60em) {
		.layout {
			grid-template-columns: minmax(18rem, 26rem) 1fr;
			align-items: start;
		}

		.lines {
			position: sticky;
			top: 5rem;
			max-height: calc(100dvh - 6.5rem);
			overflow-y: auto;
		}

		.detail {
			position: sticky;
			top: 5rem;
		}
	}

	.lines ol {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.lines button {
		display: grid;
		grid-template-columns: 4.5rem 1fr;
		gap: var(--s-3);
		width: 100%;
		padding: var(--s-2) var(--s-3);
		border: 0;
		background: none;
		text-align: left;
		line-height: 1.35;
	}

	.lines button:hover {
		background: var(--noite-alta);
	}

	.lines button.current {
		background: var(--noite-alta);
		color: var(--farol);
	}

	.lines button.backing {
		padding-left: var(--s-6);
		font-size: var(--t--1);
		color: var(--papel-suave);
	}

	.time {
		font-variant-numeric: tabular-nums;
		font-size: var(--t--1);
		color: var(--papel-suave);
		padding-top: 0.1em;
	}

	/* A dotted line, not a spellchecker's wave: the word may be out of time, not misspelt. */
	.doubtful {
		text-decoration: underline dotted var(--papel-suave);
		text-decoration-thickness: 2px;
		text-underline-offset: 0.3em;
	}

	.line-bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--s-2) var(--s-4);
	}

	.lines-toggle {
		display: none;
		gap: var(--s-2);
		align-items: center;
		min-height: var(--target);
		padding: 0 var(--s-3);
		border: 2px solid var(--linha);
		border-radius: var(--radius-control);
		background: transparent;
		font-weight: 700;
	}

	.doubts {
		display: flex;
		gap: var(--s-2);
		align-items: baseline;
		color: var(--papel-suave);
		font-size: var(--t--1);
	}

	.link {
		min-height: var(--target);
		padding: 0 var(--s-2);
		border: 0;
		background: none;
		font-weight: 800;
		color: var(--papel);
		text-decoration: underline;
		text-underline-offset: 0.2em;
	}

	.history {
		display: flex;
		gap: var(--s-2);
		margin-left: auto;
	}

	.detail {
		display: grid;
		gap: var(--s-4);
		min-width: 0;
	}

	.words {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-2);
	}

	.words button {
		min-height: var(--target);
		padding: 0 var(--s-3);
		border: 2px solid var(--linha);
		border-radius: var(--radius-control);
		background: transparent;
		font-family: var(--font-display);
		font-size: var(--t-2);
		font-weight: 800;
	}

	.words button[aria-selected='true'] {
		border-color: var(--farol);
		background: color-mix(in oklch, var(--farol) 14%, transparent);
	}

	.words button.tapped {
		color: var(--farol);
	}

	.words button.next {
		outline: 3px dashed var(--farol);
		outline-offset: 2px;
	}

	.listen {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--s-2);
	}

	.tapping {
		display: grid;
		font-weight: 700;
	}

	.tapping span {
		font-weight: 400;
		font-size: var(--t--1);
		color: var(--papel-suave);
	}

	.tap-pad {
		flex-basis: 100%;
		min-height: 6rem;
		border: 2px solid var(--farol);
		border-radius: var(--radius-control);
		background: color-mix(in oklch, var(--farol) 12%, transparent);
		font-family: var(--font-display);
		font-size: var(--t-3);
		font-weight: 900;
		touch-action: manipulation;
	}

	@media (hover: hover) and (pointer: fine) {
		.tap-pad {
			display: none;
		}
	}

	.word-tools {
		display: grid;
		gap: var(--s-4);
		padding: var(--s-4);
		background: var(--noite-alta);
	}

	.word-tools > :global(.button) {
		justify-self: start;
	}

	.edit {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-2);
	}

	.edit input {
		flex: 1;
		min-width: 10rem;
		min-height: var(--target);
		padding: 0 var(--s-3);
		border: 2px solid var(--farol);
		border-radius: var(--radius-control);
		background: var(--noite);
		font-size: var(--t-1);
		font-weight: 700;
	}

	.edit input:focus {
		outline: none;
	}

	.edges {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-4) var(--s-6);
	}

	.edge {
		display: grid;
		grid-template-columns: auto auto auto;
		align-items: center;
		gap: var(--s-2);
	}

	.edge-label {
		grid-column: 1 / -1;
		font-size: var(--t--1);
		font-weight: 700;
		color: var(--papel-suave);
	}

	.edge output {
		min-width: 6.5ch;
		text-align: center;
		font-variant-numeric: tabular-nums;
		font-weight: 700;
	}

	.doubtful-note {
		font-size: var(--t--1);
		color: var(--papel-suave);
	}

	/* Keyboard shortcuts mean nothing on a touch screen. */
	@media (pointer: coarse) {
		.help {
			display: none;
		}
	}

	.help summary {
		cursor: pointer;
		font-weight: 700;
		color: var(--papel-suave);
	}

	.help dl {
		display: grid;
		gap: var(--s-1);
		margin-top: var(--s-3);
	}

	.help div {
		display: grid;
		grid-template-columns: 7rem 1fr;
		gap: var(--s-3);
	}

	.help dd {
		margin: 0;
		color: var(--papel-suave);
	}

	kbd {
		padding: 0 0.4em;
		border: 1px solid var(--linha);
		border-radius: 4px;
		font-family: inherit;
		font-size: var(--t--1);
	}

	/* Phones: the lines are a drawer over the editor, opened from the line's own button. */
	@media (max-width: 59.99em) {
		.lines {
			display: none;
			position: fixed;
			inset: auto 0 0;
			z-index: 4;
			max-height: 70dvh;
			overflow-y: auto;
			padding: var(--s-3) var(--page-x) var(--s-6);
			background: var(--noite);
			border-top: 1px solid var(--linha);
		}

		.lines.open {
			display: block;
		}

		.lines-toggle {
			display: inline-flex;
		}

		.listen {
			display: grid;
			grid-template-columns: minmax(0, 1fr);
		}

		.detail {
			grid-template-columns: minmax(0, 1fr);
		}

		.history {
			margin-left: 0;
			justify-content: flex-end;
		}
	}
</style>
