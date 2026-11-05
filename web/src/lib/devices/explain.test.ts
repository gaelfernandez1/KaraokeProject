import { describe, expect, it } from 'vitest';
import { ApiError } from '#lib/api';
import { gl } from '#lib/i18n/gl.js';
import { explain, jobError, needsPairing } from './explain';

describe('explain', () => {
	it('says in the language why the server refused', () => {
		const error = new ApiError(422, 'Songs can last up to 20 minutes', 'too_long');
		expect(explain(error, 'fallo', gl)).toBe(gl.errors.server.too_long);
	});

	it('says the server cannot be reached', () => {
		expect(explain(new ApiError(0, 'network'), 'fallo', gl)).toBe(gl.errors.network);
	});

	it('falls back for unknown codes and other errors', () => {
		expect(explain(new ApiError(500, 'x', 'mystery'), 'fallo', gl)).toBe('fallo');
		expect(explain(new Error('x'), 'fallo', gl)).toBe('fallo');
	});

	it('knows when pairing would help', () => {
		expect(needsPairing(new ApiError(403, 'x', 'not_owner'))).toBe(true);
		expect(needsPairing(new ApiError(403, 'x', 'not_paired'))).toBe(true);
		expect(needsPairing(new ApiError(403, 'x', 'not_allowed'))).toBe(false);
		expect(needsPairing(new Error('x'))).toBe(false);
	});

	it("explains a failed job by its code, or with the server's words", () => {
		expect(jobError({ error_code: 'gpu_memory', error: 'CUDA out of memory' }, 'fallo', gl)).toBe(
			gl.errors.server.gpu_memory
		);
		expect(jobError({ error_code: null, error: 'Something else' }, 'fallo', gl)).toBe(
			'Something else'
		);
		expect(jobError({ error_code: null, error: null }, 'fallo', gl)).toBe('fallo');
	});
});
