// static/js/signature.js
// Responsabilidade: Componente reutilizável de assinatura digital
// Dependência: SignaturePad (CDN ou vendor/signature_pad.umd.min.js)

class SignaturePadComponent {
    /**
     * Inicializa o componente de assinatura dentro de um container.
     * @param {HTMLElement} containerElement - Elemento com data-signature-pad-container
     */
    constructor(containerElement) {
        this.container = containerElement;

        // Busca o canvas (novo padrão via data-attribute ou fallback por ID)
        this.canvas = this.container.querySelector(
            '[data-signature-canvas], #signature-canvas'
        );

        if (!this.canvas) {
            console.warn('[SignaturePad] Canvas não encontrado no container:', this.container);
            return;
        }

        // Referência reversa para acesso externo
        this.canvas.signaturePadInstance = this;

        // Busca elementos auxiliares
        this.clearButton = this.container.querySelector(
            '[data-signature-clear-button], #clear-signature'
        );
        this.hiddenInput = this.container.querySelector(
            '[data-signature-hidden-input], #assinatura_base64'
        );
        this.form = this.container.closest('form');

        if (!this.form) {
            console.warn('[SignaturePad] Formulário pai não encontrado.');
            return;
        }

        if (!this.hiddenInput) {
            console.warn('[SignaturePad] Input hidden para base64 não encontrado.');
            return;
        }

        // Inicializa a lib SignaturePad
        this.signaturePad = new SignaturePad(this.canvas, {
            backgroundColor: 'rgb(255, 255, 255)',
            penColor: 'rgb(0, 0, 0)',
        });

        this._setupEventListeners();

        // Delay para garantir que o layout está estável
        setTimeout(() => this.resizeCanvas(), 150);
    }

    /**
     * Configura todos os event listeners.
     */
    _setupEventListeners() {
        // Redimensionar canvas ao mudar tamanho da janela
        window.addEventListener('resize', () => this.resizeCanvas());

        // Botão limpar
        if (this.clearButton) {
            this.clearButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.signaturePad.clear();
            });
        }

        // Ao submeter o form, preenche o input hidden
        this.form.addEventListener('submit', (e) => this._handleFormSubmit(e));

        // Se estiver dentro de um modal, redimensiona ao abrir
        const modal = this.container.closest('.modal');
        if (modal) {
            modal.addEventListener('shown.bs.modal', () => this.resizeCanvas());
        }
    }

    /**
     * Redimensiona o canvas para alta resolução (Retina).
     */
    resizeCanvas() {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        this.canvas.width = this.canvas.offsetWidth * ratio;
        this.canvas.height = this.canvas.offsetHeight * ratio;
        this.canvas.getContext('2d').scale(ratio, ratio);
        this.signaturePad.clear();
    }

    /**
     * Ao submeter, converte a assinatura para base64 e coloca no input hidden.
     */
    _handleFormSubmit(event) {
        if (!this.signaturePad.isEmpty()) {
            this.hiddenInput.value = this.signaturePad.toDataURL('image/png');
        }
        // Se a assinatura for obrigatória, validar aqui:
        // else {
        //     event.preventDefault();
        //     alert('Por favor, desenhe uma assinatura.');
        // }
    }

    /**
     * Verifica se o pad está vazio.
     * @returns {boolean}
     */
    isEmpty() {
        return this.signaturePad.isEmpty();
    }

    /**
     * Limpa a assinatura.
     */
    clear() {
        this.signaturePad.clear();
    }

    /**
     * Retorna a assinatura como data URL (base64).
     * @returns {string}
     */
    toDataURL() {
        return this.signaturePad.toDataURL('image/png');
    }
}

// ═══════════════════════════════════════════════════════
// INICIALIZADOR UNIVERSAL
// ═══════════════════════════════════════════════════════
window.addEventListener('load', () => {
    // Busca containers com data-attribute
    const containers = document.querySelectorAll('[data-signature-pad-container]');

    if (containers.length > 0) {
        containers.forEach(container => new SignaturePadComponent(container));
    } else {
        // Fallback: busca pelo formulário legado
        const legacyForm = document.getElementById('formAssinatura');
        if (legacyForm) {
            new SignaturePadComponent(legacyForm);
        }
    }
});

