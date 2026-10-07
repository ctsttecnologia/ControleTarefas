
/* chat-loader.js v3 — carrega chat.js com retry e inicializa o ChatManager */
(() => {
    if (window.ChatSystemLoader) return; // já carregado

    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

    class ChatSystemLoader {
        constructor(maxAttempts = 3) {
            this.maxAttempts = maxAttempts;
            this.src = '/static/js/chat.js';
        }

        async init(urls, userId) {
            if (window.chatManager) return true; // evita dupla inicialização

            if (!urls || typeof urls !== 'object') {
                console.error('[chat-loader] URLs não fornecidas');
                return false;
            }
            this.src = urls.chat_script_url || this.src;

            let ok = !!window.ChatManager; // chat.js já incluído no template
            for (let i = 1; !ok && i <= this.maxAttempts; i++) {
                ok = !!window.ChatManager || await this.loadScript(i > 1);
                if (!ok && i < this.maxAttempts) await sleep(1000 * i);
            }
            if (!ok) {
                this.showError();
                return false;
            }

            try {
                // o construtor é singleton: se já existir, devolve a instância atual
                window.chatManager = window.chatManager || new window.ChatManager(urls, userId);
            } catch (e) {
                console.error('[chat-loader] erro ao iniciar ChatManager', e);
                this.showError();
                return false;
            }

            document.dispatchEvent(new CustomEvent('chatSystemReady', {
                detail: { chatManager: window.chatManager },
            }));
            return true;
        }

        /** Injeta <script>. Só adiciona cache-bust nas tentativas de retry. */
        loadScript(bust = false) {
            return new Promise((resolve) => {
                const s = document.createElement('script');
                s.src = bust
                    ? `${this.src}${this.src.includes('?') ? '&' : '?'}r=${Date.now()}`
                    : this.src;
                s.async = true;

                let done = false;
                const finish = (val) => {
                    if (done) return;
                    done = true;
                    clearTimeout(timer);
                    if (!val) s.remove();
                    resolve(val);
                };
                const timer = setTimeout(() => finish(false), 10000);

                s.onload = () => finish(!!window.ChatManager);
                s.onerror = () => finish(false);
                document.head.appendChild(s);
            });
        }

        showError() {
            const render = () => {
                if (document.getElementById('chat-critical-error')) return;
                const box = document.createElement('div');
                box.id = 'chat-critical-error';
                box.style.cssText = 'position:fixed;top:20px;right:20px;z-index:999999;background:#dc3545;'
                    + 'color:#fff;padding:15px;border-radius:8px;font-family:system-ui;max-width:300px';
                box.innerHTML = `<strong>Erro no chat</strong>
                    <p style="margin:8px 0;font-size:13px">Não foi possível carregar o chat. Verifique a conexão.</p>
                    <button data-r style="background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.3);color:#fff;padding:5px 10px;border-radius:4px;cursor:pointer">Recarregar</button>
                    <button data-x style="background:none;border:none;color:#fff;float:right;cursor:pointer;font-size:16px">×</button>`;
                box.querySelector('[data-r]').addEventListener('click', () => location.reload());
                box.querySelector('[data-x]').addEventListener('click', () => box.remove());
                document.body.appendChild(box);
            };
            if (document.body) render();
            else document.addEventListener('DOMContentLoaded', render, { once: true });
        }
    }

    window.ChatSystemLoader = ChatSystemLoader;
    window.initializeChatSystem = (urls, userId) => new ChatSystemLoader().init(urls, userId);
})();
