document.addEventListener('DOMContentLoaded', function() {
    // Inicializar a assinatura
    const canvas = document.querySelector("#signature-pad canvas");
    const signaturePad = new SignaturePad(canvas);
    const hiddenInput = document.getElementById('id_assinatura');
    
    document.getElementById('clear-signature').addEventListener('click', function() {
        signaturePad.clear();
        hiddenInput.value = '';
    });
    
    // Atualizar o campo oculto quando a assinatura muda
    canvas.addEventListener('mouseup', function() {
        if (!signaturePad.isEmpty()) {
            hiddenInput.value = signaturePad.toDataURL();
        }
    });
    
    // Preview das fotos
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    const previewId = `preview-${input.id}`;
                    let preview = document.getElementById(previewId);
                    if (!preview) {
                        preview = document.createElement('img');
                        preview.id = previewId;
                        preview.className = 'photo-preview';
                        input.parentNode.appendChild(preview);
                    }
                    preview.src = event.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    });
});