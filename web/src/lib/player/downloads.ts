/** What a file name cannot hold on some systems (and a slash would make it a folder). */
// eslint-disable-next-line no-control-regex -- control characters are exactly what it removes
const UNSAFE = /[\u0000-\u001f\u007f<>:"/\\|?*]+/g;

const clean = (text: string) => text.replace(UNSAFE, ' ').replace(/\s+/g, ' ').trim();

/**
 * The name a downloaded file of a song gets: «Artist - Title (what).ext», so a folder of them
 * sorts and reads well. The lyrics keep the `.karaoke.json` ending that says what they are.
 */
export function downloadName(
	song: { title: string; artist: string | null },
	file: string,
	what?: string
): string {
	const base = song.artist ? `${clean(song.artist)} - ${clean(song.title)}` : clean(song.title);
	if (file === 'karaoke.json') return `${base}.karaoke.json`;
	const dot = file.lastIndexOf('.');
	const extension = dot > file.lastIndexOf('/') ? file.slice(dot) : '';
	return `${base}${what ? ` (${what})` : ''}${extension}`;
}

/**
 * The name of a karaoke video, from its file (`exports/<id>-<16x9|9x16>-<style>[-v<vocals %>].mp4`):
 * «Artist - Title (karaoke vertical, voz 30%).mp4».
 */
export function videoName(
	song: { title: string; artist: string | null },
	file: string,
	words: { wide: string; tall: string; vocals: (percent: number) => string }
): string {
	const vocals = Number(/-v(\d+)\.mp4$/.exec(file)?.[1] ?? 0);
	const shape = file.includes('-9x16-') ? words.tall : words.wide;
	return downloadName(song, file, vocals ? `${shape}, ${words.vocals(vocals)}` : shape);
}
