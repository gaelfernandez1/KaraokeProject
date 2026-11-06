import prettier from 'eslint-config-prettier';
import path from 'node:path';
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import { defineConfig, includeIgnoreFile } from 'eslint/config';
import globals from 'globals';
import ts from 'typescript-eslint';

const gitignorePath = path.resolve(import.meta.dirname, '.gitignore');
const typedRules = Object.fromEntries(
	ts.configs.recommendedTypeCheckedOnly
		.flatMap((config) => Object.entries(config.rules ?? {}))
		.filter(([name]) => name.startsWith('@typescript-eslint/'))
);

export default defineConfig(
	includeIgnoreFile(gitignorePath),
	{ ignores: ['src/lib/contracts/generated/', 'src/lib/api/generated/'] },
	js.configs.recommended,
	ts.configs.recommended,
	svelte.configs.recommended,
	prettier,
	svelte.configs.prettier,
	{
		languageOptions: { globals: { ...globals.browser, ...globals.node } },
		rules: {
			// typescript-eslint strongly recommend that you do not use the no-undef lint rule on TypeScript projects.
			// see: https://typescript-eslint.io/troubleshooting/faqs/eslint/#i-get-errors-from-the-no-undef-rule-about-global-variables-not-being-defined-even-though-there-are-no-typescript-errors
			'no-undef': 'off'
		}
	},
	{
		files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: {
			parserOptions: {
				projectService: true,
				extraFileExtensions: ['.svelte'],
				parser: ts.parser
			}
		}
	},
	{
		// The app itself (what ships to phones and TVs) also gets the rules that need types:
		// promises nobody awaits and `any` flowing out of JSON. (no-unnecessary-condition was tried:
		// it only flagged feature detection and guards for older packages, which must stay.)
		files: ['src/**/*.ts', 'src/**/*.svelte'],
		languageOptions: {
			parserOptions: {
				projectService: true,
				extraFileExtensions: ['.svelte'],
				parser: ts.parser,
				tsconfigRootDir: import.meta.dirname
			}
		},
		rules: {
			// Only the typed rules: the configs also set the TS parser, which would replace Svelte's.
			...typedRules,
			// An async function without await is often an interface (a store, a fake): not a bug.
			'@typescript-eslint/require-await': 'off'
		}
	},
	{
		// Svelte's template expressions reach the type checker as `any` (event handlers, bindings):
		// the unsafe-any rules only see that gap there.
		files: ['src/**/*.svelte'],
		rules: {
			'@typescript-eslint/no-unsafe-argument': 'off',
			'@typescript-eslint/no-unsafe-assignment': 'off',
			'@typescript-eslint/no-unsafe-call': 'off',
			'@typescript-eslint/no-unsafe-member-access': 'off',
			'@typescript-eslint/no-unsafe-return': 'off'
		}
	},
	{
		// Generated from the OpenAPI and JSON Schemas.
		files: ['src/lib/*/generated/**'],
		extends: [ts.configs.disableTypeChecked]
	}
);
