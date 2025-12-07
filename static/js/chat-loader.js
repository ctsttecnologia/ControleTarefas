
/**
 * Chat Loader Ultra-Resiliente v2.0
 * Resolve ERR_HTTP2_PROTOCOL_ERROR e ChatManager não carregada
 */
if (typeof ChatSystemLoader === 'undefined') {
    class ChatSystemLoader {
        constructor() {
            this.loadAttempts = 0;
            this.maxAttempts = 3;
            this.chatUrls = null;
            this.currentUserId = null;
        }

        async init(urls, userId) {
            this.chatUrls = urls;
            this.currentUserId = userId;
            
            console.log('🚀 Iniciando Chat Loader Resiliente...');
            
            // Tentar carregamento principal
            const success = await this.tryLoadChatSystem();
            
            if (success) {
                console.log('✅ Chat carregado com sucesso!');
                this.setupGlobalFallbacks();
                return true;
            }
            
            console.error('💥 Falha total no carregamento do chat');
            this.showCriticalError();
            return false;
        }

        async tryLoadChatSystem() {
            for (let attempt = 1; attempt <= this.maxAttempts; attempt++) {
                console.log(`🔄 Tentativa ${attempt}/${this.maxAttempts}`);
                
                try {
                    // Método 1: Import dinâmico (HTTP/2)
                    if (attempt === 1) {
                        const success = await this.loadViaImport();
                        if (success) return true;
                    }
                    
                    // Método 2: Script tag com cache bypass (HTTP/1.1)
                    if (attempt === 2) {
                        const success = await this.loadViaScript(true);
                        if (success) return true;
                    }
                    
                    // Método 3: Fetch + eval (último recurso)
                    if (attempt === 3) {
                        const success = await this.loadViaFetch();
                        if (success) return true;
                    }
                    
                } catch (error) {
                    console.warn(`❌ Tentativa ${attempt} falhou:`, error);
                    await this.sleep(1000 * attempt); // Delay progressivo
                }
            }
            
            return false;
        }

        async loadViaImport() {
            try {
                console.log('📥 Tentando import dinâmico...');
                
                // Tenta importar como módulo
                const chatModule = await import(`/static/js/chat.js?v=${this.getCacheKey()}`);
                
                // Aguarda um momento para garantir que a classe foi registrada
                await this.sleep(100);
                
                if (typeof window.ChatManager !== 'undefined') {
                    this.initializeChatManager();
                    return true;
                }
                
                throw new Error('ChatManager não encontrado após import');
                
            } catch (error) {
                console.warn('Import dinâmico falhou:', error);
                return false;
            }
        }

        async loadViaScript(bypassCache = false) {
            return new Promise((resolve) => {
                console.log('📜 Tentando script tag...');
                
                const script = document.createElement('script');
                script.src = `/static/js/chat.js?v=${bypassCache ? Date.now() : this.getCacheKey()}`;
                script.type = 'text/javascript';
                script.async = true;
                
                let resolved = false;
                
                const checkSuccess = () => {
                    if (resolved) return;
                    
                    if (typeof window.ChatManager !== 'undefined') {
                        resolved = true;
                        this.initializeChatManager();
                        resolve(true);
                    } else {
                        resolved = true;
                        resolve(false);
                    }
                };
                
                script.onload = () => {
                    setTimeout(checkSuccess, 200); // Aguarda processamento
                };
                
                script.onerror = () => {
                    resolved = true;
                    resolve(false);
                };
                
                // Timeout de segurança
                setTimeout(() => {
                    if (!resolved) {
                        resolved = true;
                        resolve(false);
                    }
                }, 8000);
                
                document.head.appendChild(script);
            });
        }

        async loadViaFetch() {
            try {
                console.log('🌐 Tentando fetch + eval...');
                
                const response = await fetch(`/static/js/chat.js?bypass=${Date.now()}`, {
                    headers: {
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const code = await response.text();
                
                // Executa o código de forma segura
                eval(code);
                
                await this.sleep(100);
                
                if (typeof window.ChatManager !== 'undefined') {
                    this.initializeChatManager();
                    return true;
                }
                
                throw new Error('ChatManager não inicializada após eval');
                
            } catch (error) {
                console.warn('Fetch falhou:', error);
                return false;
            }
        }

        initializeChatManager() {
            try {
                console.log('🎯 Inicializando ChatManager...');
                window.chatManager = new window.ChatManager(this.chatUrls, this.currentUserId);
                
                // Dispatch evento para outros scripts
                document.dispatchEvent(new CustomEvent('chatSystemReady', {
                    detail: { chatManager: window.chatManager }
                }));
                
            } catch (error) {
                console.error('Erro na inicialização:', error);
                throw error;
            }
        }

        setupGlobalFallbacks() {
            // Garante que as funções globais funcionem mesmo se houver erros
            if (!window.toggleChatListSidebar) {
                window.toggleChatListSidebar = () => {
                    const sidebar = document.getElementById('chatListContainer');
                    const overlay = document.getElementById('chatOverlay');
                    
                    if (sidebar && overlay) {
                        sidebar.classList.toggle('active');
                        overlay.classList.toggle('active');
                    }
                };
            }
            
            if (!window.openChatDialog) {
                window.openChatDialog = (roomId, roomName) => {
                    if (window.chatManager && window.chatManager.openChatDialog) {
                        window.chatManager.openChatDialog(roomId, roomName);
                    } else {
                        console.warn('Chat ainda não está pronto');
                    }
                };
            }
        }

        showCriticalError() {
            const errorHtml = `
                <div id="chat-critical-error" style="position: fixed; top: 20px; right: 20px; z-index: 999999; background: #dc3545; color: white; padding: 15px; border-radius: 8px; font-family: system-ui; max-width: 300px;">
                    <strong>❌ Erro no Sistema de Chat</strong>
                    <p style="margin: 8px 0; font-size: 13px;">Não foi possível carregar o chat. Possível problema de rede ou servidor.</p>
                    <button onclick="location.reload()" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                        🔄 Recarregar Página
                    </button>
                    <button onclick="document.getElementById('chat-critical-error').remove()" style="background: none; border: none; color: white; float: right; cursor: pointer; font-size: 16px;">×</button>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', errorHtml);
        }

        getCacheKey() {
            // Use versão do seu sistema + timestamp para forçar reload quando necessário
            return `2.0.0.${Date.now()}`;
        }

        sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    }

    // Função global de inicialização
    window.initializeChatSystem = function(chatUrls, currentUserId) {
        const loader = new ChatSystemLoader();
        return loader.init(chatUrls, currentUserId);
    };
    console.log('ChatLoader version:', '3.1.0', 'loaded at:', new Date().toISOString());
        if (window.ChatSystemLoader) {
            console.warn('ChatSystemLoader já foi definido anteriormente');
        }

    // Auto-export
    window.ChatSystemLoader = ChatSystemLoader;
}

