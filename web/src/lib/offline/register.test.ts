import { afterEach, describe, expect, it, vi } from 'vitest';
import { watchForUpdate } from './register';

class FakeWorker extends EventTarget {
	state: ServiceWorkerState = 'installing';
	readonly messages: unknown[] = [];
	postMessage(message: unknown) {
		this.messages.push(message);
	}
	become(state: ServiceWorkerState) {
		this.state = state;
		this.dispatchEvent(new Event('statechange'));
	}
}

class FakeRegistration extends EventTarget {
	installing: FakeWorker | null = null;
	waiting: FakeWorker | null = null;
	active: FakeWorker | null = new FakeWorker();
	/** The browser found a new version and starts installing it. */
	find(): FakeWorker {
		this.installing = new FakeWorker();
		this.dispatchEvent(new Event('updatefound'));
		return this.installing;
	}
}

function install(options: { controlled?: boolean; waiting?: boolean } = {}) {
	const registration = new FakeRegistration();
	if (options.waiting) registration.waiting = new FakeWorker();
	const container = Object.assign(new EventTarget(), {
		controller: options.controlled === false ? null : new FakeWorker(),
		ready: Promise.resolve(registration)
	});
	const reload = vi.fn();
	vi.stubGlobal('navigator', { serviceWorker: container });
	vi.stubGlobal('location', { reload });
	return { registration, container, reload };
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('watchForUpdate', () => {
	it('does nothing where there are no service workers', async () => {
		vi.stubGlobal('navigator', {});
		const onUpdate = vi.fn();
		expect(() => watchForUpdate(onUpdate)).not.toThrow();
		await settle();
		expect(onUpdate).not.toHaveBeenCalled();
	});

	it('offers a version that was already waiting when the page loaded', async () => {
		install({ waiting: true });
		const onUpdate = vi.fn();
		watchForUpdate(onUpdate);
		await settle();
		expect(onUpdate).toHaveBeenCalledOnce();
	});

	it('offers a version found while the page is open, once it is installed', async () => {
		const { registration } = install();
		const onUpdate = vi.fn();
		watchForUpdate(onUpdate);
		await settle();
		const worker = registration.find();
		expect(onUpdate).not.toHaveBeenCalled();
		registration.waiting = worker;
		worker.become('installed');
		expect(onUpdate).toHaveBeenCalledOnce();
	});

	it('does not offer the first install as an update', async () => {
		const { registration } = install({ controlled: false });
		const onUpdate = vi.fn();
		watchForUpdate(onUpdate);
		await settle();
		registration.find().become('installed');
		expect(onUpdate).not.toHaveBeenCalled();
	});

	it('applies by telling the new worker to take over, then reloads once', async () => {
		const { registration, container, reload } = install({ waiting: true });
		let apply = () => {};
		watchForUpdate((fn) => (apply = fn));
		await settle();
		const waiting = registration.waiting!;
		apply();
		expect(waiting.messages).toEqual([{ type: 'skip-waiting' }]);
		expect(reload).not.toHaveBeenCalled();
		container.dispatchEvent(new Event('controllerchange'));
		container.dispatchEvent(new Event('controllerchange'));
		expect(reload).toHaveBeenCalledOnce();
	});
});
