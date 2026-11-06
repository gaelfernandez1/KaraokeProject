import { describe, expect, it } from 'vitest';
import { History } from './history.svelte';

describe('History', () => {
	it('starts with nothing to undo or redo', () => {
		const history = new History('a');
		expect(history.current).toBe('a');
		expect(history.canUndo).toBe(false);
		expect(history.canRedo).toBe(false);
		history.undo();
		history.redo();
		expect(history.current).toBe('a');
	});

	it('undoes and redoes every step', () => {
		const history = new History(0);
		history.push(1);
		history.push(2);
		history.push(3);

		history.undo();
		history.undo();
		expect(history.current).toBe(1);
		expect(history.canUndo).toBe(true);
		expect(history.canRedo).toBe(true);

		history.redo();
		history.redo();
		expect(history.current).toBe(3);
		expect(history.canRedo).toBe(false);

		history.undo();
		history.undo();
		history.undo();
		expect(history.current).toBe(0);
		expect(history.canUndo).toBe(false);
	});

	it('ignores a push of the current value', () => {
		const value = { n: 1 };
		const history = new History(value);
		history.push(value);
		expect(history.canUndo).toBe(false);
	});

	it('drops the redo branch on a new push', () => {
		const history = new History('a');
		history.push('b');
		history.push('c');
		history.undo();
		history.push('d');
		expect(history.canRedo).toBe(false);
		history.redo();
		expect(history.current).toBe('d');
		history.undo();
		expect(history.current).toBe('b');
	});

	it('keeps the last 200 steps', () => {
		const history = new History(0);
		for (let i = 1; i <= 250; i++) history.push(i);
		let undone = 0;
		while (history.canUndo) {
			history.undo();
			undone++;
		}
		expect(undone).toBe(200);
		expect(history.current).toBe(50);
	});

	it('starts over on reset', () => {
		const history = new History('a');
		history.push('b');
		history.push('c');
		history.undo();
		history.reset('z');
		expect(history.current).toBe('z');
		expect(history.canUndo).toBe(false);
		expect(history.canRedo).toBe(false);
	});

	it('keeps the edits made while a save was on its way', () => {
		const history = new History('a');
		history.push('b');
		const sent = history.current;
		history.push('c'); // a nudge while the server answers
		expect(history.settle(sent, 'b stored')).toBe(false);
		expect(history.current).toBe('c');
		expect(history.canUndo).toBe(true);
	});

	it('starts over from what the server stored when nothing changed meanwhile', () => {
		const history = new History('a');
		history.push('b');
		expect(history.settle('b', 'b stored')).toBe(true);
		expect(history.current).toBe('b stored');
		expect(history.canUndo).toBe(false);
	});
});
