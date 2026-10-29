// The package ships no types; this is the part of its API the engine uses (see its README).
declare module 'signalsmith-stretch' {
	export interface StretchChange {
		output?: number;
		active?: boolean;
		semitones?: number;
		formantCompensation?: boolean;
	}
	export interface StretchNode extends AudioWorkletNode {
		schedule(change: StretchChange): void;
		start(when?: number): void;
		stop(when?: number): void;
		/** Delay added in live input mode, in seconds. */
		latency(): number;
	}
	export default function SignalsmithStretch(
		context: BaseAudioContext,
		options?: AudioWorkletNodeOptions
	): Promise<StretchNode>;
}
