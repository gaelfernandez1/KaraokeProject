import { describe, expect, test } from 'vitest';
import { fillSegments, fillX } from './fill';
import type { Layout, Row } from './layout';
import { sceneAt } from './scene';

const row = (words: { parts: [string, number, number][] }[]): Row => ({
	line_id: 'l1',
	role: 'lead',
	singer: null,
	color: '#FFC531',
	words: words.map((w) => ({ parts: w.parts.map(([text, start, end]) => ({ text, start, end })) })),
	text: '',
	scale: 1,
	x: 500,
	y: 900,
	width: 300,
	height: 90
});

describe('fill', () => {
	test('a word without parts wipes across its whole width', () => {
		const segments = fillSegments(
			row([{ parts: [['Ola', 10, 12]] }]),
			[{ x0: 0, x1: 120 }],
			'wipe'
		);

		expect(fillX(segments, 9)).toBe(0);
		expect(fillX(segments, 11)).toBe(60);
		expect(fillX(segments, 12)).toBe(120);
	});

	test('syllables wipe at their own pace and the fill waits between words', () => {
		const r = row([
			{
				parts: [
					['Bai', 10, 10.2],
					['la', 10.2, 11.0]
				]
			},
			{ parts: [['me', 12, 13]] }
		]);
		const segments = fillSegments(
			r,
			[
				{ x0: 0, x1: 40 },
				{ x0: 40, x1: 100 },
				{ x0: 120, x1: 160 }
			],
			'wipe'
		);

		expect(fillX(segments, 10.1)).toBeCloseTo(20);
		expect(fillX(segments, 10.6)).toBeCloseTo(70);
		expect(fillX(segments, 11.5)).toBe(100);
		expect(fillX(segments, 12.5)).toBeCloseTo(140);
	});

	test('word mode fills each word at once when it starts', () => {
		const r = row([
			{
				parts: [
					['Bai', 10, 10.2],
					['la', 10.2, 11.0]
				]
			},
			{ parts: [['me', 12, 13]] }
		]);
		const boxes = [
			{ x0: 0, x1: 40 },
			{ x0: 40, x1: 100 },
			{ x0: 120, x1: 160 }
		];
		const segments = fillSegments(r, boxes, 'word');

		expect(fillX(segments, 9.99)).toBe(0);
		expect(fillX(segments, 10)).toBe(100);
		expect(fillX(segments, 11.9)).toBe(100);
		expect(fillX(segments, 12)).toBe(160);
	});

	test('boxes must match the parts', () => {
		expect(() => fillSegments(row([{ parts: [['Ola', 10, 12]] }]), [], 'wipe')).toThrow();
	});
});

const layout: Layout = {
	width: 1000,
	height: 1000,
	font_px: 75,
	mode: 'pages',
	groups: [
		{ index: 0, block: 0, slot: 0, start: 10, end: 12, show: 7, hide: 12.8, rows: [] },
		{ index: 1, block: 1, slot: 0, start: 30, end: 32, show: 27, hide: 32.8, rows: [] }
	],
	countdowns: [
		{
			block: 0,
			start: 7,
			end: 10,
			dots: [
				{ x: 1, y: 1, r: 1, off: 10 },
				{ x: 2, y: 1, r: 1, off: 9 },
				{ x: 3, y: 1, r: 1, off: 8 }
			]
		}
	],
	bars: [{ start: 12.8, end: 27, x: 500, y: 900, width: 270, height: 6 }],
	scroll: null
};

describe('sceneAt', () => {
	test('shows the groups on screen, fading in and out', () => {
		expect(sceneAt(layout, 6.9, 0.25).groups).toEqual([]);
		expect(sceneAt(layout, 7.125, 0.25).groups).toEqual([{ index: 0, opacity: 0.5 }]);
		expect(sceneAt(layout, 10, 0.25).groups).toEqual([{ index: 0, opacity: 1 }]);
		expect(sceneAt(layout, 12.7, 0.25).groups[0].opacity).toBeCloseTo(0.4);
		expect(sceneAt(layout, 12.8, 0.25).groups).toEqual([]);
	});

	test('countdown dots go out right to left', () => {
		expect(sceneAt(layout, 7.5, 0.25).dots.map((d) => d.x)).toEqual([1, 2, 3]);
		expect(sceneAt(layout, 8.5, 0.25).dots.map((d) => d.x)).toEqual([1, 2]);
		expect(sceneAt(layout, 9.99, 0.25).dots.map((d) => d.x)).toEqual([1]);
		expect(sceneAt(layout, 10, 0.25).dots).toEqual([]);
	});

	test('the break bar fills up during the break', () => {
		expect(sceneAt(layout, 12, 0.25).bar).toBeNull();
		expect(sceneAt(layout, 19.9, 0.25).bar?.progress).toBeCloseTo(0.5);
	});

	test('is pure: the same time gives the same scene after any other time', () => {
		const first = sceneAt(layout, 8.5, 0.25);
		sceneAt(layout, 30, 0.25);
		sceneAt(layout, 0, 0.25);

		expect(sceneAt(layout, 8.5, 0.25)).toEqual(first);
	});
});

describe('sceneAt in scroll mode', () => {
	const scroll: Layout = {
		...layout,
		mode: 'scroll',
		groups: [0, 1, 2, 3].map((k) => ({
			index: k,
			block: 0,
			slot: 0,
			start: 10 + 2 * k,
			end: 11.5 + 2 * k,
			show: k >= 3 ? 11.85 : 0,
			hide: 30,
			rows: []
		})),
		countdowns: [],
		bars: [],
		scroll: {
			offsets: [373, 253, 133, 13],
			switches: [11.85, 13.85, 15.85],
			transition: 0.4,
			visible: 3
		}
	};

	test('the list rests on a line, then eases to the next one', () => {
		expect(sceneAt(scroll, 11, 0.25).offset).toBe(373);
		expect(sceneAt(scroll, 12.05, 0.25).offset).toBeCloseTo(373 - 120 * 0.875);
		expect(sceneAt(scroll, 13, 0.25).offset).toBe(253);
	});

	test('lines fade with their distance from the one being sung', () => {
		const opacities = sceneAt(scroll, 13, 0.25).groups.map((g) => g.opacity);

		expect(opacities).toEqual([0.4, 1, 0.88, 0.76].map((o) => expect.closeTo(o)));
	});

	test('pages mode does not move', () => {
		expect(sceneAt(layout, 10, 0.25).offset).toBe(0);
	});
});
