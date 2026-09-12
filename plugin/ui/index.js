function ttsComponent() {
    return {
        audioPlayer: null,

        init() {
            AM.tts = {
                speak: (text, voice) => this.speak(text, voice),
                stop: () => this.stop(),
                isPlaying: () => this.audioPlayer && !this.audioPlayer.paused,
            };
            AM.onCleanup(() => { this.stop(); });
        },

        async speak(text, voice = 'alloy') {
            try {
                this.stop();
                const resp = await AM.fetch('/plugins/tts', {
                    method: 'POST',
                    body: { text, voice },
                });
                if (!resp.ok) {
                    const e = await resp.json().catch(() => ({}));
                    if (resp.status === 503) { AM.toast('TTS not configured', 'warning'); return; }
                    AM.toast(e.detail || 'TTS failed', 'error');
                    return;
                }
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                this.audioPlayer = new Audio(url);
                this.audioPlayer.onended = () => { URL.revokeObjectURL(url); };
                this.audioPlayer.play();
            } catch (e) { AM.toast('TTS error: ' + e.message, 'error'); }
        },

        stop() {
            if (this.audioPlayer) {
                this.audioPlayer.pause();
                this.audioPlayer = null;
            }
        },
    };
}
