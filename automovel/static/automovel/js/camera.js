/**
 * Configura o campo de captura de imagem com visualização e marcação de avarias
 * @param {string} inputId - ID do input file
 * @param {string} previewId - ID do elemento de visualização
 * @param {string} coordinatesId - ID do input hidden para coordenadas (opcional)
 */
function setupCameraField(inputId, previewId, coordinatesId = null) {
    const fileInput = document.getElementById(inputId);
    const previewContainer = document.getElementById(previewId);
    const coordinatesInput = coordinatesId ? document.getElementById(coordinatesId) : null;
    
    if (!fileInput || !previewContainer) {
        console.error('Elementos não encontrados para:', {inputId, previewId});
        return;
    }

    fileInput.addEventListener('change', function(e) {
        if (fileInput.files && fileInput.files[0]) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                // Limpa o preview anterior
                previewContainer.innerHTML = '';
                
                // Cria e configura a nova imagem
                const img = new Image();
                img.src = e.target.result;
                img.alt = 'Foto capturada';
                img.style.maxWidth = '100%';
                img.style.height = 'auto';
                
                // Adiciona a imagem ao container
                previewContainer.appendChild(img);
                
                // Configura marcação de avarias se necessário
                if (coordinatesInput) {
                    setupDamageMarking(img, coordinatesInput);
                }
            };
            
            reader.onerror = function() {
                console.error('Erro ao ler a imagem');
                previewContainer.innerHTML = '<p class="error">Erro ao carregar imagem</p>';
            };
            
            reader.readAsDataURL(fileInput.files[0]);
        }
    });
}

/**
 * Configura a funcionalidade de marcação de avarias na imagem
 * @param {HTMLImageElement} imgElement - Elemento de imagem
 * @param {HTMLInputElement} coordinatesInput - Input para armazenar coordenadas
 */
function setupDamageMarking(imgElement, coordinatesInput) {
    let coordinates = [];
    
    // Tenta carregar coordenadas existentes
    try {
        coordinates = coordinatesInput.value ? JSON.parse(coordinatesInput.value) : [];
    } catch (e) {
        console.error('Erro ao parsear coordenadas:', e);
        coordinates = [];
    }
    
    // Adiciona marcadores existentes
    coordinates.forEach(coord => {
        addDamageMarker(imgElement, coord.x, coord.y, false);
    });
    
    // Configura o listener para novos cliques
    imgElement.style.cursor = 'crosshair';
    imgElement.addEventListener('click', function(e) {
        const rect = imgElement.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        
        // Adiciona novo marcador
        addDamageMarker(imgElement, x, y, true);
        
        // Armazena coordenada
        coordinates.push({x, y});
        coordinatesInput.value = JSON.stringify(coordinates);
    });
}

/**
 * Adiciona um marcador visual de avaria na imagem
 * @param {HTMLImageElement} imgElement - Elemento de imagem
 * @param {number} x - Posição horizontal relativa (0-1)
 * @param {number} y - Posição vertical relativa (0-1)
 * @param {boolean} animate - Se deve animar o marcador
 */
function addDamageMarker(imgElement, x, y, animate = false) {
    const marker = document.createElement('div');
    marker.className = 'damage-marker';
    
    // Posiciona o marcador
    marker.style.position = 'absolute';
    marker.style.left = `${x * 100}%`;
    marker.style.top = `${y * 100}%`;
    
    // Estilos do marcador
    marker.style.width = '12px';
    marker.style.height = '12px';
    marker.style.backgroundColor = 'rgba(255, 0, 0, 0.7)';
    marker.style.border = '2px solid white';
    marker.style.borderRadius = '50%';
    marker.style.transform = 'translate(-50%, -50%)';
    marker.style.pointerEvents = 'none';
    
    if (animate) {
        marker.style.animation = 'pulse 0.5s';
    }
    
    // Adiciona ao container da imagem
    imgElement.parentNode.appendChild(marker);
}

// Adiciona estilos dinâmicos se necessário
function addDynamicStyles() {
    if (!document.getElementById('camera-js-styles')) {
        const style = document.createElement('style');
        style.id = 'camera-js-styles';
        style.textContent = `
            .damage-marker {
                position: absolute;
                pointer-events: none;
            }
            @keyframes pulse {
                0% { transform: translate(-50%, -50%) scale(1); }
                50% { transform: translate(-50%, -50%) scale(1.5); }
                100% { transform: translate(-50%, -50%) scale(1); }
            }
            .error {
                color: #dc3545;
                padding: 10px;
                background: #f8d7da;
                border-radius: 4px;
            }
        `;
        document.head.appendChild(style);
    }
}

// Inicializa os estilos quando o script carrega
addDynamicStyles();

