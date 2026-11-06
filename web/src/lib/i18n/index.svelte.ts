import { en } from './en';
import { es } from './es';
import { gl, type Messages } from './gl';
import type { Locale } from './plural';

export type { Locale } from './plural';
export type { Messages } from './gl';

export const LOCALES: readonly Locale[] = ['gl', 'es', 'en'];
/** Each language's name in itself, for the language picker. */
export const LOCALE_NAMES: Record<Locale, string> = {
	gl: 'Galego',
	es: 'Castellano',
	en: 'English'
};

const DICTIONARIES: Record<Locale, Messages> = { gl, es, en };
const STORAGE_KEY = 'foliada.locale';

const isLocale = (value: string | null): value is Locale =>
	value !== null && (LOCALES as readonly string[]).includes(value);

/** Languages whose speakers get the app in Galician unless they choose otherwise. */
const IBERIAN = ['gl', 'es', 'pt', 'ca', 'eu', 'ast'];

/**
 * The stored choice; else Galician (the app's language) for anyone whose browser speaks Galician
 * or another Iberian language; else English for browsers that speak English; else Galician.
 * Spanish is always one tap away in the settings.
 */
export function detectLocale(stored: string | null, languages: readonly string[]): Locale {
	if (isLocale(stored)) return stored;
	const bases = languages.map((language) => language.toLowerCase().split('-')[0]);
	if (bases.some((base) => IBERIAN.includes(base))) return 'gl';
	if (bases.includes('en')) return 'en';
	return 'gl';
}

let current = $state<Locale>('gl');

/** The interface language and its texts; reading them in a component re-renders on change. */
export const i18n = {
	get locale(): Locale {
		return current;
	},
	get t(): Messages {
		return DICTIONARIES[current];
	}
};

/** Switches language at once, without reloading (a song keeps playing), and remembers it. */
export function setLocale(locale: Locale): void {
	current = locale;
	document.documentElement.lang = locale;
	try {
		localStorage.setItem(STORAGE_KEY, locale);
	} catch {
		// Storage can be refused (private windows); the choice still holds for this visit.
	}
}

export function initLocale(): void {
	let stored: string | null = null;
	try {
		stored = localStorage.getItem(STORAGE_KEY);
	} catch {
		// As above: no storage, no remembered choice.
	}
	current = detectLocale(stored, navigator.languages ?? []);
	document.documentElement.lang = current;
}
