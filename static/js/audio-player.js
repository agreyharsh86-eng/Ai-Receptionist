/**
 * Gapless PCM Audio Player for Gemini Live 24kHz Audio Output.
 * Handles queueing, scheduled playback, and instantaneous interruption handling.
 */
class PcmAudioPlayer {
    constructor(sampleRate = 24000) {
        this.sampleRate = sampleRate;
        this.audioCtx = null;
        this.analyser = null;
        this.nextStartTime = 0;
        this.activeSources = [];
        this.isPlaying = false;
        this.onPlaybackStateChange = null;
    }

    init() {
        if (!this.audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioCtx = new AudioContext({ sampleRate: this.sampleRate });
            this.analyser = this.audioCtx.createAnalyser();
            this.analyser.fftSize = 128;
            this.analyser.smoothingTimeConstant = 0.8;
            this.analyser.connect(this.audioCtx.destination);
        }
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }
    }

    /**
     * Decode base64 PCM 16-bit mono into Float32Array
     */
    base64ToFloat32(base64Str) {
        const binaryString = window.atob(base64Str);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        const int16Array = new Int16Array(bytes.buffer);
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            // Normalize to [-1.0, 1.0]
            float32Array[i] = int16Array[i] / 32768.0;
        }
        return float32Array;
    }

    /**
     * Queue and schedule incoming PCM audio chunk
     */
    playChunk(base64Chunk) {
        this.init();
        const float32Data = this.base64ToFloat32(base64Chunk);
        if (float32Data.length === 0) return;

        const buffer = this.audioCtx.createBuffer(1, float32Data.length, this.sampleRate);
        buffer.getChannelData(0).set(float32Data);

        const source = this.audioCtx.createBufferSource();
        source.buffer = buffer;
        source.connect(this.analyser);

        const currentTime = this.audioCtx.currentTime;
        if (this.nextStartTime < currentTime) {
            this.nextStartTime = currentTime + 0.02; // Tiny lead-in buffer to prevent crackle
        }

        source.start(this.nextStartTime);
        this.nextStartTime += buffer.duration;
        this.activeSources.push(source);

        if (!this.isPlaying) {
            this.isPlaying = true;
            if (this.onPlaybackStateChange) this.onPlaybackStateChange(true);
        }

        source.onended = () => {
            const idx = this.activeSources.indexOf(source);
            if (idx !== -1) {
                this.activeSources.splice(idx, 1);
            }
            if (this.activeSources.length === 0 && this.audioCtx.currentTime >= this.nextStartTime - 0.05) {
                this.isPlaying = false;
                if (this.onPlaybackStateChange) this.onPlaybackStateChange(false);
            }
        };
    }

    /**
     * Interrupt immediately: stop all current and queued audio buffers
     */
    interrupt() {
        for (const src of this.activeSources) {
            try {
                src.stop();
                src.disconnect();
            } catch (e) {
                // Ignore already stopped sources
            }
        }
        this.activeSources = [];
        if (this.audioCtx) {
            this.nextStartTime = this.audioCtx.currentTime;
        }
        this.isPlaying = false;
        if (this.onPlaybackStateChange) this.onPlaybackStateChange(false);
    }

    getFrequencyData() {
        if (!this.analyser) return new Uint8Array(0);
        const data = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(data);
        return data;
    }

    close() {
        this.interrupt();
        if (this.audioCtx) {
            this.audioCtx.close();
            this.audioCtx = null;
        }
    }
}

window.PcmAudioPlayer = PcmAudioPlayer;
