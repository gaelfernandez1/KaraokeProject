export type PlayerAction =
	| 'toggle'
	| 'back5'
	| 'forward5'
	| 'prevLine'
	| 'nextLine'
	| 'vocalsDown'
	| 'vocalsUp'
	| 'pitchDown'
	| 'pitchUp'
	| 'fullscreen'
	| 'exit';

const KEYS: Record<string, PlayerAction> = {
	' ': 'toggle',
	k: 'toggle',
	MediaPlayPause: 'toggle',
	ArrowLeft: 'back5',
	ArrowRight: 'forward5',
	MediaTrackPrevious: 'prevLine',
	MediaTrackNext: 'nextLine',
	ArrowDown: 'vocalsDown',
	ArrowUp: 'vocalsUp',
	'-': 'pitchDown',
	'+': 'pitchUp',
	'=': 'pitchUp',
	f: 'fullscreen',
	Escape: 'exit'
};

/**
 * The player's keyboard: the keys of a video player, plus line jumps with Shift and the media
 * keys of keyboards and presentation clickers.
 */
export function playerAction(event: { key: string; shiftKey: boolean }): PlayerAction | null {
	if (event.shiftKey && event.key === 'ArrowLeft') return 'prevLine';
	if (event.shiftKey && event.key === 'ArrowRight') return 'nextLine';
	return KEYS[event.key.length === 1 ? event.key.toLowerCase() : event.key] ?? null;
}
