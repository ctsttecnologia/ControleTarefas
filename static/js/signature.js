

// static/js/signature.js

document.addEventListener('DOMContentLoaded', function () {
    const canvas = document.getElementById('signature-pad');
    const form = document.getElementById('signature-form');
    const clearButton = document.getElementById('clear-button');
    const hiddenInput = document.getElementById('assinatura_base64');

    // Verifica se todos os elementos essenciais existem
    if (!canvas || !form || !clearButton || !hiddenInput) {
        console.error("Um ou mais elementos do formulário de assinatura não foram encontrados. Verifique os IDs no HTML.");
        return;
    }

    // Inicializa a biblioteca no nosso canvas
    const signaturePad = new SignaturePad(canvas, {
        backgroundColor: 'rgb(255, 255, 255)', // Fundo branco
        penColor: 'rgb(0, 0, 0)' // Caneta preta
    });

    // Função para redimensionar o canvas corretamente em telas de alta resolução
    function resizeCanvas() {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        canvas.width = canvas.offsetWidth * ratio;
        canvas.height = canvas.offsetHeight * ratio;
        canvas.getContext("2d").scale(ratio, ratio);
        signaturePad.clear(); // Limpa a assinatura ao redimensionar
    }

    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();

    // Ação do botão de limpar
    clearButton.addEventListener('click', function (event) {
        signaturePad.clear();
    });

    // Ação ao submeter o formulário
    form.addEventListener('submit', function (event) {
        // Se o pad de assinatura estiver vazio, impede o envio
        if (signaturePad.isEmpty()) {
            alert("Por favor, forneça sua assinatura antes de salvar.");
            event.preventDefault(); 
        } else {
            // Converte a assinatura para uma imagem Base64 e a coloca no input oculto
            hiddenInput.value = signaturePad.toDataURL('image/png');
        }
    });
});