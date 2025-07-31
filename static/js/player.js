
class KaraokePlayer {
    constructor() {
        this.video = document.getElementById('karaokeVideo');
        this.vocalAudio = document.getElementById('vocalAudio');
        this.instrumentalAudio = document.getElementById('instrumentalAudio');
        
        this.vocalVolumeSlider = document.getElementById('vocalVolume');
        this.instrumentalVolumeSlider = document.getElementById('instrumentalVolume');
        this.vocalVolumeValue = document.getElementById('vocalVolumeValue');
        this.instrumentalVolumeValue = document.getElementById('instrumentalVolumeValue');
        
        this.playPauseBtn = document.getElementById('playPauseBtn');
        this.playPauseIcon = document.getElementById('playPauseIcon');
        
        this.isPlaying = false;
        
        this.init();
    }
    
    init() {
        this.video.volume = 0;
        this.video.muted = true;
        
        this.vocalAudio.volume = 0.05; // 5%
        this.instrumentalAudio.volume = 1.0; // 100%
        this.setupEventListeners();
        this.setupSynchronization();
        
        console.log('reprodutor de karaoke inicializado');
    }
    
    setupEventListeners() {
        this.vocalVolumeSlider.addEventListener('input', (e) => {
            const volume = e.target.value / 100;
            this.vocalAudio.volume = volume;
            this.vocalVolumeValue.textContent = `${e.target.value}%`;
        });
        
        this.instrumentalVolumeSlider.addEventListener('input', (e) => {
            const volume = e.target.value / 100;
            this.instrumentalAudio.volume = volume;
            this.instrumentalVolumeValue.textContent = `${e.target.value}%`;
        });
        
        this.playPauseBtn.addEventListener('click', () => {
            this.togglePlayPause();
        });
        
        this.video.addEventListener('seeked', () => {
            this.syncAudioToVideo();
        });
        
        //Control de teclado
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space') {
                e.preventDefault();
                this.togglePlayPause();
            }
        });
    }
    
    setupSynchronization() {
        //sincronizar audio con video cada 100ms
        setInterval(() => {
            if (this.isPlaying) {
                this.syncAudioToVideo();
            }
        }, 100);
    }
    
    syncAudioToVideo() {
        const videoTime = this.video.currentTime;
        
        //Sincronizar se hai desviación de mais de 0.2 segundos
        if (Math.abs(this.vocalAudio.currentTime - videoTime) > 0.2) {
            this.vocalAudio.currentTime = videoTime;
        }
        
        if (Math.abs(this.instrumentalAudio.currentTime - videoTime) > 0.2) {
            this.instrumentalAudio.currentTime = videoTime;
        }
    }
    
    async togglePlayPause() {
        try {
            if (this.isPlaying) {
                this.video.pause();
                this.vocalAudio.pause();
                this.instrumentalAudio.pause();
                
                this.playPauseIcon.className = 'fas fa-play';
                this.isPlaying = false;
            } else {
                this.syncAudioToVideo();
                
                await this.video.play();
                await this.vocalAudio.play();
                await this.instrumentalAudio.play();
                
                this.playPauseIcon.className = 'fas fa-pause';
                this.isPlaying = true;
            }
        } catch (error) {
            console.error('Erro ao reproducir:', error);
            this.showError('Erro ao reproducir. Están os arquivos dipoñibles?.');
        }
    }
    
    
    showError(message) {
        let errorDiv = document.getElementById('playerError');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'playerError';
            errorDiv.className = 'alert alert-danger mt-3';
            document.querySelector('.player-container').appendChild(errorDiv);
        }
        
        errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
        
        // Ocultar despois de 5 segundos
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado, inicializando reprodutor de karaoke...');
    
    setTimeout(() => {
        window.karaokePlayer = new KaraokePlayer();
    }, 500);
});

window.debugPlayer = function() {
    const player = window.karaokePlayer;
    if (player) {
        console.log('tempoVideo:', player.video.currentTime);
        console.log('TempoVocal:', player.vocalAudio.currentTime);
        console.log('TempoInstrumental:', player.instrumentalAudio.currentTime);
        console.log('VolumeVideo:', player.video.volume);
        console.log('VolumeVocal:', player.vocalAudio.volume);
        console.log('VolumeInstrumental:', player.instrumentalAudio.volume);
    }
};