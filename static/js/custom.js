// Ten un axuste porque daba error ca barra de progreso cando o video se facia exitosamente


document.addEventListener('DOMContentLoaded', function() {
    hideLoading();
    
    window.addEventListener('beforeunload', function() {
        hideLoading();
    });
    
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
            
            const youtubeInput = this.querySelector('[name="youtube_url"]');
            const fileInput = this.querySelector('[name="video_file"]');
            
            if (youtubeInput && fileInput) {                
                if (!youtubeInput.value && (!fileInput.files || fileInput.files.length === 0)) {
                    event.preventDefault();
                    showAlert('Introduza unha URL de YouTube ou sube un arquivo MP4.');
                    return;
                }
                
                if (youtubeInput.value && !youtubeRegex.test(youtubeInput.value)) {
                    event.preventDefault();
                    showAlert('Por favor, introduce unha URL válida.');
                    return;
                }
            }
            
            showLoading('Procesando a solicitude...');
            
            //convertir a AJAX se é un dos formularios de karaoke
            const isKaraokeForm = form.getAttribute('action') === '/generate' || 
                                 form.getAttribute('action') === '/process_manual_lyrics';
            
            if (isKaraokeForm) {
                event.preventDefault();
                
                const formData = new FormData(form);     //esto recolle os datos do formulario
                
                fetch(form.action, {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) {
                        return response.text().then(text => {
                            throw new Error(text || 'Error no procesamento');
                        });
                    }
                    
                    const contentDisposition = response.headers.get('content-disposition');
                    let filename = 'karaoke.mp4';
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                        if (filenameMatch && filenameMatch[1]) {
                            filename = filenameMatch[1].replace(/['"]/g, '');
                        }
                    }
                    
                    return response.blob().then(blob => {
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        hideLoading();
                        showAlert('O karaoke xerouse correctamente', 'success');
                    });
                })
                .catch(error => {
                    hideLoading();
                    console.error('Erro:', error);
                    showAlert(error.message || 'Erro durante o procesamento');
                });
            }
        });
    });
    
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const fileInfo = this.parentNode.querySelector('.file-info');
            if (!fileInfo) return;
            
            if (this.files && this.files[0]) {
                const file = this.files[0];
                const size = (file.size / (1024 * 1024)).toFixed(2); 
                fileInfo.innerHTML = `<strong>${file.name}</strong> (${size} MB)`;
                fileInfo.style.display = 'block';
            } else {
                fileInfo.style.display = 'none';
            }
        });
    });
    
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            clearAlerts();
        });
    });
    
    //Esto e para manejar a casilla do diarization para mostrar ou ocultar o campo do token
    const diarizationCheckbox = document.getElementById('enable_diarization');
    const diarizationCheckboxManual = document.getElementById('enable_diarization_manual');
    const hfTokenGroup = document.getElementById('hf_token_group');
    const hfTokenGroupManual = document.getElementById('hf_token_group_manual');
    
    if (diarizationCheckbox && hfTokenGroup) {
        diarizationCheckbox.addEventListener('change', function() {
            if (this.checked) {
                hfTokenGroup.style.display = 'block';
            } else {
                hfTokenGroup.style.display = 'none';
            }
        });
    }
    
    if (diarizationCheckboxManual && hfTokenGroupManual) {
        diarizationCheckboxManual.addEventListener('change', function() {
            if (this.checked) {
                hfTokenGroupManual.style.display = 'block';
            } else {
                hfTokenGroupManual.style.display = 'none';
            }
        });
    }
});

function showLoading(message = 'Procesando...') {
    const loadingElement = document.getElementById('loading');
    const messageElement = loadingElement.querySelector('p');
    
    if (messageElement) {
        messageElement.textContent = message;
    }
    
    loadingElement.style.display = 'flex';
}

function hideLoading() {
    const loadingElement = document.getElementById('loading');
    loadingElement.style.display = 'none';
}

function showAlert(message, type = 'danger') {
    if (type === 'danger') {
        hideLoading();
    }
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type} alert-dismissible fade show`;
    alertElement.role = 'alert';
    
    alertElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertElement, container.firstChild);
    
    setTimeout(() => {
        alertElement.classList.remove('show');
        setTimeout(() => {
            alertElement.remove();
        }, 300);
    }, 5000);
}

function clearAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        alert.remove();
    });
}
