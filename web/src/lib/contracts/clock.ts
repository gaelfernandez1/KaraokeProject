/**
 * Where the lyrics renderer reads the song position from. The audio engine provides it;
 * `now()` returns seconds of song audio at this instant, with the output latency
 * (HDMI, Bluetooth) already compensated.
 */
export interface PlaybackClock {
	now(): number;
}
