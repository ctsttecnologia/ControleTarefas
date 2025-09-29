// static/js/signature.js

class SignaturePadComponent {
    /**
     * @param {HTMLElement} containerElement - O elemento que contém o canvas e os botões.
     */
    constructor(containerElement) {
        this.container = containerElement;

        // Procura o canvas dentro do container, aceitando o novo data-attribute ou o ID antigo
        this.canvas = this.container.querySelector('[data-signature-canvas], #signature-canvas');

        if (!this.canvas) {
            console.error("Elemento canvas não foi encontrado no container fornecido.", this.container);
            return; // Aborta se o canvas não for encontrado
        }

        // Isso permite que outros scripts acessem métodos como o resizeCanvas()
        this.canvas.signaturePadInstance = this;
        // Procura outros elementos de forma flexível
        this.clearButton = this.container.querySelector('[data-signature-clear-button], #clear-signature');
        this.hiddenInput = this.container.querySelector('[data-signature-hidden-input], #assinatura_base64');
        this.form = this.container.closest('form');

        if (!this.form || !this.hiddenInput) {
            console.error("Componente de assinatura não encontrou o formulário pai ou o input hidden.");
            return;
        }

        this.signaturePad = new SignaturePad(this.canvas, {
            backgroundColor: 'rgb(255, 255, 255)'
        });

        this._setupEventListeners();
        
        // Usa um pequeno timeout para garantir que o layout da página está 100% estável antes de calibrar
        setTimeout(() => this.resizeCanvas(), 150);
    }

    _setupEventListeners() {
        window.addEventListener("resize", () => this.resizeCanvas());
        if (this.clearButton) {
            this.clearButton.addEventListener('click', () => this.signaturePad.clear());
        }
        this.form.addEventListener('submit', () => this._handleFormSubmit());
    }

    resizeCanvas() {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        this.canvas.width = this.canvas.offsetWidth * ratio;
        this.canvas.height = this.canvas.offsetHeight * ratio;
        this.canvas.getContext("2d").scale(ratio, ratio);
        this.signaturePad.clear();
    }

    _handleFormSubmit() {
        if (!this.signaturePad.isEmpty()) {
            this.hiddenInput.value = this.signaturePad.toDataURL('image/png');
        }
    }
}

// INICIALIZADOR UNIVERSAL ATUALIZADO
window.addEventListener('load', () => {
    // 1. Prioriza a busca pela nova estrutura (data-attributes)
    const signatureContainers = document.querySelectorAll('[data-signature-pad-container]');
    if (signatureContainers.length > 0) {
        signatureContainers.forEach(container => new SignaturePadComponent(container));
    } else {
        // 2. Se não encontrar, procura pela estrutura antiga (baseada no ID do formulário) como plano B
        const legacyForm = document.getElementById('formAssinatura');
        if (legacyForm) {
            new SignaturePadComponent(legacyForm);
        }
    }
});

