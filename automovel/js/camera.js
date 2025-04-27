function setupCameraField(inputId, previewId, coordinatesId) {
    const fileInput = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    const coordinatesInput = document.getElementById(coordinatesId);
    const coordinatesContainer = preview.parentElement.querySelector('.coordinates-container');
    
    // Ouvinte para quando uma imagem é selecionada
    fileInput.addEventListener('change', function(e) {
        if (fileInput.files && fileInput.files[0]) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                // Limpa o preview e adiciona a nova imagem
                preview.innerHTML = '';
                const img = document.createElement('img');
                img.src = e.target.result;
                img.alt = 'Foto capturada';
                
                // Adiciona funcionalidade de marcar avarias
                img.style.cursor = 'crosshair';
                img.addEventListener('click', function(e) {
                    markDamage(e, img, coordinatesInput);
                });
                
                preview.appendChild(img);
                coordinatesContainer.style.display = 'block';
            };
            
            reader.readAsDataURL(fileInput.files[0]);
        }
    });
    
    // Função para marcar avarias na imagem
    function markDamage(event, imgElement, coordInput) {
        const rect = imgElement.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width * 100).toFixed(2);
        const y = ((event.clientY - rect.top) / rect.height * 100).toFixed(2);
        
        // Cria marcador
        const marker = document.createElement('div');
        marker.className = 'damage-marker';
        marker.style.left = `${x}%`;
        marker.style.top = `${y}%`;
        
        // Adiciona ao preview
        imgElement.parentElement.appendChild(marker);
        
        // Atualiza coordenadas no input
        let coordinates = [];
        if (coordInput.value) {
            coordinates = JSON.parse(coordInput.value);
        }
        coordinates.push({x, y});
        coordInput.value = JSON.stringify(coordinates);
    }
}

function setupCameraField(inputId, previewId, coordinatesId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    
    input.addEventListener('change', function(e) {
        if (e.target.files && e.target.files[0]) {
            const reader = new FileReader();
            
            reader.onload = function(event) {
                preview.innerHTML = `<img src="${event.target.result}" alt="Preview" style="max-width: 100%;">`;
                
                // Ativa o clique para marcar avarias (se necessário)
                const img = preview.querySelector('img');
                if (img && coordinatesId) {
                    setupDamageMarking(img, coordinatesId);
                }
            };
            
            reader.readAsDataURL(e.target.files[0]);
        }
    });
}

function setupDamageMarking(imgElement, coordinatesFieldId) {
    const coordinates = [];
    const coordinatesField = document.getElementById(coordinatesFieldId);
    
    imgElement.addEventListener('click', function(e) {
        const rect = e.target.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Adiciona marcador visual
        const marker = document.createElement('div');
        marker.style.position = 'absolute';
        marker.style.left = `${x - 5}px`;
        marker.style.top = `${y - 5}px`;
        marker.style.width = '10px';
        marker.style.height = '10px';
        marker.style.backgroundColor = 'red';
        marker.style.borderRadius = '50%';
        e.target.parentNode.appendChild(marker);
        
        // Armazena coordenadas (relativas à imagem)
        const relX = x / rect.width;
        const relY = y / rect.height;
        coordinates.push({x: relX, y: relY});
        
        // Atualiza campo oculto
        coordinatesField.value = JSON.stringify(coordinates);
    });
}