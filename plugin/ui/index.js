const TTS_VOICES = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'];
const TTS_CACHE_LIMIT = 10;

function ttsComponent() {
    return {
        state: 'idle',
        audioPlayer: null,
        objectUrl: null,
        cache: new Map(),
        _speakToken: 0,

        init() {
            const pill = this.$el.querySelector('.tts-pill');
            if (pill) document.body.appendChild(pill);
            if (!document.getElementById('tts-pill-css')) {
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.id = 'tts-pill-css';
                link.href = '/plugins/tts/ui/style.css?v=' + (window.AM_CACHE_V || '');
                document.head.appendChild(link);
            }
            AM.tts = {
                speak: (text, voice) => this.speak(text, voice),
                stop: () => this.stop(),
                isPlaying: () => this.state === 'playing',
                setVoice: (voice) => this.setVoice(voice),
                getVoice: () => this.getVoice(),
                state: 'idle',
            };
            AM.onCleanup(() => {
                this.stop();
                const pill = document.body.querySelector('.tts-pill');
                if (pill) pill.remove();
            });
        },

        getVoice() {
            const voice = localStorage.getItem('am-tts-voice');
            return TTS_VOICES.includes(voice) ? voice : 'alloy';
        },

        setVoice(voice) {
            if (!TTS_VOICES.includes(voice)) return;
            localStorage.setItem('am-tts-voice', voice);
        },

        setState(state) {
            this.state = state;
            AM.tts.state = state;
        },

        async speak(text, voice) {
            const v = voice || this.getVoice();
            this.stop();
            const token = ++this._speakToken;
            this.setState('synthesizing');
            try {
                let blob = this.cache.get(text + '|' + v);
                if (!blob) {
                    const resp = await AM.fetch('/plugins/tts', {
                        method: 'POST',
                        body: { text, voice: v },
                    });
                    if (token !== this._speakToken) return;
                    if (!resp.ok) {
                        const e = await resp.json().catch(() => ({}));
                        this.setState('idle');
                        if (resp.status === 503) { AM.toast('TTS not configured', 'warning'); return; }
                        AM.toast(e.detail || 'TTS failed', 'error');
                        return;
                    }
                    blob = await resp.blob();
                    if (token !== this._speakToken) return;
                    this.cache.set(text + '|' + v, blob);
                    if (this.cache.size > TTS_CACHE_LIMIT) {
                        this.cache.delete(this.cache.keys().next().value);
                    }
                }
                const url = URL.createObjectURL(blob);
                this.objectUrl = url;
                const player = new Audio(url);
                this.audioPlayer = player;
                player.onended = () => {
                    if (this.objectUrl === url) {
                        URL.revokeObjectURL(url);
                        this.objectUrl = null;
                        this.audioPlayer = null;
                    }
                    if (token === this._speakToken) this.setState('idle');
                };
                player.onerror = () => this.stop();
                await player.play();
                if (token !== this._speakToken) return;
                this.setState('playing');
            } catch (e) {
                if (token === this._speakToken) this.setState('idle');
                AM.toast('TTS error: ' + e.message, 'error');
            }
        },

        stop() {
            if (this.audioPlayer) {
                this.audioPlayer.pause();
                this.audioPlayer = null;
            }
            if (this.objectUrl) {
                URL.revokeObjectURL(this.objectUrl);
                this.objectUrl = null;
            }
            this._speakToken++;
            this.setState('idle');
        },
    };
}
