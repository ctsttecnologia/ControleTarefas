document.addEventListener('DOMContentLoaded', function() {
    // Função para capturar imagem da câmera
    function captureCamera(elementId) {
        const input = document.getElementById(elementId);
        const video = document.createElement('video');
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(function(stream) {
                    video.srcObject = stream;
                    video.play();
                    
                    // Mostrar preview da câmera
                    const preview = document.getElementById(`${elementId}-preview`);
                    preview.innerHTML = '';
                    preview.appendChild(video);
                    
                    // Botão para capturar imagem
                    const captureBtn = document.createElement('button');
                    captureBtn.textContent = 'Capturar';
                    captureBtn.className = 'btn btn-primary mt-2';
                    captureBtn.onclick = function() {
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        context.drawImage(video, 0, 0, canvas.width, canvas.height);
                        
                        // Converter para base64 e definir no campo de input
                        const dataUrl = canvas.toDataURL('image/png');
                        input.value = dataUrl;
                        
                        // Mostrar imagem capturada
                        const img = document.createElement('img');
                        img.src = dataUrl;
                        img.className = 'img-thumbnail mt-2';
                        preview.innerHTML = '';
                        preview.appendChild(img);
                        
                        // Parar stream de vídeo
                        stream.getTracks().forEach(track => track.stop());
                    };
                    
                    preview.appendChild(captureBtn);
                })
                .catch(function(error) {
                    console.error('Erro ao acessar câmera:', error);
                });
        }
    }
    
    // Configurar captura para cada campo de imagem
    const imageFields = ['foto_frontal', 'foto_trazeira', 'foto_lado_motorista', 'foto_lado_passageiro'];
    imageFields.forEach(function(fieldId) {
        const field = document.getElementById(`id_${fieldId}`);
        if (field) {
            field.style.display = 'none';
            
            const container = document.createElement('div');
            container.id = `${fieldId}-preview`;
            container.className = 'camera-preview mb-3';
            field.parentNode.insertBefore(container, field.nextSibling);
            
            const btn = document.createElement('button');
            btn.textContent = 'Abrir Câmera';
            btn.className = 'btn btn-sm btn-outline-primary';
            btn.onclick = function(e) {
                e.preventDefault();
                captureCamera(fieldId);
            };
            container.appendChild(btn);
        }
    });
});

