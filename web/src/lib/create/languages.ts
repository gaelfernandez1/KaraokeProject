/**
 * Languages a song can be in, each named in itself, so everyone finds theirs whatever the
 * interface language. Galician first, then the languages most sung around it, then the rest
 * alphabetically. The engine has dedicated models for gl, es, pt, en, fr and de and a
 * multilingual one for the others.
 */
export const LANGUAGES: readonly { code: string; name: string }[] = [
	{ code: 'gl', name: 'Galego' },
	{ code: 'es', name: 'Español' },
	{ code: 'pt', name: 'Português' },
	{ code: 'en', name: 'English' },
	{ code: 'fr', name: 'Français' },
	{ code: 'de', name: 'Deutsch' },
	{ code: 'ca', name: 'Català' },
	{ code: 'eu', name: 'Euskara' },
	{ code: 'it', name: 'Italiano' },
	{ code: 'ast', name: 'Asturianu' },
	{ code: 'br', name: 'Brezhoneg' },
	{ code: 'cy', name: 'Cymraeg' },
	{ code: 'da', name: 'Dansk' },
	{ code: 'ga', name: 'Gaeilge' },
	{ code: 'ja', name: '日本語' },
	{ code: 'ko', name: '한국어' },
	{ code: 'nl', name: 'Nederlands' },
	{ code: 'no', name: 'Norsk' },
	{ code: 'pl', name: 'Polski' },
	{ code: 'ro', name: 'Română' },
	{ code: 'sv', name: 'Svenska' },
	{ code: 'tr', name: 'Türkçe' },
	{ code: 'uk', name: 'Українська' }
];

const NAMES = new Map(LANGUAGES.map((l) => [l.code, l.name]));

/** A language's own name, or its code when it is not in the list. */
export function languageName(code: string): string {
	return NAMES.get(code) ?? code;
}
