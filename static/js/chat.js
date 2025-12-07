
/**
 * Sistema de Chat Avançado v4.3 - Compatível com template Django
 * Com funcionalidades completas: troca de conversas, envio de arquivos, busca global
 */

class ChatManager {
    constructor(urls, currentUserId) {
        console.log('🚀 ChatManager v4.3 - Inicializando para template Django...');

        // Configuração de debug
        this.debugMode = localStorage.getItem('chat-debug-mode') === 'true';
        
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
            // URLs do template Django
            active_room_list: urls.active_room_list || '/api/chat/rooms/',
            user_list: urls.user_list || '/api/chat/users/',
            task_list: urls.task_list || '/api/tasks/',
            start_dm_base: urls.start_dm_base || '/api/chat/start-dm/0/',
            create_group_url: urls.create_group_url || '/api/chat/create-group/',
            get_task_chat_base: urls.get_task_chat_base || '/api/chat/task/0/',
            upload_file_url: urls.upload_file_url || '/api/chat/upload/',
            search_messages_url: urls.search_messages_url || '/api/chat/search/',
            // URLs do template específicas
            ws_base: urls.ws_base || '/wss/chat/',
            history_base: urls.history_base || '/chat/api/history/',
            // Adicionadas pelo template
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
        
        // Sistema de som
        this.soundEnabled = localStorage.getItem('chat-sound-enabled') !== 'false';
        this.soundInitialized = false;
        this.audioContext = null;
        this.audioElements = {};
        
        // Cache
        this.cache = { 
            users: [], 
            tasks: [], 
            rooms: [],
            messages: {}, // Cache de mensagens por sala
            searchResults: {} // Cache de resultados de busca
        };
        
        // Upload state
        this.uploadQueue = [];
        this.isUploading = false;
        this.maxFileSize = 10 * 1024 * 1024; // 10MB
        
        // Search state
        this.currentSearchQuery = '';
        this.searchResults = [];
        
        // Drag state
        this.dragData = { isDragging: false, offsetX: 0, offsetY: 0 };
        
        // Inicialização
        this.initialize();
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
        // Configura botão flutuante
        const floatingBtn = document.getElementById('chat-modal-trigger');
        if (floatingBtn) {
            floatingBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleChatListSidebar();
            });
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
        const closeBtn = document.querySelector('.chat-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleChatListSidebar();
            });
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
        const globalSearchExecute = document.getElementById('global-search-execute');
        const globalSearchResults = document.getElementById('global-search-results');
        
        if (globalSearchBtn && globalSearchContainer) {
            globalSearchBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const isVisible = globalSearchContainer.style.display !== 'none';
                globalSearchContainer.style.display = isVisible ? 'none' : 'block';
                
                if (!isVisible && globalSearchInput) {
                    setTimeout(() => globalSearchInput.focus(), 100);
                }
            });
        }
        
        if (globalSearchExecute && globalSearchInput) {
            globalSearchExecute.addEventListener('click', () => {
                const query = globalSearchInput.value.trim();
                if (query) {
                    this.performGlobalSearch(query, globalSearchResults);
                }
            });
            
            globalSearchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const query = globalSearchInput.value.trim();
                    if (query) {
                        this.performGlobalSearch(query, globalSearchResults);
                    }
                }
            });
        }
    }

    async performGlobalSearch(query, resultsContainer) {
        if (!query || query.length < 2) {
            resultsContainer.innerHTML = `
                <div class="text-center p-3 text-muted">
                    <i class="bi bi-search"></i>
                    <p>Digite pelo menos 2 caracteres</p>
                </div>
            `;
            return;
        }
        
        resultsContainer.innerHTML = `
            <div class="text-center p-3">
                <div class="spinner-border spinner-border-sm"></div>
                <p class="mt-2 mb-0">Buscando "${query}" em todas as conversas...</p>
            </div>
        `;
        
        try {
            if (!this.urls.search_messages_url) {
                throw new Error('URL de busca não configurada');
            }
            
            const response = await fetch(this.urls.search_messages_url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ query, user_id: this.currentUserId })
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            if (data.status === 'success' && data.results?.length > 0) {
                this.displayGlobalSearchResults(data.results, query, resultsContainer);
            } else {
                resultsContainer.innerHTML = `
                    <div class="text-center p-3 text-muted">
                        <i class="bi bi-search"></i>
                        <p>Nenhum resultado para "${query}"</p>
                    </div>
                `;
            }
            
        } catch (error) {
            this.log.error('Erro na busca global:', error);
            resultsContainer.innerHTML = `
                <div class="text-center p-3 text-danger">
                    <i class="bi bi-exclamation-circle"></i>
                    <p>Erro na busca</p>
                    <small>${error.message}</small>
                </div>
            `;
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
            // Verifica cache primeiro
            if (this.cache.messages[roomId]) {
                this.log.debug(`Usando cache para sala ${roomId}`);
                this.renderMessages(this.cache.messages[roomId]);
                return;
            }

            // Usa URL do template ou padrão
            const historyUrl = this.urls.history_base 
                ? `${this.urls.history_base}${roomId}/`
                : `/chat/api/history/${roomId}/`;
                
            const response = await fetch(historyUrl);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            if (data.status === 'success' && data.messages?.length > 0) {
                // Cache as mensagens
                this.cache.messages[roomId] = data.messages;
                this.renderMessages(data.messages);
                this.log.success(`${data.messages.length} mensagens carregadas`);
            } else {
                this.renderEmptyChatState();
            }
        } catch (error) {
            this.log.error('Erro ao carregar histórico:', error);
            this.renderErrorChatState(error.message);
        }
    }

    renderMessages(messages) {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return;
        
        // Limpa o chat
        chatLog.innerHTML = '';
        
        if (messages.length === 0) {
            this.renderEmptyChatState();
            return;
        }
        
        // Agrupa mensagens por data
        const groupedMessages = this.groupMessagesByDate(messages);
        
        // Renderiza cada grupo
        Object.entries(groupedMessages).forEach(([date, dayMessages]) => {
            // Adiciona separador de data
            const dateElement = document.createElement('div');
            dateElement.className = 'date-separator';
            dateElement.innerHTML = `
                <div class="date-line"></div>
                <span class="date-text">${this.formatDateHeader(date)}</span>
                <div class="date-line"></div>
            `;
            chatLog.appendChild(dateElement);
            
            // Adiciona mensagens do dia
            dayMessages.forEach(message => {
                const messageElement = this.createMessageElement(message);
                chatLog.appendChild(messageElement);
            });
        });
        
        // Rola para a última mensagem
        this.scrollToBottom();
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
        messageDiv.dataset.messageId = data.id;
        
        const timestamp = new Date(data.timestamp).toLocaleTimeString('pt-BR', {
            hour: '2-digit', 
            minute: '2-digit'
        });
        
        let content = '';
        
        // Verifica tipo de mensagem
        if (data.message_type === 'file') {
            content = this.renderFileMessage(data);
        } else {
            content = this.renderTextMessage(data);
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">${this.escapeHtml(data.username || 'Usuário')}</span>
                    <span class="message-time">${timestamp}</span>
                </div>
                ${content}
                ${data.edited ? '<small class="text-muted ms-2"><i class="bi bi-pencil"></i> editado</small>' : ''}
            </div>
        `;
        
        return messageDiv;
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
            
            if (data.status === 'success') {
                // Envia via WebSocket se conectado
                if (this.websocket && this.isConnected) {
                    this.websocket.send(JSON.stringify({
                        type: 'file_message',
                        file_data: data.file_data,
                        room_id: this.currentRoom,
                        timestamp: new Date().toISOString()
                    }));
                }
                
                // Atualiza cache local
                this.addMessageToCache(data.message);
                
                // Atualiza interface
                this.displayMessage(data.message);
                
                this.showNotification(`Arquivo ${file.name} enviado`, 'success');
            } else {
                throw new Error(data.error || 'Erro no upload');
            }
            
        } finally {
            // Remove indicador de upload
            this.hideUploadIndicator(file.name);
        }
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
        // Cria modal para visualização de imagem
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'imageViewModal';
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Visualizar Imagem</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-center">
                        <img src="${url}" class="img-fluid" alt="Imagem">
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
        bsModal.show();
        
        // Remove o modal quando fechar
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    // ==================== WEBSOCKET ====================
    
    async connectWebSocket(roomId) {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = this.urls.ws_base 
            ? `${protocol}//${window.location.host}${this.urls.ws_base}${roomId}/`
            : `${protocol}//${window.location.host}/wss/chat/${roomId}/`;
        
        this.log.info(`Conectando WebSocket: ${wsUrl}`);
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.isConnected = true;
                this.log.success('WebSocket conectado');
                
                // Atualiza status no header
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
                this.log.warn(`WebSocket desconectado: ${e.code} ${e.reason}`);
                
                // Atualiza status no header
                this.updateConnectionStatus('offline');
                
                // Tenta reconectar após 5 segundos
                if (this.currentRoom === roomId) {
                    setTimeout(() => {
                        this.log.info('Tentando reconectar WebSocket...');
                        this.connectWebSocket(roomId);
                    }, 5000);
                }
            };
            
            this.websocket.onerror = (error) => {
                this.log.error('Erro WebSocket:', error);
                this.updateConnectionStatus('error');
            };
            
        } catch (error) {
            this.log.error('Falha ao conectar WebSocket:', error);
            this.updateConnectionStatus('error');
        }
    }

    updateConnectionStatus(status) {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.header-status .last-seen');
        
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator';
            statusIndicator.classList.add(status);
        }
        
        if (statusText) {
            const statusMessages = {
                'online': 'Online agora',
                'offline': 'Offline',
                'error': 'Erro de conexão',
                'connecting': 'Conectando...'
            };
            statusText.textContent = statusMessages[status] || '...';
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'new_message':
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
                
            default:
                this.log.debug('Mensagem WebSocket não tratada:', data);
        }
    }

    handleNewMessage(data) {
        // Verifica se a mensagem é para a sala atual
        if (data.room_id && data.room_id !== this.currentRoom) {
            // Atualiza badge de não lidas para outras salas
            this.updateUnreadBadge(data.room_id);
            return;
        }
        
        // Adiciona ao cache
        this.addMessageToCache(data);
        
        // Exibe na interface
        this.displayMessage(data);
        
        // Toca som de notificação se não for própria mensagem
        if (data.user_id != this.currentUserId) {
            this.playNotificationSound('message');
            
            // Mostra notificação se o chat não está em foco
            if (document.hidden || this.isMinimized) {
                this.showDesktopNotification(`${data.username}: ${data.message?.substring(0, 50)}...`);
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
        if (!chatLog) return;
        
        // Remove estados vazios
        chatLog.querySelectorAll('.welcome-state, .loading-state').forEach(el => el.remove());
        
        const messageElement = this.createMessageElement(data);
        chatLog.appendChild(messageElement);
        this.scrollToBottom();
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
        const modalContent = document.getElementById('chat-info-content');
        if (!modalContent) return;
        
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
        
        const modal = new bootstrap.Modal(document.getElementById('chatInfoModal'));
        modal.show();
    }

    countFilesInRoom() {
        if (!this.cache.messages[this.currentRoom]) return 0;
        return this.cache.messages[this.currentRoom].filter(msg => 
            msg.message_type === 'file'
        ).length;
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
        
        // Limpa estado
        this.isMinimized = false;
        this.currentRoom = null;
        this.currentRoomName = null;
        
        // Desconecta WebSocket
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        this.log.info('Chat fechado');
        this.showNotification('Chat fechado', 'info');
    }

    toggleChatListSidebar(show = null) {
        const overlay = document.getElementById('chatOverlay');
        const sidebar = document.getElementById('chatListContainer');
        
        if (!overlay || !sidebar) {
            this.log.warn('Elementos da sidebar não encontrados');
            return;
        }
        
        const shouldShow = show !== null ? show : !sidebar.classList.contains('active');
        
        sidebar.classList.toggle('active', shouldShow);
        overlay.classList.toggle('active', shouldShow);
        
        // Se está mostrando, carrega lista de conversas
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

// Exporta a classe
window.ChatManager = ChatManager;

console.log('✅ ChatManager v4.3 - Refatorado para template Django');

