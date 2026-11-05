import type { KaraokeDoc } from '#lib/contracts';

/** The lead line sung most often (the chorus hook); without repeats, the first line of 3+ words. */
export function hookOf(doc: KaraokeDoc): string | null {
	const lines = doc.lines
		.filter((line) => (line.role ?? 'lead') === 'lead')
		.map((line) => line.words.map((w) => w.text).join(' '));
	const key = (text: string) =>
		text
			.toLocaleLowerCase('gl')
			.replace(/[^\p{L}\p{N} ]/gu, '')
			.trim();
	const counts = new Map<string, number>();
	for (const line of lines) counts.set(key(line), (counts.get(key(line)) ?? 0) + 1);
	let best: string | null = null;
	let most = 1;
	for (const line of lines) {
		const count = counts.get(key(line)) ?? 0;
		if (count > most && line.split(' ').length >= 2) {
			best = line;
			most = count;
		}
	}
	const hook = best ?? lines.find((line) => line.split(' ').length >= 3) ?? lines[0] ?? null;
	// A quoted line ends clean: "Ola, mar de Vigo," is printed «Ola, mar de Vigo».
	return hook?.replace(/[\s,;:–—-]+$/u, '') ?? null;
}
