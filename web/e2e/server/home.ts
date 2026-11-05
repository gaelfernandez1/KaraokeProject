import type { Browser, BrowserContext } from '@playwright/test';
import { networkInterfaces } from 'node:os';

/** The server as a phone on the home network reaches it: through this machine's address. */
export function homeBase(port = 8785): string {
	const address = Object.values(networkInterfaces())
		.flat()
		.find((a) => a && a.family === 'IPv4' && !a.internal)?.address;
	if (!address) throw new Error('No network address to reach the server as a phone would');
	return `http://${address}:${port}`;
}

/** A phone on the home network: not the owner until it is paired. */
export function phoneAtHome(browser: Browser): Promise<BrowserContext> {
	return browser.newContext({
		baseURL: homeBase(),
		viewport: { width: 390, height: 844 },
		isMobile: true,
		hasTouch: true,
		locale: 'gl-ES'
	});
}

/** A short WAV tone, a real audio file for the upload (the fake engine ignores what it sings). */
export function tone(seconds: number): Buffer {
	const rate = 22050;
	const samples = Math.round(seconds * rate);
	const wav = Buffer.alloc(44 + samples * 2);
	wav.write('RIFF', 0);
	wav.writeUInt32LE(36 + samples * 2, 4);
	wav.write('WAVE', 8);
	wav.write('fmt ', 12);
	wav.writeUInt32LE(16, 16);
	wav.writeUInt16LE(1, 20); // PCM
	wav.writeUInt16LE(1, 22); // mono
	wav.writeUInt32LE(rate, 24);
	wav.writeUInt32LE(rate * 2, 28);
	wav.writeUInt16LE(2, 32);
	wav.writeUInt16LE(16, 34);
	wav.write('data', 36);
	wav.writeUInt32LE(samples * 2, 40);
	for (let i = 0; i < samples; i++) {
		wav.writeInt16LE(Math.round(8000 * Math.sin((2 * Math.PI * 440 * i) / rate)), 44 + i * 2);
	}
	return wav;
}
