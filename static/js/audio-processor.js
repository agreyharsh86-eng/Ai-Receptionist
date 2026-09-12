/**
 * Microphone Audio Capture & 16kHz PCM Streamer.
 * Captures user voice, resamples to 16,000Hz mono 16-bit PCM, and pushes chunks.
 */
class PcmAudioRecorder {
    constructor(options = {}) {
        this.targetSampleRate = options.targetSampleRate || 16000;
        this.bufferSize = options.bufferSize || 4096;
        this.onAudioChunk = options.onAudioChunk || null;
        this.onVolumeChange = options.onVolumeChange || null;

        this.audioCtx = null;
        this.mediaStream = null;
        this.sourceNode = null;
        this.processorNode = null;
        this.analyser = null;
        this.isRecording = false;
        this.isMuted = false;
    }

    async start() {
        if (this.isRecording) return;

        this.mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                channelCount: 1
            }
        });

        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.audioCtx = new AudioContext();

        this.sourceNode = this.audioCtx.createMediaStreamSource(this.mediaStream);
        this.analyser = this.audioCtx.createAnalyser();
        this.analyser.fftSize = 128;
        this.sourceNode.connect(this.analyser);

        // Use ScriptProcessorNode for wide browser compatibility
        this.processorNode = this.audioCtx.createScriptProcessor(this.bufferSize, 1, 1);

        this.processorNode.onaudioprocess = (e) => {
            if (!this.isRecording || this.isMuted) return;

            const inputData = e.inputBuffer.getChannelData(0);
            const inputSampleRate = this.audioCtx.sampleRate;

            // Downsample input data to targetSampleRate (16kHz)
            const resampledData = this._resample(inputData, inputSampleRate, this.targetSampleRate);

            // Convert Float32 to 16-bit PCM
            const pcm16 = this._floatTo16BitPCM(resampledData);

            // Convert to Base64
            const base64Chunk = this._arrayBufferToBase64(pcm16.buffer);

            if (this.onAudioChunk) {
                this.onAudioChunk(base64Chunk);
            }

            // Compute volume level for UI
            if (this.onVolumeChange) {
                let sum = 0;
                for (let i = 0; i < inputData.length; i++) {
                    sum += inputData[i] * inputData[i];
                }
                const rms = Math.sqrt(sum / inputData.length);
                this.onVolumeChange(Math.min(1.0, rms * 5));
            }
        };

        this.sourceNode.connect(this.processorNode);
        this.processorNode.connect(this.audioCtx.destination);
        this.isRecording = true;
    }

    setMuted(muted) {
        this.isMuted = muted;
    }

    _resample(data, fromSampleRate, toSampleRate) {
        if (fromSampleRate === toSampleRate) return data;
        const ratio = fromSampleRate / toSampleRate;
        const newLength = Math.round(data.length / ratio);
        const result = new Float32Array(newLength);
        let offsetResult = 0;
        let offsetBuffer = 0;

        while (offsetResult < result.length) {
            const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
            let accum = 0;
            let count = 0;
            for (let i = offsetBuffer; i < nextOffsetBuffer && i < data.length; i++) {
                accum += data[i];
                count++;
            }
            result[offsetResult] = count > 0 ? accum / count : 0;
            offsetResult++;
            offsetBuffer = nextOffsetBuffer;
        }
        return result;
    }

    _floatTo16BitPCM(float32Array) {
        const pcm16 = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return pcm16;
    }

    _arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        const len = bytes.byteLength;
        for (let i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    }

    stop() {
        this.isRecording = false;
        if (this.processorNode) {
            this.processorNode.disconnect();
            this.processorNode = null;
        }
        if (this.sourceNode) {
            this.sourceNode.disconnect();
            this.sourceNode = null;
        }
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        if (this.audioCtx) {
            this.audioCtx.close();
            this.audioCtx = null;
        }
    }
}

window.PcmAudioRecorder = PcmAudioRecorder;
