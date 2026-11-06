/** Undo steps kept by default; older ones are dropped. */
const LIMIT = 200;

/**
 * Undo and redo over immutable values (the editor keeps whole documents: the ops share every
 * untouched line, so a step costs little).
 */
export class History<T> {
	current: T = $state.raw() as T;
	// Replaced, never mutated, so `canUndo` and `canRedo` stay reactive.
	#past: T[] = $state.raw([]);
	#future: T[] = $state.raw([]);
	readonly #limit: number;

	constructor(initial: T, limit = LIMIT) {
		this.current = initial;
		this.#limit = limit;
	}

	get canUndo(): boolean {
		return this.#past.length > 0;
	}

	get canRedo(): boolean {
		return this.#future.length > 0;
	}

	/** Makes `next` the current value; ops return the same object when nothing changed. */
	push(next: T): void {
		if (next === this.current) return;
		this.#past = [...this.#past, this.current].slice(-this.#limit);
		this.#future = [];
		this.current = next;
	}

	undo(): void {
		const previous = this.#past.at(-1);
		if (!this.canUndo) return;
		this.#future = [...this.#future, this.current];
		this.#past = this.#past.slice(0, -1);
		this.current = previous as T;
	}

	redo(): void {
		const next = this.#future.at(-1);
		if (!this.canRedo) return;
		this.#past = [...this.#past, this.current];
		this.#future = this.#future.slice(0, -1);
		this.current = next as T;
	}

	/**
	 * The server stored `sent` as `stored`. Starts over from `stored` (true) unless something was
	 * edited while the save was on its way: those edits stay, with their undo steps (false).
	 */
	settle(sent: T, stored: T): boolean {
		if (this.current !== sent) return false;
		this.reset(stored);
		return true;
	}

	/** Starts over from `value`, forgetting every step (another song, or a reload). */
	reset(value: T): void {
		this.current = value;
		this.#past = [];
		this.#future = [];
	}
}
