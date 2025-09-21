// static/js/signature.js

document.addEventListener('DOMContentLoaded', function() {
    const formAssinatura = document.getElementById('formAssinatura');
    const canvas = document.getElementById('signature-canvas');
    const clearButton = document.getElementById('clear-signature');
    const hiddenInput = document.getElementById('assinatura_base64');
    const signatureTypeInput = document.getElementById('signature_type');
    const drawTabButton = document.getElementById('draw-tab');
    const uploadTabButton = document.getElementById('upload-tab');
    const fileInput = document.getElementById('assinatura_imagem_upload');

    // Agora a verificação de existência vai funcionar corretamente
    if (!canvas || !formAssinatura || !clearButton || !hiddenInput || !signatureTypeInput || !drawTabButton || !uploadTabButton || !fileInput) {
        console.error("Um ou mais elementos do formulário de assinatura não foram encontrados. Verifique os IDs no HTML.");
        // Remova o 'return' temporariamente para ver qual elemento está faltando
        // return; 
    }

    const signaturePad = new SignaturePad(canvas, {
        backgroundColor: 'rgb(248, 249, 250)'
    });

    drawTabButton.addEventListener('click', function() {
        signatureTypeInput.value = 'draw';
    });

    uploadTabButton.addEventListener('click', function() {
        signatureTypeInput.value = 'upload';
    });

    formAssinatura.addEventListener('submit', function(event) {
        if (signatureTypeInput.value === 'draw') {
            if (signaturePad.isEmpty()) {
                alert("Por favor, desenhe uma assinatura para salvar.");
                event.preventDefault();
            } else {
                hiddenInput.value = signaturePad.toDataURL('image/png');
            }
        } else if (signatureTypeInput.value === 'upload') {
            if (fileInput.files.length === 0) {
                alert("Por favor, selecione um arquivo de imagem para salvar.");
                event.preventDefault();
            }
        }
    });

    function resizeCanvas() {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        canvas.width = canvas.offsetWidth * ratio;
        canvas.height = canvas.offsetHeight * ratio;
        canvas.getContext("2d").scale(ratio, ratio);
        signaturePad.clear();
    }

    window.addEventListener("resize", resizeCanvas);
    resizeCanvas(); // Chamada inicial para redimensionar o canvas
    
    // Apenas para garantir que funcione se a chamada inicial falhar.
    setTimeout(resizeCanvas, 200); 

    if (clearButton) {
        clearButton.addEventListener('click', () => signaturePad.clear());
    }
});
