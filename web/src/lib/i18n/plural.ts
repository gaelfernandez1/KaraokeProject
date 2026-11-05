export type Locale = 'gl' | 'es' | 'en';

/**
 * The plural form of `forms` for `n` in `locale`, with `#` replaced by the number written the
 * locale's way.
 */
export function plural(n: number, locale: Locale, forms: { one: string; other: string }): string {
	const form = new Intl.PluralRules(locale).select(n) === 'one' ? forms.one : forms.other;
	return form.replaceAll('#', new Intl.NumberFormat(locale).format(n));
}
