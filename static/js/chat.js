
/**
 * Sistema de Chat Avançado v4.3 - Compatível com template Django
 * Com funcionalidades completas: troca de conversas, envio de arquivos, busca global
 */

class ChatManager {
    constructor(urls, currentUserId) {
        console.log('🚀 ChatManager v4.3 - Inicializando para template Django...');

        // Configuração de debug
        this.debugMode = localStorage.getItem('chat-debug-mode') === 'true';
        
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5; // LIMITE DE 5 TENTATIVAS

        // Método helper para logs condicionais
        this.log = {
            info: (...args) => console.log('ℹ️', ...args),
            warn: (...args) => console.warn('⚠️', ...args),
            error: (...args) => console.error('❌', ...args),
            debug: (...args) => this.debugMode && console.debug('🔍', ...args),
            success: (...args) => console.log('✅', ...args)
        };

        // Validação inicial
        if (!urls || typeof urls !== 'object') {
            return this.handleCriticalError('URLs não fornecidas');
        }
        
        // Configuração única de URLs baseada no template
        this.urls = {
            active_room_list: urls.active_room_list || '/chat/api/rooms/',
            user_list: urls.user_list || '/chat/api/users/',
            task_list: urls.task_list || '/chat/api/tasks/',
            start_dm_base: urls.start_dm_base || '/chat/api/start-dm/0/',
            create_group_url: urls.create_group_url || '/chat/api/create-group/',
            get_task_chat_base: urls.get_task_chat_base || '/chat/api/task/0/',
            upload_file_url: urls.upload_file_url || '/chat/api/upload/',
            search_messages_url: urls.search_messages_url || '/chat/api/search/',
            ws_base: urls.ws_base || '/ws/chat/',
            history_base: urls.history_base || '/chat/api/history/',
            ...urls
        };

        // Validação de URLs obrigatórias
        const requiredUrls = ['active_room_list', 'user_list', 'start_dm_base', 'create_group_url'];
        const missingUrls = requiredUrls.filter(url => !this.urls[url]);
        
        if (missingUrls.length > 0) {
            const errorMsg = `URLs obrigatórias faltando: ${missingUrls.join(', ')}`;
            this.log.error(errorMsg);
            return this.handleCriticalError(errorMsg);
        }

        // Core state
        this.currentUserId = currentUserId;
        this.currentRoom = null;
        this.currentRoomName = null;
        this.websocket = null;
        this.isConnected = false;
        
        // UI state
        this.isMinimized = false;
        
        // Sistema de som e Cache
        this.soundEnabled = localStorage.getItem('chat-sound-enabled') !== 'false';
        this.soundInitialized = false;
        this.audioContext = null;
        this.audioElements = {};
        this.cache = { users: [], tasks: [], rooms: [], messages: {}, searchResults: {} };
        
        // Outros states
        this.uploadQueue = [];
        this.isUploading = false;
        this.maxFileSize = 10 * 1024 * 1024;
        this.currentSearchQuery = '';
        this.searchResults = [];
        this.dragData = { isDragging: false, offsetX: 0, offsetY: 0 };

        // Inicia os processos DEPOIS de tudo configurado.
        this.initialize(); 
        this.connectNotificationSocket(); // ADICIONE A ÚNICA CHAMADA AQUI!
    }

    // ==================== INICIALIZAÇÃO ====================
    
    async initialize() {
        try {
            await this.waitForDOM();
            
            // Verifica elementos críticos do template
            const criticalElements = ['chat-draggable-container', 'chat-log', 'chat-message-input'];
            const missingElements = criticalElements.filter(id => !document.getElementById(id));
            
            if (missingElements.length > 0) {
                this.log.warn(`Elementos críticos faltando: ${missingElements.join(', ')}`);
                // Não injetamos dinamicamente pois o template já existe
            }
            
            // Configura elementos específicos do template
            this.configureTemplateElements();
            
            await this.setupComponents();
            this.log.success('Chat inicializado com sucesso');
            
            // Dispara evento de inicialização completa
            this.dispatchEvent('chatSystemFullyReady', { loadTime: Date.now() });
            
        } catch (error) {
            this.log.error('Erro na inicialização:', error);
            this.handleCriticalError('Falha na inicialização');
        }
    }

    configureTemplateElements() {
        console.log("Iniciando configureTemplateElements...");

            // Configura botão flutuante
            const floatingBtn = document.getElementById('chat-modal-trigger');

            // 1. Verificamos se o botão foi encontrado no DOM
            console.log("Elemento do botão encontrado:", floatingBtn);

            if (floatingBtn) {
                // 2. Verificamos se a função existe no 'this' atual
                console.log("Função toggleChatListSidebar disponível em 'this':", this.toggleChatListSidebar);

                floatingBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    console.log("Botão flutuante clicado!");

                    // 3. Verificamos se a função ainda está acessível no momento do clique
                    if (typeof this.toggleChatListSidebar === 'function') {
                        this.toggleChatListSidebar();
                    } else {
                        console.error("ERRO: 'this.toggleChatListSidebar' não é uma função no momento do clique.", "Contexto 'this':", this);
                    }
                });
                console.log("Listener de clique adicionado com sucesso!");
            } else {
                console.error("ERRO: Botão com id 'chat-modal-trigger' não foi encontrado no DOM. Verifique se o script está sendo carregado após o HTML.");
            }
        

        
        // Configura overlay
        const overlay = document.getElementById('chatOverlay');
        if (overlay) {
            overlay.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleChatListSidebar();
            });
        }
        
        // Configura botão de fechar sidebar
        // DIAGNÓSTICO: Verificando o botão de fechar
        const closeBtn = document.querySelector('.chat-close-btn');
        if (closeBtn) {
            this.log.info('Botão de fechar (.chat-close-btn) encontrado. Adicionando listener de clique...');
            closeBtn.addEventListener('click', (e) => {
                this.log.info('--- CLIQUE NO BOTÃO DE FECHAR DETECTADO! ---');
                e.preventDefault();
                this.toggleChatListSidebar();
            });
        } else {
            this.log.error('CRÍTICO: Botão de fechar (.chat-close-btn) NÃO foi encontrado no DOM.');
        }
        
        // Configura botão de nova conversa no modal
        const novaConversaBtn = document.getElementById('iniciar-nova-conversa');
        if (novaConversaBtn) {
            novaConversaBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const modal = new bootstrap.Modal(document.getElementById('novaConversaModal'));
                modal.show();
            });
        }
        
        // Configura busca global
        this.configureGlobalSearch();
        
        this.log.success('Elementos do template configurados');
    }

   configureGlobalSearch() {
        const globalSearchBtn = document.getElementById('global-search-btn');
        const globalSearchContainer = document.getElementById('global-search-container');
        const globalSearchInput = document.getElementById('global-search-input');

        // Restaura o evento de clique no ícone de lupa para mostrar/esconder a busca.
        if (globalSearchBtn && globalSearchContainer) {
            globalSearchBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const isVisible = globalSearchContainer.style.display !== 'none';
                globalSearchContainer.style.display = isVisible ? 'none' : 'block';
                
                // Foca no campo de busca quando ele se torna visível.
                if (!isVisible && globalSearchInput) {
                    setTimeout(() => globalSearchInput.focus(), 100);
                }
            });
        }
        
        // Mantém a busca em tempo real no campo de input.
        if (globalSearchInput) {
            globalSearchInput.addEventListener('input', () => {
                const query = globalSearchInput.value;
                this.performGlobalSearch(query);
            });
        }
    }

    performGlobalSearch(query) {
        this.log.debug(`Filtrando conversas locais com: "${query}"`);

        // Garante que o cache de salas existe.
        if (!this.cache.rooms) {
            this.log.warn('Cache de salas vazio, não é possível filtrar.');
            return;
        }

        const lowerCaseQuery = query.toLowerCase().trim();
        const container = document.getElementById('active-chats-list');

        // Se a busca estiver vazia, mostra todas as conversas originais.
        if (!lowerCaseQuery) {
            this.renderRoomList(this.cache.rooms);
            // Se o container estiver vazio após renderizar, mostra o estado de "nenhuma conversa".
            if (container && this.cache.rooms.length === 0) {
                 this.renderEmptyState(container, 'chat-dots', 'Nenhuma conversa ativa', 'Clique em "Nova Conversa" para começar');
            }
            return;
        }

        // Filtra a lista de conversas em cache com base no nome da sala.
        const filteredRooms = this.cache.rooms.filter(room =>
            room.room_name.toLowerCase().includes(lowerCaseQuery)
        );

        // Se houver resultados, renderiza a lista filtrada.
        if (filteredRooms.length > 0) {
            this.renderRoomList(filteredRooms);
        } else {
            // Se não houver resultados, mostra uma mensagem.
            if (container) {
                container.innerHTML = `
                    <div class="text-center p-3 text-muted">
                        <i class="bi bi-search"></i>
                        <p class="mb-0">Nenhum resultado para "${query}"</p>
                    </div>
                `;
            }
        }
    }

    displayGlobalSearchResults(results, query, container) {
        container.innerHTML = `
            <div class="search-results-header p-2 border-bottom">
                <small class="text-muted">${results.length} resultado(s) encontrado(s)</small>
            </div>
            ${results.map(result => `
                <div class="search-result-item p-3 border-bottom" 
                     onclick="chatManager.openChatDialog('${result.room_id}', '${this.escapeHtml(result.room_name)}'); 
                              chatManager.highlightMessage('${result.message_id}')">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <strong class="d-block">${this.escapeHtml(result.room_name)}</strong>
                            <small class="text-muted">${this.escapeHtml(result.username)}</small>
                        </div>
                        <small class="text-muted">${new Date(result.timestamp).toLocaleString('pt-BR')}</small>
                    </div>
                    <div class="search-result-text">
                        ${this.highlightQuery(this.escapeHtml(result.message || '📎 Arquivo'), query)}
                    </div>
                </div>
            `).join('')}
        `;
    }

    highlightQuery(text, query) {
        if (!query || !text) return text;
        const regex = new RegExp(`(${this.escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    async setupComponents() {
        const tasks = [
            this.initializeDrag(),
            this.setupEventListeners(),
            this.loadInitialData(),
            this.initializeModals(),
            this.initializePreview(),
            this.initializeChatSearch(),
            this.initializeDynamicContent(),
            this.initializeFileUpload(),
            this.initializeSoundSystem()
        ];
        
        await Promise.allSettled(tasks);
    }

    // ==================== TROCA DE CONVERSA ====================
    
    async openChatDialog(roomId, roomName) {
        try {
            this.log.info(`Abrindo conversa: ${roomName} (${roomId})`);
            
            // Fecha WebSocket anterior se existir
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
                this.isConnected = false;
            }
            
            // Fecha sidebar se estiver aberto
            this.toggleChatListSidebar(false);
            
            const container = document.getElementById('chat-draggable-container');
            const title = document.getElementById('chat-dialog-header-title');
            const content = document.getElementById('chat-dialog-content');
            
            if (!container || !title || !content) {
                throw new Error('Elementos do chat não encontrados');
            }

            // Atualiza estado atual
            this.currentRoom = roomId;
            this.currentRoomName = roomName;
            
            // Mostra container
            container.style.display = 'flex';
            container.classList.remove('minimized');
            
            // Atualiza título
            title.textContent = roomName || 'Chat';
            
            // Atualiza status no header
            this.updateConnectionStatus('connecting');
            
            // Limpa e exibe estado de carregamento
            const chatLog = document.getElementById('chat-log');
            if (chatLog) {
                chatLog.innerHTML = `
                    <div class="loading-state text-center p-4">
                        <div class="spinner-border spinner-border-sm" role="status"></div>
                        <p class="mt-2 mb-0">Carregando mensagens...</p>
                    </div>
                `;
            }
            
            // Carrega histórico e conecta WebSocket em paralelo
            await Promise.allSettled([
                this.loadChatHistory(roomId),
                this.connectWebSocket(roomId)
            ]);
            
            // Atualiza lista de conversas (marca como lida)
            this.markRoomAsRead(roomId);
            
            this.log.success(`Conversa aberta: ${roomName}`);
            
        } catch (error) {
            this.log.error('Erro ao abrir conversa:', error);
            this.showNotification('Falha ao abrir conversa', 'error');
            
            // Mostra estado de erro
            const chatLog = document.getElementById('chat-log');
            if (chatLog) {
                chatLog.innerHTML = `
                    <div class="error-state">
                        <i class="bi bi-exclamation-triangle"></i>
                        <p>Erro ao carregar conversa</p>
                        <button class="btn btn-sm btn-outline-danger mt-2" onclick="chatManager.openChatDialog('${roomId}', '${roomName}')">
                            Tentar Novamente
                        </button>
                    </div>
                `;
            }
        }
    }

    async loadChatHistory(roomId) {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return;

        try {
            this.log.info(`📜 Carregando histórico da sala ${roomId}...`);
            
            // Monta a URL correta
            const historyUrl = this.urls.get_chat_history 
                ? this.urls.get_chat_history.replace('00000000-0000-0000-0000-000000000000', roomId)
                : `/chat/api/history/${roomId}/`;
            
            console.log('🔗 URL do histórico:', historyUrl);
            
            const response = await fetch(historyUrl);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📦 Dados recebidos:', data);
            
            if (data.status === 'success') {
                if (data.messages && data.messages.length > 0) {
                    // Cache as mensagens
                    this.cache.messages[roomId] = data.messages;
                    
                    // Renderiza as mensagens
                    this.renderMessages(data.messages);
                    
                    this.log.success(`✅ ${data.messages.length} mensagens carregadas`);
                } else {
                    this.log.info('📭 Nenhuma mensagem encontrada');
                    this.renderEmptyChatState();
                }
            } else {
                throw new Error(data.error || 'Erro desconhecido');
            }
            
        } catch (error) {
            this.log.error('❌ Erro ao carregar histórico:', error);
            this.renderErrorChatState(error.message);
        }
    }
    renderMessages(messages) {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return;
        
        console.log(`🖼️ Renderizando ${messages.length} mensagens...`);
        
        // Limpa o chat
        chatLog.innerHTML = '';
        
        if (messages.length === 0) {
            this.renderEmptyChatState();
            return;
        }
        
        // Renderiza cada mensagem
        messages.forEach((message, index) => {
            const messageElement = this.createMessageElement(message);
            chatLog.appendChild(messageElement);
        });
        
        // Rola para a última mensagem
        this.scrollToBottom();
        
        console.log('✅ Mensagens renderizadas com sucesso');
    }

    groupMessagesByDate(messages) {
        const groups = {};
        
        messages.forEach(message => {
            const date = new Date(message.timestamp).toDateString();
            if (!groups[date]) {
                groups[date] = [];
            }
            groups[date].push(message);
        });
        
        return groups;
    }

    formatDateHeader(dateString) {
        const date = new Date(dateString);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        if (date.toDateString() === today.toDateString()) {
            return 'Hoje';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Ontem';
        } else {
            return date.toLocaleDateString('pt-BR', {
                weekday: 'long',
                day: 'numeric',
                month: 'long'
            });
        }
    }

    createMessageElement(data) {
        const messageDiv = document.createElement('div');
        const isOwn = data.user_id == this.currentUserId;
        
        messageDiv.className = `message ${isOwn ? 'own-message' : 'other-message'}`;
        messageDiv.dataset.messageId = data.id || data.message_id;
        
        // ✅ CORREÇÃO: Trata timestamp inválido
        let timestamp = 'Agora';
        if (data.timestamp) {
            const date = new Date(data.timestamp);
            if (!isNaN(date.getTime())) {
                timestamp = date.toLocaleTimeString('pt-BR', {
                    hour: '2-digit', 
                    minute: '2-digit'
                });
            }
        }
        
        // Garante que username nunca seja vazio
        const username = data.username || 'Usuário';
        
        // Conteúdo da mensagem (texto ou arquivo)
        let contentHtml = '';
        
        if (data.message_type === 'file' && data.file_data) {
            contentHtml = this.renderFileContent(data);
        } else if (data.message_type === 'image' && data.image_url) {
            contentHtml = `
                <div class="message-image">
                    <img src="${data.image_url}" alt="Imagem" class="img-fluid rounded" 
                        style="max-width: 200px; cursor: pointer;"
                        onclick="chatManager.viewImage('${data.image_url}')">
                </div>
            `;
        } else {
            // Mensagem de texto
            const messageText = data.message || data.content || '';
            contentHtml = `<div class="message-text">${this.formatMessageText(messageText)}</div>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">${this.escapeHtml(username)}</span>
                    <span class="message-time">${timestamp}</span>
                </div>
                ${contentHtml}
                ${data.is_edited ? '<small class="text-muted ms-2"><i class="bi bi-pencil"></i> editado</small>' : ''}
            </div>
        `;
        
        return messageDiv;
    }


    renderFileContent(data) {
        try {
            const fileData = typeof data.file_data === 'string' 
                ? JSON.parse(data.file_data) 
                : data.file_data;
                
            const fileName = fileData.name || 'arquivo';
            const fileSize = fileData.size ? this.formatFileSize(fileData.size) : '';
            const fileType = fileData.type || '';
            const fileUrl = fileData.url || '';
            
            let icon = 'bi-file-earmark';
            if (fileType.includes('image')) icon = 'bi-file-image';
            else if (fileType.includes('pdf')) icon = 'bi-file-pdf';
            else if (fileType.includes('word') || fileType.includes('document')) icon = 'bi-file-word';
            else if (fileType.includes('excel') || fileType.includes('sheet')) icon = 'bi-file-excel';
            else if (fileType.includes('video')) icon = 'bi-file-play';
            else if (fileType.includes('audio')) icon = 'bi-file-music';
            else if (fileType.includes('zip') || fileType.includes('compressed')) icon = 'bi-file-zip';
            
            // Se for imagem, mostra preview
            if (fileType.includes('image') && fileUrl) {
                return `
                    <div class="message-file">
                        <div class="file-icon"><i class="bi ${icon}"></i></div>
                        <div class="file-info">
                            <div class="file-name">${this.escapeHtml(fileName)}</div>
                            ${fileSize ? `<div class="file-size">${fileSize}</div>` : ''}
                        </div>
                    </div>
                    <div class="image-preview mt-2">
                        <img src="${fileUrl}" alt="${fileName}" class="img-fluid rounded" 
                            style="max-width: 200px; cursor: pointer;"
                            onclick="chatManager.viewImage('${fileUrl}')">
                    </div>
                `;
            }
            
            return `
                <div class="message-file" style="cursor: pointer;" 
                    onclick="chatManager.downloadFile('${fileUrl}', '${this.escapeHtml(fileName)}')">
                    <div class="file-icon"><i class="bi ${icon}"></i></div>
                    <div class="file-info">
                        <div class="file-name">${this.escapeHtml(fileName)}</div>
                        ${fileSize ? `<div class="file-size">${fileSize}</div>` : ''}
                    </div>
                    <button class="btn btn-sm btn-outline-primary ms-2">
                        <i class="bi bi-download"></i>
                    </button>
                </div>
            `;
        } catch (error) {
            console.error('Erro ao renderizar arquivo:', error);
            return `<div class="message-text">📎 Arquivo anexado</div>`;
        }
    }

    renderTextMessage(data) {
        return `<div class="message-text">${this.formatMessageText(data.message)}</div>`;
    }

    renderFileMessage(data) {
        try {
            const fileData = data.file_data ? JSON.parse(data.file_data) : {};
            const fileName = fileData.name || 'arquivo';
            const fileSize = fileData.size ? this.formatFileSize(fileData.size) : '';
            const fileType = fileData.type || '';
            
            let icon = 'bi-file-earmark';
            if (fileType.includes('image')) icon = 'bi-file-image';
            else if (fileType.includes('pdf')) icon = 'bi-file-pdf';
            else if (fileType.includes('word') || fileType.includes('document')) icon = 'bi-file-word';
            else if (fileType.includes('excel') || fileType.includes('sheet')) icon = 'bi-file-excel';
            else if (fileType.includes('video')) icon = 'bi-file-play';
            else if (fileType.includes('audio')) icon = 'bi-file-music';
            else if (fileType.includes('zip') || fileType.includes('compressed')) icon = 'bi-file-zip';
            
            const url = fileData.url || '';
            const isImage = fileType.includes('image');
            
            if (isImage && url) {
                return `
                    <div class="message-image-container">
                        <div class="message-file">
                            <div class="file-icon">
                                <i class="bi ${icon}"></i>
                            </div>
                            <div class="file-info">
                                <div class="file-name">${this.escapeHtml(fileName)}</div>
                                ${fileSize ? `<div class="file-size">${fileSize}</div>` : ''}
                            </div>
                            <button class="btn btn-sm btn-outline-primary" onclick="chatManager.downloadFile('${url}', '${fileName}')">
                                <i class="bi bi-download"></i>
                            </button>
                        </div>
                        <div class="image-preview mt-2">
                            <img src="${url}" alt="${fileName}" class="img-fluid rounded" 
                                 onclick="chatManager.viewImage('${url}')" 
                                 style="max-width: 200px; cursor: pointer;">
                        </div>
                    </div>
                `;
            }
            
            return `
                <div class="message-file" onclick="chatManager.downloadFile('${url}', '${fileName}')">
                    <div class="file-icon">
                        <i class="bi ${icon}"></i>
                    </div>
                    <div class="file-info">
                        <div class="file-name">${this.escapeHtml(fileName)}</div>
                        ${fileSize ? `<div class="file-size">${fileSize}</div>` : ''}
                    </div>
                    <button class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-download"></i>
                    </button>
                </div>
            `;
        } catch (error) {
            return `<div class="message-text">📎 Arquivo anexado</div>`;
        }
    }

    formatMessageText(text) {
        if (!text) return '';
        
        // Substitui URLs por links
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        text = text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener" class="message-link">$1</a>');
        
        // Substitui quebras de linha
        text = text.replace(/\n/g, '<br>');
        
        // Destaca menções
        const mentionRegex = /@(\w+)/g;
        text = text.replace(mentionRegex, '<span class="mention">@$1</span>');
        
        return text;
    }

    formatFileSize(bytes) {
        if (!bytes) return '';
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    scrollToBottom() {
        const chatLog = document.getElementById('chat-log');
        if (chatLog) {
            setTimeout(() => {
                chatLog.scrollTop = chatLog.scrollHeight;
            }, 100);
        }
    }

    renderEmptyChatState() {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return;
        
        chatLog.innerHTML = `
            <div class="welcome-state">
                <i class="bi bi-chat-heart" style="font-size: 3rem; color: var(--text-muted); margin-bottom: 1rem;"></i>
                <p>Nenhuma mensagem ainda</p>
                <small>Seja o primeiro a enviar uma mensagem!</small>
            </div>
        `;
    }

    renderErrorChatState(error) {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return;
        
        chatLog.innerHTML = `
            <div class="error-state">
                <i class="bi bi-exclamation-triangle"></i>
                <p>Erro ao carregar mensagens</p>
                <small>${this.escapeHtml(error)}</small>
                <button class="btn btn-sm btn-outline-danger mt-2" onclick="chatManager.loadChatHistory('${this.currentRoom}')">
                    Tentar Novamente
                </button>
            </div>
        `;
    }

    markRoomAsRead(roomId) {
        // Atualiza na lista de conversas
        const roomElements = document.querySelectorAll('.chat-list-item');
        roomElements.forEach(element => {
            if (element.getAttribute('data-room-id') === roomId || 
                element.getAttribute('onclick')?.includes(roomId)) {
                element.classList.remove('has-unread');
                const unreadBadge = element.querySelector('.chat-list-unread');
                if (unreadBadge) {
                    unreadBadge.remove();
                }
            }
        });
    }

    // ==================== EVENT LISTENERS ====================
    
    setupEventListeners() {
        // Chat controls
        this.bindElement('chat-message-submit', 'click', () => this.sendMessage());
        this.bindElement('chat-message-input', 'keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-expand textarea
        this.bindElement('chat-message-input', 'input', (e) => {
            this.autoExpandTextarea(e.target);
        });
        
        // Window controls
        this.bindElement('minimize-chat-btn', 'click', (e) => {
            e.stopPropagation();
            this.toggleMinimize();
        });
        this.bindElement('maximize-chat-btn', 'click', (e) => {
            e.stopPropagation();
            this.toggleMinimize();
        });
        this.bindElement('close-dialog-btn', 'click', (e) => {
            e.stopPropagation();
            this.closeChat();
        });
        
        // Controles de sidebar
        this.bindElement('chat-list-btn', 'click', () => this.toggleChatListSidebar());
        
        // Busca
        this.bindElement('toggle-chat-search-btn', 'click', () => this.toggleChatSearch());
        this.bindElement('close-chat-search-btn', 'click', () => this.closeChatSearch());
        
        // Informações
        this.bindElement('chat-info-btn', 'click', () => this.showChatInfo());
        
        // Som
        this.bindElement('chat-sound-toggle', 'click', () => this.toggleSound());
        
        // Anexar arquivo (usando o input do template)
        this.bindElement('attach-image-btn', 'click', () => this.handleFileUpload());
        
        this.log.info('Event listeners configurados');
    }

    autoExpandTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    // ==================== ENVIO DE ARQUIVOS ====================
    
    initializeFileUpload() {
        // Usa o input file já existente no template
        this.fileInput = document.getElementById('image-upload-input');
        
        if (!this.fileInput) {
            this.log.warn('Input de upload não encontrado no template');
            return;
        }
        
        // Configura o input file
        this.fileInput.accept = 'image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.zip,.rar';
        this.fileInput.multiple = true;
        
        // Event listener para seleção de arquivos
        this.fileInput.addEventListener('change', (e) => {
            this.handleFileSelection(e.target.files);
            e.target.value = ''; // Reset para permitir selecionar o mesmo arquivo novamente
        });
        
        this.log.success('Sistema de upload configurado');
    }

    handleFileUpload() {
        // Abre o seletor de arquivos
        if (this.fileInput) {
            this.fileInput.click();
        }
    }

    async handleFileSelection(files) {
        if (!files || files.length === 0) return;
        
        const validFiles = Array.from(files).filter(file => {
            if (file.size > this.maxFileSize) {
                this.showNotification(`Arquivo ${file.name} excede 10MB`, 'warning');
                return false;
            }
            return true;
        });
        
        if (validFiles.length === 0) return;
        
        // Adiciona à fila de upload
        this.uploadQueue.push(...validFiles);
        
        // Mostra notificação
        this.showNotification(`${validFiles.length} arquivo(s) preparado(s) para envio`, 'info');
        
        // Inicia upload se não estiver em andamento
        if (!this.isUploading) {
            this.processUploadQueue();
        }
    }

    async processUploadQueue() {
        if (this.uploadQueue.length === 0) {
            this.isUploading = false;
            return;
        }
        
        this.isUploading = true;
        const file = this.uploadQueue.shift();
        
        try {
            await this.uploadFile(file);
        } catch (error) {
            this.log.error('Erro no upload:', error);
            this.showNotification(`Falha ao enviar ${file.name}`, 'error');
        }
        
        // Processa próximo arquivo
        setTimeout(() => this.processUploadQueue(), 500);
    }

    async uploadFile(file) {
        if (!this.currentRoom) {
            throw new Error('Nenhuma conversa selecionada');
        }
        
        if (!this.urls.upload_file_url) {
            throw new Error('URL de upload não configurada');
        }
        
        // Cria FormData
        const formData = new FormData();
        formData.append('file', file);
        formData.append('room_id', this.currentRoom);
        formData.append('message_type', 'file');
        
        // Mostra indicador de upload
        this.showUploadIndicator(file.name);
        
        try {
            // Envia via AJAX
            const response = await fetch(this.urls.upload_file_url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log('📤 Resposta do upload:', data);
            
            if (data.status === 'success' && data.file_data) {
                // Envia via WebSocket para broadcast
                await this.sendFileMessage(data.file_data);
                this.showNotification(`Arquivo ${file.name} enviado`, 'success');
            } else {
                throw new Error(data.error || 'Erro no upload');
            }
            
        } finally {
            // Remove indicador de upload
            this.hideUploadIndicator(file.name);
        }
    }

    // Adicione após o método uploadFile
    async sendFileMessage(fileData) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            this.log.error('WebSocket não conectado para enviar arquivo');
            return;
        }
        
        const message = {
            type: 'file_message',  // Tipo específico para arquivo
            file_data: fileData,
            room_id: this.currentRoom,
            timestamp: new Date().toISOString()
        };
        
        console.log('📤 Enviando arquivo via WebSocket:', message);
        this.websocket.send(JSON.stringify(message));
    }

    showUploadIndicator(fileName) {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return;
        
        const uploadDiv = document.createElement('div');
        uploadDiv.id = `upload-${fileName.replace(/\s+/g, '-')}`;
        uploadDiv.className = 'message own-message uploading';
        uploadDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">Você</span>
                    <span class="message-time">Enviando...</span>
                </div>
                <div class="message-file">
                    <div class="file-icon">
                        <i class="bi bi-cloud-upload"></i>
                    </div>
                    <div class="file-info">
                        <div class="file-name">${this.escapeHtml(fileName)}</div>
                        <div class="upload-progress">
                            <div class="progress" style="height: 4px;">
                                <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        chatLog.appendChild(uploadDiv);
        this.scrollToBottom();
    }

    hideUploadIndicator(fileName) {
        const uploadDiv = document.getElementById(`upload-${fileName.replace(/\s+/g, '-')}`);
        if (uploadDiv) {
            uploadDiv.remove();
        }
    }

    addMessageToCache(message) {
        if (!this.cache.messages[this.currentRoom]) {
            this.cache.messages[this.currentRoom] = [];
        }
        this.cache.messages[this.currentRoom].push(message);
    }

    async downloadFile(url, fileName) {
        if (!url) {
            this.showNotification('Arquivo não disponível para download', 'warning');
            return;
        }
        
        try {
            // Usa o método fetch para baixar o arquivo
            const response = await fetch(url);
            const blob = await response.blob();
            
            // Cria link de download
            const downloadUrl = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = fileName;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Limpa o URL
            window.URL.revokeObjectURL(downloadUrl);
            
        } catch (error) {
            this.log.error('Erro ao baixar arquivo:', error);
            this.showNotification('Falha ao baixar arquivo', 'error');
        }
    }

    viewImage(url) {
        // Remove modal anterior se existir
        const existingModal = document.getElementById('imageViewModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Cria modal para visualização de imagem
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'imageViewModal';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-labelledby', 'imageViewModalLabel');
        modal.setAttribute('aria-hidden', 'true');
        
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="imageViewModalLabel">Visualizar Imagem</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                    </div>
                    <div class="modal-body text-center">
                        <img src="${url}" class="img-fluid" alt="Imagem" style="max-height: 70vh;">
                    </div>
                    <div class="modal-footer">
                        <a href="${url}" download class="btn btn-primary">
                            <i class="bi bi-download"></i> Download
                        </a>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const bsModal = new bootstrap.Modal(modal);
        
        // Remove aria-hidden antes de mostrar
        modal.removeAttribute('aria-hidden');
        
        bsModal.show();
        
        // Limpa o modal quando fechar
        modal.addEventListener('hidden.bs.modal', () => {
            // Remove foco de qualquer elemento antes de remover
            document.activeElement?.blur();
            modal.remove();
        });
        
        // Também limpa se clicar fora
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                bsModal.hide();
            }
        });
    }

    // ==================== WEBSOCKET ====================
    
    connectWebSocket(room_id) {
        // GARANTE QUE A RECONEXÃO NÃO OCORRA COM ID INDEFINIDA
        if (!room_id) {
            this.log.error("Tentativa de conectar WebSocket com room_id indefinido. Abortando.");
            return;
        }

        // Evita múltiplas conexões simultâneas
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.log.warn('WebSocket já conectado. Ignorando nova tentativa.');
            return;
        }

        // Evita spam de reconexões
        if (this.isConnecting) {
            this.log.warn('Conexão já em andamento. Ignorando nova tentativa.');
            return;
        }
        
        this.isConnecting = true;
        
        //const ws_path = `${this.urls.ws_base}${room_id}/`;
        const ws_path = `/ws/chat/${room_id}/`;
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const ws_url = `${protocol}://${window.location.host}${ws_path}`;
        
        this.log.info(`🔄 Conectando WebSocket: ${ws_url} (Tentativa ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
        
        try {
            this.websocket = new WebSocket(ws_url);
            
            this.websocket.onopen = (e) => {
                this.log.success('✅ WebSocket conectado com sucesso!');
                this.isConnected = true;
                this.isConnecting = false;
                this.reconnectAttempts = 0; 
                this.hideConnectionError();
                this.updateConnectionStatus('online');
            };
            
            this.websocket.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    this.log.error('Erro ao processar mensagem WebSocket:', error);
                }
            };
            
            this.websocket.onclose = (e) => {
                this.isConnected = false;
                this.isConnecting = false;
                this.updateConnectionStatus('offline');
                
                this.log.warn(`⚠️ WebSocket desconectado: ${e.code} - ${e.reason || 'Sem razão'}`);

                // **EVITA RECONEXÃO AUTOMÁTICA SE:**
                // 1. Código 1000 = fechamento normal
                // 2. Código 1001 = navegador saindo
                // 3. Máximo de tentativas atingido
                // 4. Sala atual mudou
                if (e.code === 1000 || e.code === 1001) {
                    this.log.info('Conexão fechada normalmente. Não reconectando.');
                    return;
                }

                if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                    this.log.error(`❌ Máximo de ${this.maxReconnectAttempts} tentativas atingido. Parando reconexões.`);
                    this.showConnectionError('Falha de conexão. Clique para tentar novamente.');
                    this.updateConnectionStatus('error');
                    return;
                }

                // Só reconecta se ainda estiver na mesma sala
                if (this.currentRoom !== room_id) {
                    this.log.info('Sala mudou durante desconexão. Cancelando reconexão.');
                    return;
                }

                // **RECONEXÃO CONTROLADA COM BACKOFF**
                this.reconnectAttempts++;
                const delay = Math.min(Math.pow(2, this.reconnectAttempts) * 1000, 30000); // Max 30s
                
                this.log.warn(`🔄 Reagendando reconexão em ${delay / 1000}s... (tentativa ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.showConnectionError(`Reconectando em ${delay / 1000}s...`);
                
                // Cancela timeout anterior se existir
                if (this.reconnectTimeout) {
                    clearTimeout(this.reconnectTimeout);
                }
                
                this.reconnectTimeout = setTimeout(() => {
                    // **DUPLA VERIFICAÇÃO ANTES DE RECONECTAR**
                    if (this.currentRoom === room_id && !this.isConnected && !this.isConnecting) {
                        this.connectWebSocket(room_id);
                    } else {
                        this.log.info('Condições mudaram. Cancelando reconexão programada.');
                    }
                }, delay);
            };
            
            this.websocket.onerror = (e) => {
                this.isConnecting = false;
                this.log.error('❌ Erro WebSocket:', e);
                this.updateConnectionStatus('error');
            };

            // **TIMEOUT DE SEGURANÇA PARA CONEXÃO**
            setTimeout(() => {
                if (this.websocket && this.websocket.readyState === WebSocket.CONNECTING) {
                    this.log.warn('⏰ Timeout na conexão WebSocket');
                    this.websocket.close();
                }
            }, 10000); // 10 segundos

        } catch (error) {
            this.isConnecting = false;
            this.log.error('❌ Erro ao criar WebSocket:', error);
            this.updateConnectionStatus('error');
        }
    }

    // ==================== WEBSOCKET DE NOTIFICAÇÕES ====================

    connectNotificationSocket() {
        // **EVITA MÚLTIPLAS CONEXÕES**
        if (this.notificationSocket && this.notificationSocket.readyState === WebSocket.OPEN) {
            this.log.info('WebSocket de notificações já conectado.');
            return;
        }

        // **EVITA SPAM DE TENTATIVAS**
        if (this.notificationConnecting) {
            this.log.warn('Conexão de notificações já em andamento.');
            return;
        }

        this.notificationConnecting = true;
        this.notificationReconnectAttempts = this.notificationReconnectAttempts || 0;

        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const ws_url = `${protocol}://${window.location.host}/ws/notifications/`;

        this.log.info(`🔔 Conectando WebSocket de Notificações: ${ws_url} (Tentativa ${this.notificationReconnectAttempts + 1}/${this.maxReconnectAttempts})`);
        
        try {
            this.notificationSocket = new WebSocket(ws_url);

            this.notificationSocket.onopen = (e) => {
                this.log.success('✅ WebSocket de Notificações conectado');
                this.notificationConnecting = false;
                this.notificationReconnectAttempts = 0;
            };

            this.notificationSocket.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    this.log.info('🔔 Notificação Recebida:', data);

                    switch (data.type) {
                        case 'new_chat_notification':
                            this.log.info(`Nova conversa de ${data.room_name}`);
                            this.handleNewChatRoomUI(data);
                            this.playNotificationSound('connect');
                            break;
                        default:
                            this.log.debug('Notificação não tratada:', data.type);
                    }
                } catch (error) {
                    this.log.error('Erro ao processar notificação:', error);
                }
            };

            this.notificationSocket.onclose = (e) => {
                this.notificationConnecting = false;
                this.log.warn(`⚠️ WebSocket de Notificações fechado: ${e.code}`);

                // **EVITA LOOP INFINITO**
                if (e.code === 1000 || e.code === 1001) {
                    this.log.info('Notificações fechadas normalmente.');
                    return;
                }

                if (this.notificationReconnectAttempts >= this.maxReconnectAttempts) {
                    this.log.error('❌ Máximo de tentativas para notificações atingido.');
                    return;
                }

                // **RECONEXÃO CONTROLADA**
                this.notificationReconnectAttempts++;
                const delay = Math.min(this.notificationReconnectAttempts * 5000, 30000); // Max 30s
                
                this.log.warn(`⏰ Reagendando reconexão de notificações em ${delay / 1000}s...`);
                
                if (this.notificationReconnectTimeout) {
                    clearTimeout(this.notificationReconnectTimeout);
                }
                
                this.notificationReconnectTimeout = setTimeout(() => {
                    if (!this.notificationSocket || this.notificationSocket.readyState === WebSocket.CLOSED) {
                        this.connectNotificationSocket();
                    }
                }, delay);
            };

            this.notificationSocket.onerror = (e) => {
                this.notificationConnecting = false;
                this.log.error('❌ Erro no WebSocket de Notificações:', e);
            };

        } catch (error) {
            this.notificationConnecting = false;
            this.log.error('❌ Erro ao criar WebSocket de notificações:', error);
        }
    }


    // função handleNewChatRoomUI :

    handleNewChatRoomUI(roomData) {
        // Verifica se a sala já existe na UI para não duplicar
        const existingRoomElement = document.querySelector(`.chat-room-item[data-room-id="${roomData.room_id}"]`);
        if (existingRoomElement) {
            this.log.warn(`A sala ${roomData.room_id} já existe na UI. Apenas movendo para o topo.`);
            existingRoomElement.parentElement.prepend(existingRoomElement);
            return;
        }

        this.log.success(`🎨 Renderizando nova sala na UI: ${roomData.room_name}`);

        // Encontra o container da lista de conversas
        // **IMPORTANTE**: Verifique se o ID 'active-chat-list-container' corresponde ao seu HTML.
        const chatListContainer = document.getElementById('active-chat-list-container');
        
        if (!chatListContainer) {
            this.log.error("Container da lista de chats ('active-chat-list-container') não encontrado!");
            return;
        }
        
        // Remove a mensagem "Nenhuma conversa ativa", se ela existir
        const emptyStateMessage = chatListContainer.querySelector('.chat-empty-state');
        if (emptyStateMessage) {
            emptyStateMessage.remove();
        }

        // Cria o elemento HTML para a nova sala
        // **Adapte este HTML para ser exatamente igual ao de uma sala já existente**
        const newRoomElement = document.createElement('div');
        newRoomElement.className = 'chat-room-item'; // Use a classe correta do seu CSS
        newRoomElement.setAttribute('data-room-id', roomData.room_id);
        newRoomElement.innerHTML = `
            <div class="avatar-placeholder"></div> <!-- Ou <img src="..."> -->
            <div class="room-info">
                <div class="room-name">${roomData.room_name}</div>
                <div class="last-message-preview">Nova conversa iniciada...</div>
            </div>
            <div class="unread-badge">1</div>
        `;

        // Adiciona o evento de clique para abrir a conversa
        newRoomElement.addEventListener('click', () => {
            this.openChat(roomData.room_id, roomData.room_name);
        });

        // Adiciona a nova sala no topo da lista
        chatListContainer.prepend(newRoomElement);
        
        // Adiciona ao cache interno para consistência
        if (!this.cache.rooms.some(room => room.room_id === roomData.room_id)) {
            this.cache.rooms.unshift(roomData);
        }
    }
    
    handleWebSocketMessage(data) {
        console.log('📨 WebSocket message received:', data);
    
        switch (data.type) {
            case 'new_message':
            case 'chat_message':
                this.handleNewMessage(data);
                break;
                
            case 'file_message':
                this.handleFileMessage(data);
                break;
                
            case 'user_joined':
                this.handleUserJoined(data);
                break;
                
            case 'user_left':
                this.handleUserLeft(data);
                break;
                
            case 'typing':
                this.handleTypingIndicator(data);
                break;
                
            case 'message_edited':
                this.handleMessageEdited(data);
                break;
                
            case 'message_deleted':
                this.handleMessageDeleted(data);
                break;
            
            case 'message_read':
            // Opcional: atualiza status de leitura
            break;
                
            default:
                this.log.debug('Mensagem WebSocket não tratada:', data);
        }
    }

    handleNewMessage(data) {
        console.log('💬 Nova mensagem recebida:', data);
        
        // Verifica se a mensagem é para a sala atual
        if (data.room_id && data.room_id !== this.currentRoom) {
            console.log('Mensagem para outra sala, atualizando badge');
            this.updateUnreadBadge(data.room_id);
            return;
        }
        
        // ✅ CORREÇÃO: Prepara dados da mensagem com fallbacks
        const messageData = {
            id: data.message_id || data.id,
            message: data.message || data.content || '',
            message_type: data.message_type || 'text',
            file_data: data.file_data || null,
            image_url: data.image_url || null,
            username: data.username || 'Usuário',
            user_id: data.user_id,
            timestamp: data.timestamp || new Date().toISOString(),
            is_own: data.user_id == this.currentUserId
        };
        
        // Exibe a mensagem na interface
        this.displayMessage(messageData);
        
        // Toca som de notificação se não for própria mensagem
        if (data.user_id != this.currentUserId) {
            this.playNotificationSound('message');
            
            if (document.hidden || this.isMinimized) {
                const preview = data.message_type === 'file' 
                    ? '📎 Arquivo enviado' 
                    : (data.message || data.content || '').substring(0, 50);
                this.showDesktopNotification(`${data.username}: ${preview}`);
            }
        }
    }

    handleFileMessage(data) {
        this.handleNewMessage(data);
    }

    handleUserJoined(data) {
        this.playNotificationSound('connect');
        this.showSystemMessage(`${data.username} entrou no chat`);
    }

    handleUserLeft(data) {
        this.showSystemMessage(`${data.username} saiu do chat`);
    }

    handleTypingIndicator(data) {
        this.showTypingIndicator(data.user_id, data.username);
    }

    handleMessageEdited(data) {
        // Atualiza mensagem no cache
        if (this.cache.messages[this.currentRoom]) {
            const index = this.cache.messages[this.currentRoom].findIndex(m => m.id === data.message_id);
            if (index !== -1) {
                this.cache.messages[this.currentRoom][index].message = data.new_content;
                this.cache.messages[this.currentRoom][index].edited = true;
                
                // Atualiza na interface
                this.updateMessageInUI(data.message_id, data.new_content);
            }
        }
    }

    handleMessageDeleted(data) {
        // Remove do cache
        if (this.cache.messages[this.currentRoom]) {
            this.cache.messages[this.currentRoom] = this.cache.messages[this.currentRoom]
                .filter(m => m.id !== data.message_id);
        }
        
        // Remove da interface
        this.removeMessageFromUI(data.message_id);
    }

    updateMessageInUI(messageId, newContent) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            const textElement = messageElement.querySelector('.message-text');
            if (textElement) {
                textElement.innerHTML = this.formatMessageText(newContent);
            }
            
            // Adiciona indicador de edição
            const editedElement = messageElement.querySelector('.message-edited') || 
                document.createElement('small');
            editedElement.className = 'message-edited text-muted';
            editedElement.innerHTML = '<i class="bi bi-pencil"></i> editado';
            
            if (!messageElement.querySelector('.message-edited')) {
                messageElement.querySelector('.message-content').appendChild(editedElement);
            }
        }
    }

    removeMessageFromUI(messageId) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            messageElement.innerHTML = `
                <div class="message-content">
                    <div class="message-deleted">
                        <i class="bi bi-trash"></i>
                        <span>Mensagem excluída</span>
                    </div>
                </div>
            `;
            messageElement.classList.add('deleted-message');
        }
    }

    showTypingIndicator(userId, username) {
        const indicatorsContainer = document.getElementById('typing-indicators');
        if (!indicatorsContainer) return;
        
        // Remove indicador anterior do mesmo usuário
        const existingIndicator = indicatorsContainer.querySelector(`[data-user-id="${userId}"]`);
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        // Cria novo indicador
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.dataset.userId = userId;
        indicator.innerHTML = `
            <div class="typing-dots">
                <span></span><span></span><span></span>
            </div>
            <span class="typing-text">${username} está digitando...</span>
        `;
        
        indicatorsContainer.appendChild(indicator);
        
        // Remove após 5 segundos
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.remove();
            }
        }, 5000);
    }

    showSystemMessage(text) {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return;
        
        const systemDiv = document.createElement('div');
        systemDiv.className = 'system-message';
        systemDiv.innerHTML = `
            <div class="message-content">
                <div class="system-text">${this.escapeHtml(text)}</div>
            </div>
        `;
        
        chatLog.appendChild(systemDiv);
        this.scrollToBottom();
    }

    updateUnreadBadge(roomId) {
        // Atualiza badge na lista de conversas
        const roomElement = document.querySelector(`[data-room-id="${roomId}"]`);
        if (roomElement) {
            let unreadBadge = roomElement.querySelector('.chat-list-unread');
            if (!unreadBadge) {
                unreadBadge = document.createElement('div');
                unreadBadge.className = 'chat-list-unread';
                roomElement.appendChild(unreadBadge);
                roomElement.classList.add('has-unread');
            }
            
            const currentCount = parseInt(unreadBadge.textContent) || 0;
            unreadBadge.textContent = currentCount + 1;
        }
        
        // Atualiza badge no botão flutuante
        const notificationIndicator = document.querySelector('.notification-indicator');
        if (notificationIndicator) {
            const currentCount = parseInt(notificationIndicator.textContent) || 0;
            notificationIndicator.textContent = currentCount + 1;
            notificationIndicator.style.display = 'block';
        }
    }

    showDesktopNotification(message) {
        if (!("Notification" in window)) return;
        
        if (Notification.permission === "granted") {
            new Notification("Nova mensagem", {
                body: message,
                icon: '/static/images/chat-icon.png'
            });
        } else if (Notification.permission !== "denied") {
            Notification.requestPermission().then(permission => {
                if (permission === "granted") {
                    new Notification("Nova mensagem", {
                        body: message,
                        icon: '/static/images/chat-icon.png'
                    });
                }
            });
        }
    }

    // ==================== ENVIO DE MENSAGENS ====================
    
    sendMessage() {
        const input = document.getElementById('chat-message-input');
        const message = input?.value?.trim();
        
        if (!message) {
            this.showNotification('Digite uma mensagem', 'warning');
            return;
        }
        
        if (!this.websocket || !this.isConnected) {
            this.showNotification('Reconectando...', 'info');
            // Tenta reconectar
            if (this.currentRoom) {
                this.connectWebSocket(this.currentRoom);
            }
            return;
        }

        try {
            // Envia via WebSocket
            this.websocket.send(JSON.stringify({
                type: 'chat_message',
                message: message,
                room_id: this.currentRoom,
                timestamp: new Date().toISOString()
            }));
            
            // Limpa input
            input.value = '';
            input.style.height = 'auto';
            
            // Fecha preview se estiver aberto
            this.closePreview();
            
        } catch (error) {
            this.log.error('Erro ao enviar mensagem:', error);
            this.showNotification('Falha no envio', 'error');
        }
    }

    displayMessage(data) {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) {
            console.error('❌ chat-log não encontrado');
            return;
        }
        
        console.log('🖼️ Exibindo mensagem:', data);
        
        // Remove estados vazios
        chatLog.querySelectorAll('.welcome-state, .loading-state').forEach(el => el.remove());
        
        // Cria elemento da mensagem
        const messageDiv = document.createElement('div');
        const isOwn = data.is_own || data.user_id == this.currentUserId;
        messageDiv.className = `message ${isOwn ? 'own-message' : 'other-message'}`;
        messageDiv.dataset.messageId = data.id || data.message_id;
        
        // ✅ CORREÇÃO: Trata timestamp inválido
        let timestamp = 'Agora';
        if (data.timestamp) {
            const date = new Date(data.timestamp);
            if (!isNaN(date.getTime())) {
                timestamp = date.toLocaleTimeString('pt-BR', {
                    hour: '2-digit', 
                    minute: '2-digit'
                });
            }
        }
        
        // ✅ CORREÇÃO: Garante que username nunca seja vazio
        const username = data.username || 'Usuário';
        
        // ✅ CORREÇÃO: Detecta tipo de mensagem e renderiza corretamente
        let contentHtml = '';
        
        if (data.message_type === 'file' && data.file_data) {
            // Renderiza arquivo/imagem
            contentHtml = this.renderFileContent(data);
        } else if (data.message_type === 'image' && data.image_url) {
            // Renderiza imagem direta
            contentHtml = `
                <div class="message-image">
                    <img src="${data.image_url}" alt="Imagem" class="img-fluid rounded" 
                        style="max-width: 200px; cursor: pointer;"
                        onclick="chatManager.viewImage('${data.image_url}')">
                </div>
            `;
        } else {
            // Mensagem de texto
            const messageText = data.message || data.content || '';
            contentHtml = `<div class="message-text">${this.formatMessageText(messageText)}</div>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">${this.escapeHtml(username)}</span>
                    <span class="message-time">${timestamp}</span>
                </div>
                ${contentHtml}
            </div>
        `;
        
        chatLog.appendChild(messageDiv);
        this.scrollToBottom();
        
        console.log('✅ Mensagem exibida com sucesso');
    }

    // ==================== BUSCA NO CHAT ====================
    
    initializeChatSearch() {
        this.bindElement('toggle-chat-search-btn', 'click', () => this.toggleChatSearch());
        this.bindElement('close-chat-search-btn', 'click', () => this.closeChatSearch());
        this.bindElement('chat-search-input', 'input', (e) => this.performChatSearch(e.target.value));
        this.bindElement('chat-search-input', 'keypress', (e) => {
            if (e.key === 'Enter') {
                this.performChatSearch(e.target.value);
            }
        });
    }

    toggleChatSearch() {
        const container = document.getElementById('chat-search-container');
        const input = document.getElementById('chat-search-input');
        
        if (!container) return;
        
        const isVisible = container.style.display !== 'none';
        
        if (isVisible) {
            container.style.display = 'none';
            this.clearSearchHighlights();
        } else {
            container.style.display = 'block';
            if (input) {
                input.focus();
                input.select();
            }
        }
    }

    closeChatSearch() {
        const container = document.getElementById('chat-search-container');
        if (container) {
            container.style.display = 'none';
        }
        this.clearSearchHighlights();
    }

    async performChatSearch(query) {
        this.currentSearchQuery = query;
        
        if (!query || query.length < 2) {
            this.clearSearchResults();
            return;
        }
        
        const resultsContainer = document.getElementById('chat-search-results');
        if (!resultsContainer) return;
        
        // Mostrar loading
        resultsContainer.innerHTML = `
            <div class="text-center p-3">
                <div class="spinner-border spinner-border-sm"></div>
                <p class="mt-2 mb-0">Buscando "${query}"...</p>
            </div>
        `;
        
        try {
            // Busca local primeiro
            const localResults = this.searchLocalMessages(query);
            
            // Busca no servidor se necessário
            const serverResults = await this.searchServerMessages(query);
            
            const allResults = [...localResults, ...serverResults];
            this.searchResults = allResults;
            this.displaySearchResults(allResults, query);
            
        } catch (error) {
            this.log.error('Erro na busca:', error);
            resultsContainer.innerHTML = `
                <div class="text-center p-3 text-danger">
                    <i class="bi bi-exclamation-circle"></i>
                    <p>Erro na busca</p>
                </div>
            `;
        }
    }

    searchLocalMessages(query) {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return [];
        
        const messages = chatLog.querySelectorAll('.message');
        const results = [];
        
        messages.forEach((message, index) => {
            const textContent = message.textContent.toLowerCase();
            if (textContent.includes(query.toLowerCase())) {
                const messageText = message.querySelector('.message-text')?.textContent || '';
                const sender = message.querySelector('.message-sender')?.textContent || '';
                const time = message.querySelector('.message-time')?.textContent || '';
                
                results.push({
                    index,
                    sender,
                    time,
                    text: messageText,
                    element: message
                });
            }
        });
        
        return results;
    }

    async searchServerMessages(query) {
        if (!this.currentRoom || !this.urls.search_messages_url) return [];
        
        try {
            const response = await fetch(this.urls.search_messages_url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ 
                    query, 
                    room_id: this.currentRoom,
                    user_id: this.currentUserId 
                })
            });
            
            const data = await response.json();
            return data.status === 'success' ? data.messages : [];
            
        } catch (error) {
            this.log.warn('Busca no servidor falhou:', error);
            return [];
        }
    }

    displaySearchResults(results, query) {
        const container = document.getElementById('chat-search-results');
        if (!container) return;
        
        if (results.length === 0) {
            container.innerHTML = `
                <div class="text-center p-3 text-muted">
                    <i class="bi bi-search"></i>
                    <p>Nenhum resultado para "${query}"</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="search-results-header p-2 border-bottom">
                <small class="text-muted">${results.length} resultado(s) encontrado(s)</small>
            </div>
            ${results.map((result, index) => `
                <div class="search-result-item p-2 border-bottom" 
                     onclick="chatManager.goToMessage(${result.index || index})">
                    <div class="search-result-sender">
                        <strong>${this.escapeHtml(result.sender)}</strong>
                        <small class="text-muted ms-2">${result.time}</small>
                    </div>
                    <div class="search-result-text">${this.highlightQuery(result.text, query)}</div>
                </div>
            `).join('')}
        `;
        
        // Destaca resultados no chat
        this.highlightSearchResults(results);
    }

    highlightSearchResults(results) {
        this.clearSearchHighlights();
        
        results.forEach(result => {
            if (result.element) {
                result.element.classList.add('search-highlighted');
            }
        });
    }

    clearSearchHighlights() {
        document.querySelectorAll('.search-highlighted').forEach(el => {
            el.classList.remove('search-highlighted');
        });
    }

    clearSearchResults() {
        const container = document.getElementById('chat-search-results');
        if (container) {
            container.innerHTML = '';
        }
    }

    goToMessage(messageIndex) {
        const chatLog = document.getElementById('chat-log');
        const messages = chatLog?.querySelectorAll('.message');
        
        if (messages && messages[messageIndex]) {
            messages[messageIndex].scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
            
            // Destaque temporário
            messages[messageIndex].style.backgroundColor = 'rgba(var(--bs-primary-rgb), 0.1)';
            setTimeout(() => {
                messages[messageIndex].style.backgroundColor = '';
            }, 2000);
        }
    }

    highlightMessage(messageId) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            messageElement.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
            
            // Destaque temporário
            messageElement.style.backgroundColor = 'rgba(var(--bs-primary-rgb), 0.1)';
            setTimeout(() => {
                messageElement.style.backgroundColor = '';
            }, 2000);
        }
    }

    // ==================== PREVIEW DE MENSAGENS ====================
    
    initializePreview() {
        this.bindElement('close-preview-btn', 'click', () => this.closePreview());
        this.bindElement('edit-preview-btn', 'click', () => this.editPreview());
        this.bindElement('send-preview-btn', 'click', () => this.sendPreviewMessage());
        
        // Auto-preview para mensagens longas
        const messageInput = document.getElementById('chat-message-input');
        if (messageInput) {
            messageInput.addEventListener('input', (e) => {
                if (e.target.value.length > 100) {
                    this.showPreview(e.target.value);
                } else {
                    this.closePreview();
                }
            });
        }
    }

    showPreview(message) {
        const container = document.getElementById('response-preview-container');
        const content = document.getElementById('response-preview-content');
        
        if (!container || !content) return;
        
        const processedContent = this.processMessageContent(message);
        
        content.innerHTML = `
            <div class="preview-message">
                <div class="preview-message-content">${processedContent}</div>
                <div class="preview-message-meta">
                    <small class="text-muted">
                        ${message.length} caracteres • 
                        ${message.split('\n').length} linhas
                    </small>
                </div>
            </div>
        `;
        
        container.style.display = 'block';
    }

    closePreview() {
        const container = document.getElementById('response-preview-container');
        if (container) {
            container.style.display = 'none';
        }
    }

    editPreview() {
        const input = document.getElementById('chat-message-input');
        const content = document.getElementById('response-preview-content');
        
        if (input && content) {
            const previewText = content.textContent || '';
            input.value = previewText;
            input.focus();
            input.setSelectionRange(previewText.length, previewText.length);
        }
    }

    sendPreviewMessage() {
        this.sendMessage();
        this.closePreview();
    }

    // ==================== CONTEÚDO DINÂMICO ====================
    
    initializeDynamicContent() {
        this.loadDynamicSections();
        
        // Atualização periódica
        setInterval(() => {
            if (this.currentRoom) {
                this.updateDynamicContent();
            }
        }, 30000);
    }

    async loadDynamicSections() {
        const container = document.getElementById('dynamic-content-section');
        if (!container) return;
        
        try {
            // Carrega conteúdo dinâmico
            const content = await this.loadDynamicContent();
            container.innerHTML = content || this.getEmptyDynamicContent();
            
        } catch (error) {
            this.log.error('Erro carregando conteúdo dinâmico:', error);
            container.innerHTML = this.getErrorDynamicContent();
        }
    }

    async loadDynamicContent() {
        // Simula carregamento de conteúdo dinâmico
        return `
            <div class="dynamic-content-section">
                <div class="dynamic-section user-status-section">
                    <h6><i class="bi bi-people"></i> Status do Sistema</h6>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-number">0</span>
                            <span class="stat-label">Online</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number">0</span>
                            <span class="stat-label">Ativos</span>
                        </div>
                    </div>
                </div>
                <div class="dynamic-section quick-actions-section">
                    <h6><i class="bi bi-lightning"></i> Ações Rápidas</h6>
                    <div class="quick-actions-grid">
                        <button class="btn btn-sm btn-outline-primary" onclick="chatManager.shareScreen()">
                            <i class="bi bi-display"></i> Compartilhar
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="chatManager.createPoll()">
                            <i class="bi bi-list-check"></i> Enquete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    updateDynamicContent() {
        // Atualiza contadores dinâmicos
        this.updateUserCount();
        this.updateMessageCount();
    }

    updateUserCount() {
        const statNumbers = document.querySelectorAll('.stat-number');
        if (statNumbers.length > 0) {
            // Simula atualização
            statNumbers[0].textContent = Math.floor(Math.random() * 10) + 1;
        }
    }

    updateMessageCount() {
        const chatLog = document.getElementById('chat-log');
        const messageCount = chatLog?.querySelectorAll('.message').length || 0;
        
        const statElements = document.querySelectorAll('.stat-number');
        if (statElements[1]) {
            statElements[1].textContent = messageCount;
        }
    }

    getEmptyDynamicContent() {
        return `
            <div class="text-center p-3 text-muted">
                <i class="bi bi-inbox"></i>
                <p>Conteúdo dinâmico não disponível</p>
            </div>
        `;
    }

    getErrorDynamicContent() {
        return `
            <div class="text-center p-3 text-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <p>Erro ao carregar conteúdo</p>
                <button class="btn btn-sm btn-outline-danger" onclick="chatManager.loadDynamicSections()">
                    Tentar Novamente
                </button>
            </div>
        `;
    }

    // ==================== MODAIS ====================
    
    async initializeModals() {
        // Busca nos modais
        this.bindElement('dm-user-search', 'input', (e) => this.filterUsers(e.target.value));
        this.bindElement('task-search', 'input', (e) => this.filterTasks(e.target.value));
        
        // Form de grupo
        this.bindElement('create-group-form', 'submit', (e) => this.createGroupChat(e));
        
        // Configura eventos dos modais
        this.setupModalEvents();
    }

    setupModalEvents() {
        const novaConversaModal = document.getElementById('novaConversaModal');
        if (novaConversaModal) {
            novaConversaModal.addEventListener('shown.bs.modal', () => {
                this.loadModalData();
            });
        }
    }

    async loadModalData() {
        // Carrega dados dos modais quando necessário
        await Promise.all([
            this.renderUsersModal(),
            this.renderTasksModal(),
            this.renderGroupModal()
        ]);
    }

    async renderUsersModal() {
        const container = document.getElementById('dm-user-list-container');
        if (!container) return;

        try {
            // Carrega usuários se não estiverem em cache
            if (this.cache.users.length === 0) {
                const response = await fetch(this.urls.user_list);
                const data = await response.json();
                if (data.status === 'success' && data.users) {
                    this.cache.users = data.users;
                }
            }

            if (this.cache.users.length > 0) {
                container.innerHTML = this.cache.users.map(user => `
                    <div class="user-list-item" onclick="chatManager.startDM('${user.id}')">
                        <div class="user-avatar"><i class="bi bi-person-fill"></i></div>
                        <div class="user-info">
                            <div class="user-name">${this.escapeHtml(user.display_name || user.username)}</div>
                            <div class="user-email">@${this.escapeHtml(user.username)}</div>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = `
                    <div class="text-center p-4 text-muted">
                        <i class="bi bi-people" style="font-size: 2rem;"></i>
                        <p>Nenhum usuário encontrado</p>
                    </div>
                `;
            }
        } catch (error) {
            this.log.error('Erro ao carregar usuários:', error);
            container.innerHTML = `
                <div class="text-center p-4 text-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p>Erro ao carregar usuários</p>
                </div>
            `;
        }
    }

    async renderTasksModal() {
        const container = document.getElementById('task-list-container');
        if (!container) return;

        try {
            // Carrega tarefas se não estiverem em cache
            if (this.cache.tasks.length === 0) {
                const response = await fetch(this.urls.task_list);
                const data = await response.json();
                if (data.status === 'success' && data.tasks) {
                    this.cache.tasks = data.tasks;
                }
            }

            if (this.cache.tasks.length > 0) {
                container.innerHTML = this.cache.tasks.map(task => `
                    <div class="task-list-item" onclick="chatManager.openTaskChat(${task.id})">
                        <div class="task-icon"><i class="bi bi-check-square-fill"></i></div>
                        <div class="task-info">
                            <div class="task-title">${this.escapeHtml(task.titulo)}</div>
                            <div class="task-details">
                                <span class="badge bg-secondary">${task.status || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = `
                    <div class="text-center p-4 text-muted">
                        <i class="bi bi-list-task" style="font-size: 2rem;"></i>
                        <p>Nenhuma tarefa encontrada</p>
                    </div>
                `;
            }
        } catch (error) {
            this.log.error('Erro ao carregar tarefas:', error);
            container.innerHTML = `
                <div class="text-center p-4 text-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p>Erro ao carregar tarefas</p>
                </div>
            `;
        }
    }

    renderGroupModal() {
        const select = document.getElementById('group-participants-select');
        if (!select || this.cache.users.length === 0) return;

        select.innerHTML = this.cache.users.map(user => `
            <option value="${user.id}">${this.escapeHtml(user.display_name || user.username)}</option>
        `).join('');
    }

    filterUsers(searchTerm) {
        const container = document.getElementById('dm-user-list-container');
        if (!container) return;
        
        const filtered = this.cache.users.filter(user => 
            user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (user.display_name || '').toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="text-center p-3 text-muted">
                    <i class="bi bi-search"></i>
                    <p>Nenhum usuário encontrado</p>
                </div>
            `;
        } else {
            container.innerHTML = filtered.map(user => `
                <div class="user-list-item" onclick="chatManager.startDM('${user.id}')">
                    <div class="user-avatar"><i class="bi bi-person-fill"></i></div>
                    <div class="user-info">
                        <div class="user-name">${this.escapeHtml(user.display_name || user.username)}</div>
                        <div class="user-email">@${this.escapeHtml(user.username)}</div>
                    </div>
                </div>
            `).join('');
        }
    }

    filterTasks(searchTerm) {
        const container = document.getElementById('task-list-container');
        if (!container) return;
        
        const filtered = this.cache.tasks.filter(task => 
            task.titulo.toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="text-center p-3 text-muted">
                    <i class="bi bi-search"></i>
                    <p>Nenhuma tarefa encontrada</p>
                </div>
            `;
        } else {
            container.innerHTML = filtered.map(task => `
                <div class="task-list-item" onclick="chatManager.openTaskChat(${task.id})">
                    <div class="task-icon"><i class="bi bi-check-square-fill"></i></div>
                    <div class="task-info">
                        <div class="task-title">${this.escapeHtml(task.titulo)}</div>
                        <div class="task-details">
                            <span class="badge bg-secondary">${task.status || 'N/A'}</span>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    }

    // ==================== AÇÕES DO CHAT ====================
    
    async startDM(userId) {
        try {
            this.log.info(`Iniciando DM com ${userId}`);
            const response = await fetch(this.urls.start_dm_base.replace('0', userId));
            const data = await response.json();
            
            if (data.status === 'success') {
                await this.openChatDialog(data.room_id, data.room_name);
                this.closeModal('novaConversaModal');
                this.showNotification('Conversa iniciada!', 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.log.error('Erro startDM:', error);
            this.showNotification('Falha ao iniciar conversa', 'error');
        }
    }

    async createGroupChat(event) {
        event.preventDefault();
        
        try {
            const formData = new FormData(event.target);
            const name = formData.get('name')?.trim();
            const participants = formData.getAll('participants');
            
            if (!name) return this.showNotification('Nome obrigatório', 'warning');
            if (!participants.length) return this.showNotification('Selecione participantes', 'warning');

            const response = await fetch(this.urls.create_group_url, {
                method: 'POST',
                headers: { 'X-CSRFToken': this.getCSRFToken() },
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                await this.openChatDialog(data.room_id, data.room_name);
                this.closeModal('novaConversaModal');
                this.showNotification('Grupo criado!', 'success');
                event.target.reset();
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.log.error('Erro createGroup:', error);
            this.showNotification('Falha ao criar grupo', 'error');
        }
    }

    async openTaskChat(taskId) {
        if (!this.urls.get_task_chat_base) {
            return this.showNotification('Funcionalidade não disponível', 'warning');
        }

        try {
            const response = await fetch(this.urls.get_task_chat_base.replace('0', taskId));
            const data = await response.json();
            
            if (data.status === 'success') {
                await this.openChatDialog(data.room_id, data.room_name);
                this.closeModal('novaConversaModal');
                this.showNotification('Chat da tarefa aberto!', 'success');
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            this.log.error('Erro openTaskChat:', error);
            this.showNotification('Falha ao acessar chat da tarefa', 'error');
        }
    }

    showChatInfo() {
        const modalElement = document.getElementById('chatInfoModal');
        const modalContent = document.getElementById('chat-info-content');
        
        if (!modalContent || !modalElement) return;
        
        modalContent.innerHTML = `
            <div class="chat-info-details">
                <h6>Detalhes da Conversa</h6>
                <p><strong>Nome:</strong> ${this.currentRoomName || 'N/A'}</p>
                <p><strong>ID da Sala:</strong> ${this.currentRoom || 'N/A'}</p>
                <p><strong>Status:</strong> ${this.isConnected ? '🟢 Conectado' : '🔴 Desconectado'}</p>
                <p><strong>Som:</strong> ${this.soundEnabled ? 'Ativado' : 'Desativado'}</p>
                <hr>
                <p><strong>Mensagens em cache:</strong> ${this.cache.messages[this.currentRoom]?.length || 0}</p>
                <p><strong>Arquivos enviados:</strong> ${this.countFilesInRoom()}</p>
            </div>
        `;
        
        // Remove aria-hidden antes de mostrar
        modalElement.removeAttribute('aria-hidden');
        
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        
        // Restaura aria-hidden quando fechar
        modalElement.addEventListener('hidden.bs.modal', () => {
            document.activeElement?.blur();
            modalElement.setAttribute('aria-hidden', 'true');
        }, { once: true });
    }


    // ==================== SISTEMA DE SOM ====================
    
    async initializeSoundSystem() {
        try {
            // Verifica suporte a áudio
            if (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined') {
                this.audioContext = new (AudioContext || webkitAudioContext)();
            }
            
            // Pre-carrega sons
            await this.preloadSounds();
            this.soundInitialized = true;
            this.updateSoundButton();
            
            this.log.success('Sistema de som inicializado');
        } catch (error) {
            this.log.warn('Falha ao inicializar áudio:', error);
            this.soundEnabled = false;
            this.updateSoundButton();
        }
    }

    async preloadSounds() {
        const sounds = {
            notification: '/static/sounds/notification_1.mp3',
            message: '/static/sounds/notification_2.mp3',
            connect: '/static/sounds/notification_2.mp3'
        };

        for (const [key, url] of Object.entries(sounds)) {
            try {
                const audio = new Audio();
                audio.preload = 'auto';
                audio.volume = 0.3;
                
                // Fallback para sons sintéticos se o arquivo não existir
                audio.onerror = () => {
                    this.log.info(`Usando som sintético para ${key}`);
                    this.audioElements[key] = this.createSyntheticSound(key);
                };
                
                // Evento de sucesso
                audio.oncanplaythrough = () => {
                    this.audioElements[key] = audio;
                    this.log.success(`Som ${key} carregado`);
                };
                
                audio.src = url;
                
                // Timeout para fallback
                setTimeout(() => {
                    if (!this.audioElements[key]) {
                        this.log.info(`Timeout no carregamento de ${key}, usando sintético`);
                        this.audioElements[key] = this.createSyntheticSound(key);
                    }
                }, 1000);
                
            } catch (error) {
                this.log.warn(`Erro carregando som ${key}:`, error);
                this.audioElements[key] = this.createSyntheticSound(key);
            }
        }
    }
    createSyntheticSound(type) {
        return {
            play: () => {
                if (!this.audioContext || !this.soundEnabled) return;
                
                try {
                    const oscillator = this.audioContext.createOscillator();
                    const gainNode = this.audioContext.createGain();
                    
                    oscillator.connect(gainNode);
                    gainNode.connect(this.audioContext.destination);
                    
                    // Diferentes frequências para diferentes tipos
                    const frequencies = {
                        notification: [800, 1000, 1200],
                        message: [400, 600],
                        connect: [200, 400, 800]
                    };
                    
                    const freq = frequencies[type] || [440];
                    oscillator.frequency.setValueAtTime(freq[0], this.audioContext.currentTime);
                    
                    // Envelope de volume
                    gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
                    gainNode.gain.linearRampToValueAtTime(0.1, this.audioContext.currentTime + 0.01);
                    gainNode.gain.exponentialRampToValueAtTime(0.001, this.audioContext.currentTime + 0.3);
                    
                    oscillator.start(this.audioContext.currentTime);
                    oscillator.stop(this.audioContext.currentTime + 0.3);
                    
                } catch (error) {
                    this.log.warn('Erro reproduzindo som sintético:', error);
                }
            }
        };
    }

    toggleSound() {
        if (!this.soundInitialized) {
            this.initializeSoundSystem();
        }
        
        this.soundEnabled = !this.soundEnabled;
        localStorage.setItem('chat-sound-enabled', this.soundEnabled.toString());
        this.updateSoundButton();
        
        // Teste de som ao ativar
        if (this.soundEnabled) {
            this.playNotificationSound('connect');
        }
        
        this.showNotification(
            `Notificações de som ${this.soundEnabled ? 'ativadas' : 'desativadas'}`,
            'info'
        );
    }

    updateSoundButton() {
        const button = document.getElementById('chat-sound-toggle');
        const icon = button?.querySelector('i');
        
        if (icon) {
            icon.className = this.soundEnabled && this.soundInitialized
                ? 'bi bi-volume-up-fill' 
                : 'bi bi-volume-mute-fill';
        }
        
        if (button) {
            button.title = this.soundEnabled ? 'Desativar som' : 'Ativar som';
            button.classList.toggle('active', this.soundEnabled);
        }
    }

    playNotificationSound(type = 'notification') {
        if (!this.soundEnabled || !this.soundInitialized) return;
        
        try {
            const audio = this.audioElements?.[type];
            if (audio) {
                // Reset audio para permitir múltiplas reproduções
                if (audio.currentTime) {
                    audio.currentTime = 0;
                }
                audio.play().catch(e => {
                    this.log.warn('Falha reprodução áudio:', e);
                });
            }
        } catch (error) {
            this.log.warn('Erro playNotificationSound:', error);
        }
    }

    // ==================== DRAG AND DROP ====================

    initializeDrag() {
        const header = document.getElementById('chat-dialog-header');
        const container = document.getElementById('chat-draggable-container');

        if (!header || !container) {
            this.log.warn('Elementos para drag não encontrados');
            return;
        }

        // Configura posição inicial (do template)
        container.style.position = 'fixed';
        container.style.right = '20px';
        container.style.bottom = '80px';

        // Event listeners para drag
        header.addEventListener('mousedown', (e) => this.startDrag(e));
        document.addEventListener('mousemove', (e) => this.drag(e));
        document.addEventListener('mouseup', () => this.stopDrag());
        
        this.log.success('Sistema de drag inicializado');
    }

    startDrag(e) {
        // Ignora se clicar em um botão
        if (e.target.closest('.btn') || e.target.closest('.header-buttons')) {
            return;
        }
        
        const container = document.getElementById('chat-draggable-container');
        if (!container) return;
        
        this.dragData = {
            isDragging: true,
            offsetX: e.clientX - container.getBoundingClientRect().left,
            offsetY: e.clientY - container.getBoundingClientRect().top
        };
        
        container.style.transition = 'none';
        container.style.cursor = 'grabbing';
        
        const header = document.getElementById('chat-dialog-header');
        if (header) {
            header.style.cursor = 'grabbing';
        }
    }

    drag(e) {
        if (!this.dragData.isDragging) return;
        
        const container = document.getElementById('chat-draggable-container');
        if (!container) return;
        
        const newX = e.clientX - this.dragData.offsetX;
        const newY = e.clientY - this.dragData.offsetY;
        
        // Limites da tela
        const maxX = window.innerWidth - container.offsetWidth;
        const maxY = window.innerHeight - container.offsetHeight;
        
        container.style.left = `${Math.max(0, Math.min(maxX, newX))}px`;
        container.style.top = `${Math.max(0, Math.min(maxY, newY))}px`;
        container.style.right = 'auto';
        container.style.bottom = 'auto';
    }

    stopDrag() {
        if (!this.dragData.isDragging) return;
        
        this.dragData.isDragging = false;
        
        const container = document.getElementById('chat-draggable-container');
        const header = document.getElementById('chat-dialog-header');
        
        if (container) {
            container.style.transition = 'all 0.3s ease';
            container.style.cursor = 'default';
        }
        
        if (header) {
            header.style.cursor = 'grab';
        }
    }

    // ==================== CONTROLES DE JANELA ====================
    
    toggleMinimize() {
        const container = document.getElementById('chat-draggable-container');
        const content = document.getElementById('chat-dialog-content');
        const minimizeBtn = document.getElementById('minimize-chat-btn');
        const maximizeBtn = document.getElementById('maximize-chat-btn');
        
        if (!container || !content) {
            this.log.error('Elementos do chat não encontrados para minimizar');
            return;
        }
        
        this.isMinimized = !this.isMinimized;
        
        if (this.isMinimized) {
            // Estado minimizado
            content.style.display = 'none';
            container.style.height = '60px';
            container.classList.add('minimized');
            
            if (minimizeBtn) minimizeBtn.style.display = 'none';
            if (maximizeBtn) maximizeBtn.style.display = 'inline-block';
            
            this.log.info('Chat minimizado');
        } else {
            // Estado normal
            content.style.display = 'flex';
            container.style.height = '500px';
            container.classList.remove('minimized');
            
            if (minimizeBtn) minimizeBtn.style.display = 'inline-block';
            if (maximizeBtn) maximizeBtn.style.display = 'none';
            
            this.log.info('Chat expandido');
        }
        
        // Força o reflow
        container.offsetHeight;
    }

    closeChat() {
        const container = document.getElementById('chat-draggable-container');
        if (container) {
            container.style.display = 'none';
            container.classList.remove('minimized');
        }
        
        // **LIMPEZA COMPLETA DE WEBSOCKETS**
        this.cleanupWebSockets();
        
        // Limpa estado
        this.isMinimized = false;
        this.currentRoom = null;
        this.currentRoomName = null;
        this.isConnected = false;
        
        this.log.info('💥 Chat fechado e recursos limpos');
    }

    cleanupWebSockets() {
        // **CANCELA TIMEOUTS DE RECONEXÃO**
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
        
        if (this.notificationReconnectTimeout) {
            clearTimeout(this.notificationReconnectTimeout);
            this.notificationReconnectTimeout = null;
        }
        
        // **FECHA WEBSOCKETS**
        if (this.websocket) {
            this.websocket.onclose = null; // Remove listener para evitar reconexão
            this.websocket.close(1000, 'Chat fechado pelo usuário');
            this.websocket = null;
        }
        
        // **RESETA CONTADORES**
        this.reconnectAttempts = 0;
        this.notificationReconnectAttempts = 0;
        this.isConnecting = false;
        this.notificationConnecting = false;
        
        this.log.success('🧹 WebSockets limpos');
    }

    // ==================== CONTROLE MANUAL DE RECONEXÃO ====================

    manualReconnect() {
        if (!this.currentRoom) {
            this.showNotification('Nenhuma sala selecionada', 'warning');
            return;
        }
        
        this.log.info('🔄 Reconexão manual solicitada');
        
        // **RESETA CONTADORES**
        this.reconnectAttempts = 0;
        this.notificationReconnectAttempts = 0;
        
        // **LIMPA CONEXÕES ANTIGAS**
        this.cleanupWebSockets();
        
        // **CONECTA NOVAMENTE**
        setTimeout(() => {
            this.connectWebSocket(this.currentRoom);
            this.connectNotificationSocket();
        }, 1000);
        
        this.showNotification('Reconectando...', 'info');
    }

    toggleChatListSidebar(show = null) {
        this.log.info('A função toggleChatListSidebar() foi chamada.');
        const overlay = document.getElementById('chatOverlay');
        const sidebar = document.getElementById('chatListContainer');
        
        if (!overlay || !sidebar) {
            this.log.error('CRÍTICO: Elementos da sidebar (overlay ou container) não encontrados.');
            return;
        }
        
        const shouldShow = show !== null ? show : !sidebar.classList.contains('active');
        this.log.info(`Sidebar deve ser exibida: ${shouldShow}`);

        // Mantém a lógica de classes para consistência de estado
        sidebar.classList.toggle('active', shouldShow);
        overlay.classList.toggle('active', shouldShow);

        // ===== NOVO CÓDIGO PARA FORÇAR A MUDANÇA VISUAL =====
        if (shouldShow) {
            // MOSTRA a sidebar
            sidebar.style.visibility = 'visible';
            sidebar.style.transform = 'translateX(0)';
            overlay.style.display = 'block';
            setTimeout(() => {
                overlay.style.opacity = '1';
            }, 10);
        } else {
            // ESCONDE a sidebar
            sidebar.style.transform = 'translateX(100%)';
            overlay.style.opacity = '0';
            
            // Esconde os elementos após a transição para não atrapalharem
            setTimeout(() => {
                sidebar.style.visibility = 'hidden';
                overlay.style.display = 'none';
            }, 300); // Duração da animação em milissegundos
        }
        
        if (shouldShow && this.cache.rooms.length === 0) {
            this.loadActiveRoomList();
        }
    }

    // ==================== CARREGAMENTO DE DADOS ====================
    
    async loadInitialData() {
        const loadTasks = [
            this.loadActiveRoomList(),
            this.preloadUsers(),
            this.preloadTasks()
        ];
        
        await Promise.allSettled(loadTasks);
    }

    async loadActiveRoomList() {
        const container = document.getElementById('active-chats-list');
        if (!container) return;

        try {
            const response = await fetch(this.urls.active_room_list);
            const data = await response.json();

            if (data.status === 'success' && data.rooms?.length > 0) {
                this.cache.rooms = data.rooms;
                this.renderRoomList(data.rooms);
                this.log.success(`${data.rooms.length} salas carregadas`);
            } else {
                this.renderEmptyState(container, 'chat-dots', 'Nenhuma conversa ativa', 'Clique em "Nova Conversa" para começar');
            }
        } catch (error) {
            this.log.error('Erro ao carregar salas:', error);
            this.renderErrorState(container, 'Erro ao carregar conversas', () => this.loadActiveRoomList());
        }
    }

    renderRoomList(rooms) {
        const container = document.getElementById('active-chats-list');
        if (!container) return;

        container.innerHTML = rooms.map(room => `
            <div class="chat-list-item ${room.unread_count > 0 ? 'has-unread' : ''}" 
                 data-room-id="${room.room_id}"
                 onclick="chatManager.openChatDialog('${room.room_id}', '${this.escapeHtml(room.room_name)}')">
                <div class="chat-list-avatar">
                    <i class="bi ${room.room_type === 'DM' ? 'bi-person' : 'bi-people'}"></i>
                </div>
                <div class="chat-list-info">
                    <div class="chat-list-name">${this.escapeHtml(room.room_name)}</div>
                    <div class="chat-list-preview">${this.escapeHtml(room.last_message || '')}</div>
                </div>
                <div class="chat-list-meta">
                    ${room.unread_count > 0 ? `<div class="chat-list-unread">${room.unread_count}</div>` : ''}
                </div>
            </div>
        `).join('');
    }

    async preloadUsers() {
        try {
            const response = await fetch(this.urls.user_list);
            const data = await response.json();
            if (data.status === 'success' && data.users) {
                this.cache.users = data.users;
                this.log.success(`${data.users.length} usuários em cache`);
            }
        } catch (error) {
            this.log.warn('Falha no preload de usuários:', error);
        }
    }

    async preloadTasks() {
        try {
            const response = await fetch(this.urls.task_list);
            const data = await response.json();
            if (data.status === 'success' && data.tasks) {
                this.cache.tasks = data.tasks;
                this.log.success(`${data.tasks.length} tarefas em cache`);
            }
        } catch (error) {
            this.log.warn('Falha no preload de tarefas:', error);
        }
    }

    // ==================== UTILITY METHODS ====================
    
    bindElement(id, event, handler) {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener(event, handler.bind(this));
            return true;
        } else {
            this.log.debug(`Elemento opcional não encontrado: ${id}`);
            return false;
        }
    }

    waitForDOM() {
        return new Promise(resolve => {
            if (document.readyState === 'complete' || document.readyState === 'interactive') {
                resolve();
            } else {
                window.addEventListener('DOMContentLoaded', resolve);
            }
        });
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) bsModal.hide();
        }
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    getCurrentUsername() {
        const script = document.getElementById('json-username');
        try {
            return script ? JSON.parse(script.textContent) : '';
        } catch {
            return '';
        }
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type = 'info') {
        // Remove notificação anterior
        const existing = document.querySelector('.chat-notification');
        if (existing) existing.remove();

        const notification = document.createElement('div');
        notification.className = `chat-notification notification-${type}`;
        notification.innerHTML = `
            <i class="bi bi-${this.getNotificationIcon(type)} me-2"></i>
            <span>${message}</span>
        `;
        notification.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 9999;
            background: var(--bs-${type === 'info' ? 'primary' : type}); color: white;
            padding: 12px 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            animation: slideInRight 0.3s ease-out; max-width: 300px;
        `;

        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle-fill',
            'error': 'exclamation-circle-fill',
            'warning': 'exclamation-triangle-fill',
            'info': 'info-circle-fill'
        };
        return icons[type] || 'info-circle-fill';
    }

    dispatchEvent(name, detail) {
        const event = new CustomEvent(name, { detail });
        document.dispatchEvent(event);
    }

    handleCriticalError(message) {
        this.log.error(`ERRO CRÍTICO: ${message}`);
        
        const errorDiv = document.createElement('div');
        errorDiv.innerHTML = `
            <div style="position: fixed; top: 20px; right: 20px; z-index: 999999; 
                        background: #dc3545; color: white; padding: 15px; border-radius: 8px; 
                        max-width: 300px; font-family: system-ui;">
                <strong>❌ Erro no Chat</strong>
                <p style="margin: 8px 0; font-size: 13px;">${message}</p>
                <button onclick="location.reload()" style="background: rgba(255,255,255,0.2); 
                        border: 1px solid rgba(255,255,255,0.3); color: white; 
                        padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                    🔄 Recarregar
                </button>
            </div>
        `;
        
        document.body.appendChild(errorDiv);
        
        // Dispara evento de emergência
        this.dispatchEvent('chatEmergencyReady', { error: message });
        
        return null;
    }

    renderEmptyState(container, icon, title, subtitle) {
        container.innerHTML = `
            <div class="empty-state text-center p-4">
                <i class="bi bi-${icon}" style="font-size: 2rem; color: var(--text-muted);"></i>
                <p class="text-muted mt-2">${title}</p>
                <small>${subtitle}</small>
            </div>
        `;
    }

    renderErrorState(container, message, retryCallback) {
        container.innerHTML = `
            <div class="error-state text-center p-4">
                <i class="bi bi-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
                <p class="text-muted mt-2">${message}</p>
                <button class="btn btn-sm btn-outline-warning mt-2" 
                        onclick="${retryCallback?.name ? `chatManager.${retryCallback.name}()` : 'location.reload()'}">
                    <i class="bi bi-arrow-clockwise"></i> Tentar Novamente
                </button>
            </div>
        `;
    }

    // ==================== PLACEHOLDER METHODS ====================
    
    shareScreen() {
        this.showNotification('Compartilhamento de tela não implementado', 'info');
    }

    createPoll() {
        this.showNotification('Criação de enquetes não implementada', 'info');
    }

    showConnectionError(message) {
        const errorContainer = document.getElementById('chat-connection-error') || this.createConnectionErrorElement();
        
        errorContainer.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <span>${message}</span>
                <button class="btn btn-sm btn-outline-light" onclick="chatManager.manualReconnect()">
                    <i class="bi bi-arrow-clockwise"></i> Reconectar
                </button>
            </div>
        `;
        errorContainer.style.display = 'block';
    }

    createConnectionErrorElement() {
        const errorDiv = document.createElement('div');
        errorDiv.id = 'chat-connection-error';
        errorDiv.className = 'alert alert-warning mb-2';
        errorDiv.style.cssText = 'display: none; margin: 10px; font-size: 12px;';
        
        const chatContainer = document.getElementById('chat-dialog-content');
        if (chatContainer) {
            chatContainer.insertBefore(errorDiv, chatContainer.firstChild);
        }
        
        return errorDiv;
    }

    hideConnectionError() {
        const errorContainer = document.getElementById('chat-connection-error');
        if (errorContainer) {
            errorContainer.style.display = 'none';
        }
    }   

    // ==================== CONNECTION STATUS ====================

    updateConnectionStatus(status) {
        const statusIndicator = document.querySelector('.status-indicator');
        const lastSeen = document.querySelector('.last-seen');
        
        if (statusIndicator) {
            // Remove todas as classes de status
            statusIndicator.classList.remove('online', 'offline', 'connecting', 'error');
            
            // Adiciona a classe correspondente
            switch (status) {
                case 'online':
                    statusIndicator.classList.add('online');
                    if (lastSeen) lastSeen.textContent = 'Online';
                    break;
                case 'offline':
                    statusIndicator.classList.add('offline');
                    if (lastSeen) lastSeen.textContent = 'Offline';
                    break;
                case 'connecting':
                    statusIndicator.classList.add('connecting');
                    if (lastSeen) lastSeen.textContent = 'Conectando...';
                    break;
                case 'error':
                    statusIndicator.classList.add('error');
                    if (lastSeen) lastSeen.textContent = 'Erro de conexão';
                    break;
                default:
                    statusIndicator.classList.add('offline');
            }
        }
        
        this.log.debug(`Status de conexão atualizado: ${status}`);
    }


}

// ==================== GLOBAL SETUP ====================
// Funções globais para compatibilidade com o template
window.toggleChatListSidebar = () => {
    if (window.chatManager) {
        window.chatManager.toggleChatListSidebar();
    }
};

window.openChatDialog = (roomId, roomName) => {
    if (window.chatManager) {
        window.chatManager.openChatDialog(roomId, roomName);
    }
};

// ==================== LIMPEZA GLOBAL ====================

// Limpa recursos quando a página é fechada
window.addEventListener('beforeunload', () => {
    if (window.chatManager) {
        window.chatManager.cleanupWebSockets();
    }
});

// Limpa recursos quando a aba perde o foco
document.addEventListener('visibilitychange', () => {
    if (document.hidden && window.chatManager) {
        // Opcional: pausa reconexões quando a aba não está ativa
        window.chatManager.pauseReconnections = true;
    } else if (window.chatManager) {
        window.chatManager.pauseReconnections = false;
    }
});




console.log('✅ Sistema de chat com controle de loop inicializado');
console.log('✅ ChatManager v4.3 - Refatorado para template Django');

// Exporta o ChatManager para o objeto global (window)
window.ChatManager = ChatManager;