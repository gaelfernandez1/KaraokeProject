import { describe, expect, it } from 'vitest';
import { downloadName, videoName } from './downloads';

describe('downloadName', () => {
	const song = { title: 'Mar de Vigo', artist: 'Uxía' };

	it('names a file by artist and title, what it is and its own extension', () => {
		expect(downloadName(song, 'exports/mar-16x9-clasico.mp4', 'karaoke')).toBe(
			'Uxía - Mar de Vigo (karaoke).mp4'
		);
		expect(downloadName({ ...song, artist: null }, 'instrumental.m4a', 'sen voz')).toBe(
			'Mar de Vigo (sen voz).m4a'
		);
	});

	it('marks the lyrics as a karaoke document', () => {
		expect(downloadName(song, 'karaoke.json')).toBe('Uxía - Mar de Vigo.karaoke.json');
	});

	it('leaves out what a file name cannot hold', () => {
		expect(downloadName({ title: 'Ida/volta: "1"?', artist: 'A\\B' }, 'v.mp4', 'karaoke')).toBe(
			'A B - Ida volta 1 (karaoke).mp4'
		);
	});
});

describe('videoName', () => {
	const song = { title: 'Mar de Vigo', artist: 'Uxía' };
	const words = { wide: 'karaoke', tall: 'karaoke vertical', vocals: (n: number) => `voz ${n}%` };

	it('says the shape of the video and how loud the guide vocals are, from its file', () => {
		expect(videoName(song, 'exports/mar-16x9-clasico.mp4', words)).toBe(
			'Uxía - Mar de Vigo (karaoke).mp4'
		);
		expect(videoName(song, 'exports/mar-9x16-moderno-v30.mp4', words)).toBe(
			'Uxía - Mar de Vigo (karaoke vertical, voz 30%).mp4'
		);
	});
});
