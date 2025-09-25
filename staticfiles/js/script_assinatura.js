document.addEventListener('DOMContentLoaded', function() {
    const assinaturaModal = document.getElementById('assinaturaModal');
    if (assinaturaModal) {
        const formAssinatura = document.getElementById('formAssinatura');
        const canvas = document.getElementById('signature-pad');
        const signaturePad = new SignaturePad(canvas, {
            backgroundColor: 'rgb(248, 249, 250)'
        });

        const signatureTypeInput = document.getElementById('signature_type');
        const drawTabButton = document.getElementById('draw-tab');
        const uploadTabButton = document.getElementById('upload-tab');
        const fileInput = document.getElementById('assinatura_imagem_upload');

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
                    document.getElementById('assinatura_base64').value = signaturePad.toDataURL('image/png');
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
        assinaturaModal.addEventListener('shown.bs.modal', resizeCanvas);
        document.getElementById('clear-signature').addEventListener('click', () => signaturePad.clear());

        assinaturaModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const url = button.getAttribute('data-url');
            formAssinatura.setAttribute('action', url);
            drawTabButton.click();
            signatureTypeInput.value = 'draw';
        });
    }
});


