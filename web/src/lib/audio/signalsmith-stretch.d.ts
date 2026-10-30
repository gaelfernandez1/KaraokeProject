// The package ships no types; this is the part of its API the engine uses (see its README).
declare module 'signalsmith-stretch' {
	export interface StretchChange {
		output?: number;
		active?: boolean;
		semitones?: number;
		formantCompensation?: boolean;
	}
	export interface StretchNode extends AudioWorkletNode {
		// Every method is a message to the worklet and answers with a promise.
		schedule(change: StretchChange): Promise<unknown>;
		start(when?: number): Promise<unknown>;
		stop(when?: number): Promise<unknown>;
		/** Delay added in live input mode, in seconds. */
		latency(): Promise<number>;
	}
	export default function SignalsmithStretch(
		context: BaseAudioContext,
		options?: AudioWorkletNodeOptions
	): Promise<StretchNode>;
}
