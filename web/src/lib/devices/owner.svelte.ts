import { getMe, type Me } from '#lib/api';

/**
 * Who this device is to the server: the laptop itself, a paired device, or a visitor (a phone at
 * home may browse and sing; away from home it must be paired first). Asked once per visit.
 */
class Owner {
	me = $state<Me | null>(null);

	get isOwner(): boolean {
		return this.me?.owner ?? false;
	}

	async refresh(): Promise<void> {
		try {
			this.me = await getMe();
		} catch {
			// Offline or no server: what was known still stands.
		}
	}
}

export const owner = new Owner();
