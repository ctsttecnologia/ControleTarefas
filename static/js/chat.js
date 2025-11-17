/**
 * Sistema de Chat - Gerenciador Principal
 * Responsável por controle de UI, WebSocket e notificações
 */
class ChatManager {

    constructor() {
        
        this.currentRoom = null;
        this.websocket = null;
        this.isMinimized = false;
        this.isConnected = false;
        
        // URLs da aplicação (injetadas do Django)
        this.urls = window.chatUrls || {};
        console.log('ChatManager inicializado com URLs:', this.urls);
        
        this.initializeEventListeners();
        this.initializeNotificationSocket();
        this.loadActiveRoomList();
    }

    /**
     * Lida com o upload de imagem selecionada pelo usuário.
     * Este método agora é parte da classe ChatManager.
     */
    async handleImageUpload(event) {
        const file = event.target.files[0]; // Pega o primeiro arquivo selecionado

        if (file) {
            // Verifica o tipo de arquivo
            if (!file.type.startsWith('image/')) {
                this.showNotification('Por favor, selecione um arquivo de imagem.', 'warning');
                return;
            }

            // Verifica o tamanho do arquivo (ex: limite de 5MB)
            const maxSize = 5 * 1024 * 1024; // 5 MB
            if (file.size > maxSize) {
                this.showNotification('A imagem é muito grande. Tamanho máximo é 5MB.', 'warning');
                return;
            }

            console.log('Imagem selecionada:', file.name, 'Tamanho:', file.size, 'Tipo:', file.type);

            // Limpa o input imediatamente
            event.target.value = ''; 

            // Mostra um feedback de "enviando"
            this.showNotification('Enviando imagem...', 'info');

            // Chama a nova função de upload
            await this.uploadImage(file);
        }
    }

    /**
     * Faz o upload de um arquivo de imagem para o servidor.
     * Este método agora é parte da classe ChatManager.
     * @param {File} file - O arquivo de imagem a ser enviado.
     */
    async uploadImage(file) {
        if (!this.urls.upload_image_url) {
            console.error('URL de upload de imagem não definida em chatUrls');
            this.showError('Não foi possível enviar a imagem (configuração faltando).');
            return;
        }

        const formData = new FormData();
        formData.append('image_file', file); // 'image_file' será o nome no request do Django
        
        try {
            const response = await fetch(this.urls.upload_image_url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(), // Reutiliza seu método de pegar o token
                    'X-Requested-With': 'XMLHttpRequest' // Útil para o Django saber que é AJAX
                },
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                console.log('Imagem enviada com sucesso:', data.image_url);
                
                // AGORA SIM, enviamos a URL pelo WebSocket
                this.sendImageMessage(data.image_url);
            } else {
                console.error('Erro no servidor ao enviar imagem:', data.error);
                this.showError(data.error || 'Erro ao enviar imagem.');
            }
        } catch (error) {
            console.error('Erro de rede ao enviar imagem:', error);
            this.showError('Erro de rede ao enviar imagem.');
        }
    }
    
    /**
     * Inicializa todos os event listeners do chat
     * Agora este método contém *apenas* os listeners,
     * e não as definições de outros métodos.
     */
    initializeEventListeners() {
        console.log('Inicializando event listeners do chat...');

        // Botão de anexar imagem
        const attachImageBtn = document.getElementById('attach-image-btn');
        if (attachImageBtn) {
            attachImageBtn.addEventListener('click', () => {
                const imageUploadInput = document.getElementById('image-upload-input');
                if (imageUploadInput) {
                    imageUploadInput.click(); // Simula o clique no input de arquivo escondido
                }
            });
        }

        // Input de upload de imagem
        const imageUploadInput = document.getElementById('image-upload-input');
        if (imageUploadInput) {
            // Agora isso vai funcionar, pois 'this.handleImageUpload' existe
            imageUploadInput.addEventListener('change', (event) => this.handleImageUpload(event));
        }
        
        // Botão de enviar mensagem
        const submitBtn = document.getElementById('chat-message-submit');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => this.sendMessage());
        } else {
            console.warn('Botão de enviar mensagem não encontrado');
        }
        
        // Enter para enviar mensagem
        const messageInput = document.getElementById('chat-message-input');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Auto-resize da textarea
            messageInput.addEventListener('input', () => this.autoResizeTextarea());
        }

        // Botões de controle da janela
        const minimizeBtn = document.getElementById('minimize-chat-btn');
        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', () => this.toggleMinimize());
        }
        
        const closeBtn = document.getElementById('close-dialog-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeChat());
        }
        
        // Drag da janela
        this.makeDraggable();
        
        // Modal de nova conversa
        this.initializeModalListeners();
        
        console.log('Event listeners do chat inicializados com sucesso');
    }

    /**
     * Inicializa listeners do modal de nova conversa
     */
    initializeModalListeners() {
        const modal = document.getElementById('novaConversaModal');
        if (modal) {
            modal.addEventListener('show.bs.modal', () => this.loadModalData());
            
            // Form de criar grupo
            const groupForm = document.getElementById('create-group-form');
            if (groupForm) {
                groupForm.addEventListener('submit', (e) => this.createGroupChat(e));
            }

            // Busca em tempo real
            const dmSearch = document.getElementById('dm-user-search');
            if (dmSearch) {
                dmSearch.addEventListener('input', (e) => this.filterUsers(e.target.value));
            }

            const taskSearch = document.getElementById('task-search');
            if (taskSearch) {
                taskSearch.addEventListener('input', (e) => this.filterTasks(e.target.value));
            }
        } else {
            console.warn('Modal de nova conversa não encontrado');
        }
    }

    /**
     * Carrega dados para o modal (usuários e tarefas)
     */
    async loadModalData() {
        await this.loadUsersForDM();
        await this.loadUsersForGroup();
        await this.loadTasks();
    }

    /**
     * Carrega usuários para conversas individuais
     */
    async loadUsersForDM() {
        try {
            if (!this.urls.user_list) {
                console.error('URL de lista de usuários não definida');
                this.showErrorInModal('dm-user-list-container', 'URL de usuários não configurada');
                return;
            }

            console.log('Carregando usuários para DM...');
            const response = await fetch(this.urls.user_list);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            const container = document.getElementById('dm-user-list-container');
            if (container && data.users) {
                this.allUsers = data.users;
                this.renderUsers(this.allUsers);
                console.log(`${data.users.length} usuários carregados para DM`);
            }
        } catch (error) {
            console.error('Erro ao carregar usuários:', error);
            this.showErrorInModal('dm-user-list-container', 'Erro ao carregar lista de usuários');
        }
    }
    
    /**
     * Mostra erro no container do modal
     */
    showErrorInModal(containerId, message) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="error-state text-center p-4">
                    <i class="bi bi-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
                    <p class="text-muted mt-2">${message}</p>
                    <button class="btn btn-sm btn-outline-warning mt-2" onclick="window.chatManager.loadModalData()">
                        <i class="bi bi-arrow-clockwise"></i> Tentar Novamente
                    </button>
                </div>
            `;
        }
    }

    /**
     * Renderiza lista de usuários
     */
    renderUsers(users) {
        const container = document.getElementById('dm-user-list-container');
        if (!container) return;

        if (users.length === 0) {
            container.innerHTML = `
                <div class="empty-state text-center p-4">
                    <i class="bi bi-person-x" style="font-size: 2rem;"></i>
                    <p class="text-muted mt-2">Nenhum usuário encontrado</p>
                </div>
            `;
            return;
        }

        container.innerHTML = users.map(user => `
            <div class="user-list-item" onclick="window.chatManager.startDM(${user.id})">
                <div class="user-avatar">
                    <i class="bi bi-person-fill"></i>
                </div>
                <div class="user-info">
                    <div class="user-name">${this.escapeHtml(user.name)}</div>
                    <div class="user-email">${this.escapeHtml(user.email)}</div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Filtra usuários na busca
     */
    filterUsers(searchTerm) {
        if (!this.allUsers) return;
        
        const filteredUsers = this.allUsers.filter(user => 
            user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            user.email.toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        this.renderUsers(filteredUsers);
    }

    /**
     * Carrega usuários para seleção em grupos
     */
    async loadUsersForGroup() {
        try {
            if (!this.urls.user_list) {
                console.error('URL de lista de usuários não definida');
                return;
            }

            console.log('Carregando usuários para grupo...');
            const response = await fetch(this.urls.user_list);
            const data = await response.json();
            
            const select = document.getElementById('group-participants-select');
            if (select && data.users) {
                select.innerHTML = data.users.map(user => `
                    <option value="${user.id}">
                        ${this.escapeHtml(user.name)} (${this.escapeHtml(user.email)})
                    </option>
                `).join('');
                console.log(`${data.users.length} usuários carregados para grupo`);
            }
        } catch (error) {
            console.error('Erro ao carregar usuários para grupo:', error);
        }
    }

    /**
     * Carrega tarefas para o chat
     */
    async loadTasks() {
        try {
            if (!this.urls.task_list) {
                console.error('URL de lista de tarefas não definida');
                this.showErrorInModal('task-list-container', 'URL de tarefas não configurada');
                return;
            }

            console.log('Carregando tarefas...');
            const response = await fetch(this.urls.task_list);
            const data = await response.json();
            
            const container = document.getElementById('task-list-container');
            if (container && data.tasks) {
                this.allTasks = data.tasks;
                this.renderTasks(this.allTasks);
                console.log(`${data.tasks.length} tarefas carregadas`);
            }
        } catch (error) {
            console.error('Erro ao carregar tarefas:', error);
            this.showErrorInModal('task-list-container', 'Erro ao carregar lista de tarefas');
        }
    }

    /**
     * Renderiza lista de tarefas
     */
    renderTasks(tasks) {
        const container = document.getElementById('task-list-container');
        if (!container) return;

        if (tasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state text-center p-4">
                    <i class="bi bi-check-square" style="font-size: 2rem;"></i>
                    <p class="text-muted mt-2">Nenhuma tarefa encontrada</p>
                </div>
            `;
            return;
        }

        container.innerHTML = tasks.map(task => `
            <div class="task-list-item" onclick="window.chatManager.openTaskChat(${task.id})">
                <div class="task-icon">
                    <i class="bi bi-check-square-fill"></i>
                </div>
                <div class="task-info">
                    <div class="task-title">${this.escapeHtml(task.titulo)}</div>
                    <div class="task-details">
                        <span class="task-status badge ${this.getStatusBadgeClass(task.status)}">${task.status}</span>
                        <span class="task-priority badge ${this.getPriorityBadgeClass(task.prioridade)}">${task.prioridade}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Filtra tarefas na busca
     */
    filterTasks(searchTerm) {
        if (!this.allTasks) return;
        
        const filteredTasks = this.allTasks.filter(task => 
            task.titulo.toLowerCase().includes(searchTerm.toLowerCase()) ||
            task.descricao.toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        this.renderTasks(filteredTasks);
    }

    /**
     * Inicia uma conversa individual
     */
    async startDM(userId) {
        try {
            if (!this.urls.start_dm_base) {
                console.error('URL base para DM não definida');
                this.showNotification('Configuração de URL incompleta', 'error');
                return;
            }
            // =Setting .replace('0', userId);
            const finalUrl = this.urls.start_dm_base.replace('0', userId);
            
            console.log(`Iniciando DM com usuário ${userId} em ${finalUrl}...`); 

            const response = await fetch(finalUrl, {

                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log(`DM criada: ${data.room_id}`);
                this.openChatDialog(data.room_id, data.room_name);
                this.hideModal('novaConversaModal');
                this.showNotification('Conversa iniciada com sucesso!', 'success');
            } else {
                console.error('Erro ao criar DM:', data.error);
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Erro ao iniciar DM:', error);
            this.showNotification('Erro ao iniciar conversa', 'error');
        }
    }

    /**
     * Cria um grupo de chat
     */
    async createGroupChat(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const name = formData.get('name');
        const participants = formData.getAll('participants');
        
        if (!name || participants.length === 0) {
            this.showNotification('Preencha todos os campos obrigatórios', 'warning');
            return;
        }

        try {
            if (!this.urls.create_group_url) {
                console.error('URL de criação de grupo não definida');
                return;
            }

            this.showLoading('Criando grupo...');

            const response = await fetch(this.urls.create_group_url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.openChatDialog(data.room_id, data.room_name);
                this.hideModal('novaConversaModal');
                this.showNotification('Grupo criado com sucesso!', 'success');
                
                // Limpa o formulário
                event.target.reset();
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Erro ao criar grupo:', error);
            this.showNotification('Erro ao criar grupo', 'error');
        }
    }

    /**
     * Abre chat de tarefa
     */
    async openTaskChat(taskId) {
        try {
            if (!this.urls.get_task_chat_base) { // O valor disto é '/chat/task/0/'
                console.error('URL base para chat de tarefa não definida');
                return;
            }

            // Substitua o '0' pelo ID real

            const finalUrl = this.urls.get_task_chat_base.replace('0', taskId);

            this.showLoading('Abrindo chat da tarefa...');

            const response = await fetch(finalUrl); // Use a 'finalUrl' corrigida
            const data = await response.json();
            
            if (data.status === 'success') {
                this.openChatDialog(data.room_id, data.room_name);
                this.hideModal('novaConversaModal');
                this.showNotification('Chat da tarefa aberto!', 'success');
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Erro ao abrir chat de tarefa:', error);
            this.showNotification('Erro ao acessar chat da tarefa', 'error');
        }
    }

    /**
     * Abre diálogo do chat - CORRIGIDO
     */
    openChatDialog(roomId, roomName) {
        const container = document.getElementById('chat-draggable-container');
        const title = document.getElementById('chat-dialog-header-title');
        const content = document.getElementById('chat-dialog-content');
        
        if (container && title && content) {
            // Garante que o container está visível e restaurado
            container.style.display = 'flex';
            this.isMinimized = false;
            
            // Mostra o conteúdo (caso estivesse minimizado)
            content.style.display = 'flex';
            container.classList.remove('minimized');
            
            // Restaura altura padrão
            container.style.height = '500px';
            container.style.minHeight = '400px';
            
            // Atualiza título
            title.textContent = roomName || 'Chat';
        }
        
        // Sua lógica existente para carregar o chat...
        this.currentRoom = roomId;
        this.loadChatHistory(roomId);
        this.connectWebSocket(roomId);
    }

    /**
     * Conecta ao WebSocket
     */
    connectWebSocket(roomId) {
        if (this.websocket) {
            this.websocket.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${roomId}/`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('✅ WebSocket conectado para sala:', roomId);
            this.isConnected = true;
            this.showNotification('Conectado ao chat', 'success');
        };
        
        this.websocket.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                this.displayMessage(data);
            } catch (error) {
                console.error('Erro ao processar mensagem WebSocket:', error);
            }
        };
        
        this.websocket.onclose = (e) => {
            console.log('🔴 WebSocket desconectado:', e.code, e.reason);
            this.isConnected = false;
            
            // Tentar reconectar se não foi um fechamento normal
            if (e.code !== 1000 && this.currentRoom) {
                setTimeout(() => {
                    if (this.currentRoom) {
                        this.connectWebSocket(this.currentRoom);
                    }
                }, 3000);
            }
        };
        
        this.websocket.onerror = (error) => {
            console.error('Erro WebSocket:', error);
            this.showNotification('Erro de conexão com o chat', 'error');
        };
    }

    /**
     * Envia mensagem via WebSocket
     */
    sendMessage() {
        const input = document.getElementById('chat-message-input');
        const message = input ? input.value.trim() : '';
        
        if (!message) {
            this.showNotification('Digite uma mensagem', 'warning');
            return;
        }

        if (!this.websocket || !this.isConnected) {
            this.showNotification('Conexão não disponível. Tentando reconectar...', 'error');
            if (this.currentRoom) {
                this.connectWebSocket(this.currentRoom);
            }
            return;
        }

        try {
            this.websocket.send(JSON.stringify({
                'message': message
            }));

            if (input) {
                input.value = '';
                this.autoResizeTextarea();
            }
        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            this.showNotification('Erro ao enviar mensagem', 'error');
        }
    }

    /**
     * Envia uma URL de imagem via WebSocket
     */
    sendImageMessage(imageUrl) {
        if (!this.websocket || !this.isConnected) {
            this.showError('Conexão não disponível.');
            return;
        }

        try {
            this.websocket.send(JSON.stringify({
                'type': 'chat_message',
                'message': '', // Mensagem de texto vazia
                'image_url': imageUrl // Envia a URL da imagem
            }));
        } catch (error) {
            console.error('Erro ao enviar mensagem de imagem:', error);
            this.showError('Erro ao enviar imagem.');
        }
    }

    /**
     * Exibe mensagem no chat
     */
    displayMessage(data) {
        const chatLog = document.getElementById('chat-log');
        if (!chatLog) return;
        
        // Remove estado de boas-vindas se existir
        const welcomeState = chatLog.querySelector('.welcome-state');
        if (welcomeState) {
            welcomeState.remove();
        }

        // Remove estado vazio se existir
        const emptyState = chatLog.querySelector('.empty-chat-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        const messageElement = this.createMessageElement(data);
        chatLog.appendChild(messageElement);
        chatLog.scrollTop = chatLog.scrollHeight;
        
        // Notificação para mensagens de outros usuários
        if (data.username !== this.getCurrentUsername()) {
            
            // Define um texto de fallback para a notificação
            let notificationText = data.message;
            if (!notificationText && data.image_url) {
                notificationText = '[Enviou uma imagem]';
            }

            this.showDesktopNotification(data.username, notificationText);
        }
    }

    /**
     * Cria elemento de mensagem
     */
    createMessageElement(data) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${data.username === this.getCurrentUsername() ? 'own-message' : 'other-message'}`;
        
        const timestamp = new Date(data.timestamp).toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">${this.escapeHtml(data.username)}</span>
                    <span class="message-time">${timestamp}</span>
                </div>
                <div class="message-text">${this.escapeHtml(data.message)}</div>
                ${data.image_url ? `<img src="${data.image_url}" class="message-image" alt="Imagem da mensagem">` : ''}
            </div>
        `;
        
        return messageDiv;
    }

    /**
     * Carrega histórico do chat
     */
    async loadChatHistory(roomId) {
        try {
            const response = await fetch(`/chat/api/history/${roomId}/`);
            const data = await response.json();
            
            const chatLog = document.getElementById('chat-log');
            if (!chatLog) return;
            
            if (data.status === 'success' && data.messages.length > 0) {
                chatLog.innerHTML = '';
                data.messages.forEach(msg => this.displayMessage(msg));
            } else {
                chatLog.innerHTML = `
                    <div class="empty-chat-state">
                        <i class="bi bi-chat-left-text" style="font-size: 2rem;"></i>
                        <p>Nenhuma mensagem ainda</p>
                        <small>Seja o primeiro a enviar uma mensagem!</small>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Erro ao carregar histórico:', error);
            this.showNotification('Erro ao carregar histórico do chat', 'error');
        }
    }

    /**
     * Minimiza/restaura janela do chat - CORRIGIDO
     */
    toggleMinimize() {
        const container = document.getElementById('chat-draggable-container');
        const content = document.getElementById('chat-dialog-content');
        
        if (!container || !content) return;
        
        this.isMinimized = !this.isMinimized;
        
        if (this.isMinimized) {
            // Minimizar: esconde o conteúdo, mantém só o header
            content.style.display = 'none';
            container.classList.add('minimized');
            
            // Ajusta altura para mostrar apenas o header
            container.style.height = '60px';
            container.style.minHeight = '60px';
        } else {
            // Restaurar: mostra o conteúdo novamente
            content.style.display = 'flex';
            container.classList.remove('minimized');
            
            // Restaura altura padrão
            container.style.height = '500px';
            container.style.minHeight = '400px';
        }
    }

    /**
     * Fecha janela do chat
     */
    closeChat() {
        // 1. A função foi chamada?
        console.log('--- DEBUG: 1. closeChat() FOI CHAMADA ---'); 
    
        try {
            const container = document.getElementById('chat-draggable-container');
            
            // 2. O contêiner foi encontrado?
            if (container) {
                console.log('--- DEBUG: 2. Contêiner #chat-draggable-container ENCONTRADO ---');
                
                // 3. Esta é a linha que esconde o chat
                container.style.display = 'none';
                console.log('--- DEBUG: 3. container.style.display foi definido como "none" ---');
                
                container.classList.remove('minimized');
            } else {
                // Se o contêiner não for encontrado, este erro aparecerá
                console.error('--- DEBUG: FALHA CRÍTICA: Contêiner #chat-draggable-container NÃO ENCONTRADO! ---');
                return; 
            }
            
            // --- O resto da sua lógica de limpeza ---
            
            this.isMinimized = false;
            this.currentRoom = null;
            
            const chatLog = document.getElementById('chat-log');
            if (chatLog) {
                chatLog.innerHTML = `
                    <div class="welcome-state">
                        <i class="bi bi-chat-heart" style="font-size: 3rem; color: var(--text-muted); margin-bottom: 1rem;"></i>
                        <p>Selecione uma conversa para começar</p>
                    </div>
                `;
            } else {
                console.warn('--- DEBUG: Aviso: #chat-log não encontrado para limpar. ---');
            }
            
            if (this.websocket) {
                this.websocket.close(1000, 'Usuário fechou o chat');
                this.websocket = null;
                console.log('--- DEBUG: 4. WebSocket fechado. ---');
            }
            
            const messageInput = document.getElementById('chat-message-input');
            if (messageInput) {
                messageInput.value = '';
            }
            
            console.log('--- DEBUG: 5. Função closeChat() CONCLUÍDA ---');

        } catch (error) {
            // 6. Pega qualquer erro inesperado
            console.error('--- DEBUG: ERRO INESPERADO DENTRO DE closeChat():', error);
        }
    }

    /**
     * Toggle da sidebar de conversas
     */
    toggleChatListSidebar() {
        const overlay = document.getElementById('chatOverlay');
        const sidebar = document.getElementById('chatListContainer');
        
        if (!overlay || !sidebar) return;
        
        const isVisible = sidebar.classList.contains('active');
        
        if (isVisible) {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        } else {
            sidebar.classList.add('active');
            overlay.classList.add('active');
        }
    }

    // METODOS AUXILIARES
    /**
     * Esconde modal do Bootstrap
     */
    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }
    }

    /**
     * Obtém token CSRF
     */
    getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }

    /**
     * Obtém username atual
     */
    getCurrentUsername() {
        const usernameElement = document.getElementById('json-username');
        return usernameElement ? usernameElement.textContent : '';
    }

    /**
     * Escape HTML para prevenir XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Mostra notificação
     */
    showNotification(message, type = 'info') {
        // Remove notificação anterior se existir
        const existingNotification = document.querySelector('.chat-notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        const notification = document.createElement('div');
        notification.className = `chat-notification notification-${type}`;
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi ${this.getNotificationIcon(type)} me-2"></i>
                <span>${message}</span>
            </div>
        `;

        document.body.appendChild(notification);

        // Remove automaticamente após 5 segundos
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    /**
     * Ícone para notificação
     */
    getNotificationIcon(type) {
        const icons = {
            'success': 'bi-check-circle-fill',
            'error': 'bi-exclamation-circle-fill',
            'warning': 'bi-exclamation-triangle-fill',
            'info': 'bi-info-circle-fill'
        };
        return icons[type] || 'bi-info-circle-fill';
    }

    /**
     * Mostra estado de carregamento
     */
    showLoading(message = 'Carregando...') {
        this.showNotification(message, 'info');
    }

    /**
     * Mostra erro
     */
    showError(message) {
        this.showNotification(message, 'error');
    }

    /**
     * Notificação desktop
     */
    showDesktopNotification(title, message) {
        if ('Notification' in window) {
            if (Notification.permission === 'granted') {
                new Notification(title, {
                    body: message,
                    icon: '/static/images/favicon.ico' // Certifique-se que este caminho está correto
                });
            } else if (Notification.permission !== 'denied') {
                Notification.requestPermission().then(permission => {
                    if (permission === 'granted') {
                        new Notification(title, {
                            body: message,
                            icon: '/static/images/favicon.ico'
                        });
                    }
                });
            }
        }
    }

    //  (AGORA DENTRO DA CLASSE E SENDO CHAMADA)

    initializeNotificationSocket() {
        // Seu método está correto: ele espera o DOM carregar
        document.addEventListener('DOMContentLoaded', () => {
            
            // 1. Pegue os indicadores persistentes (pontos vermelhos)
            // Lembre-se de adicionar um ID 'header-notification-bell' ao seu sino
            const bellElement = document.getElementById('header-notification-bell');
            const chatButtonElement = document.getElementById('chat-modal-trigger'); // Correto!
            
            const bellIndicator = bellElement ? bellElement.querySelector('.notification-indicator') : null;
            const chatIndicator = chatButtonElement ? chatButtonElement.querySelector('.notification-indicator') : null;

            // 2. Conecte-se ao WebSocket de Notificação
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const notificationSocket = new WebSocket(
                protocol + '//' + window.location.host + '/ws/notifications/'
            );

            notificationSocket.onopen = function(e) {
                console.log('Socket de Notificação conectado.');
            };

            // Usar '=>' aqui é CRUCIAL e está CORRETO.
            // Garante que o 'this' dentro desta função ainda é a classe 'ChatManager'
            notificationSocket.onmessage = (e) => {

                // -----------------------------------------------------------------
                // ADICIONE ESTE CONSOLE.LOG 
                // Este é o log mais importante. Ele dispara ANTES de qualquer
                // 'if' ou 'JSON.parse'. Se isto não aparecer, o problema
                // é no backend.
                console.log("!!! [DEBUG NOTIFICAÇÃO] MENSAGEM CRUA RECEBIDA:", e.data);
                // -----------------------------------------------------------------

                const data = JSON.parse(e.data);
                console.log('Notificação recebida:', data);

                if (data.type === 'new_message') {
                    
                    const notificationTitle = 'Nova Mensagem';
                    // Tente buscar o nome da sala no backend se for fácil, senão o ID está bom.
                    const notificationMessage = `Você tem uma nova mensagem de ${data.sender_username}.`;

                    // 1. CHAMA SEUS ALERTS MOMENTÂNEOS
                    this.showNotification(notificationMessage, 'info'); 
                    this.showDesktopNotification(notificationTitle, notificationMessage);
                    
                    // 2. ATIVA OS INDICADORES PERSISTENTES
                    if (bellIndicator) {
                        bellIndicator.style.display = 'block';
                    }
                    if (chatIndicator) {
                        chatIndicator.style.display = 'block';
                    }
                }
                
                if (data.type === 'new_chat') {
                    this.showNotification(`Você foi adicionado ao chat: ${data.room.name}`, 'info');
                    // Você pode querer recarregar a lista de chats aqui
                }
            };

            notificationSocket.onclose = (e) => {
                console.error('Socket de Notificação fechou inesperadamente.');
            };

            // 3. Lógica para LIMPAR os indicadores
            if (chatButtonElement) {
                chatButtonElement.addEventListener('click', () => {
                    if (chatIndicator) chatIndicator.style.display = 'none';
                    // Também limpa o sino, já que abrir o chat conta como ver as mensagens
                    if (bellIndicator) bellIndicator.style.display = 'none';
                });
            }
            if (bellElement) {
                bellElement.addEventListener('click', () => {
                    if (bellIndicator) bellIndicator.style.display = 'none';
                    // Nota: clicar no sino não limpa o indicador do chat
                });
            }
        });
    }
    
    /**
     * NOVO: Carrega a lista principal de salas de chat ativas.
     */
    async loadActiveRoomList() {
        // Verifica se a URL foi injetada (do context_processor)
        if (!this.urls.active_room_list) {
            console.error('URL active_room_list não definida. Você adicionou ao context_processor?');
            this.renderActiveRoomError('Falha ao carregar conversas (URL).');
            return;
        }

        try {
            const response = await fetch(this.urls.active_room_list);
            const data = await response.json();

            if (data.rooms && data.rooms.length > 0) {
                // Encontrou salas, vamos renderizá-las
                this.renderActiveRoomList(data.rooms);
            } else {
                // O backend funcionou, mas não há salas
                this.renderActiveRoomEmpty();
            }
        } catch (error) {
            console.error('Erro ao buscar lista de salas ativas:', error);
            this.renderActiveRoomError('Erro ao buscar conversas.');
        }
    }

    /**
     * NOVO: Renderiza a lista de salas ativas na sidebar.
     */
    renderActiveRoomList(rooms) {
        
        const container = document.getElementById('active-chats-list');
        
        if (!container) {
            console.error('Container #active-chats-list não encontrado!');
            return;
        }

        container.innerHTML = rooms.map(room => `
            <div class="chat-list-item" onclick="window.chatManager.openChatDialog('${room.room_id}', '${this.escapeHtml(room.room_name)}')">
                <div class="chat-list-avatar">
                    <i class="bi ${room.room_type === 'DM' ? 'bi-person' : 'bi-people'}"></i>
                </div>
                <div class="chat-list-info">
                    <div class="chat-list-name">${this.escapeHtml(room.room_name)}</div>
                    <div class="chat-list-preview">${this.escapeHtml(room.last_message)}</div>
                </div>
                ${room.unread_count > 0 ? `<div class="chat-list-unread">${room.unread_count}</div>` : ''}
            </div>
        `).join('');
    }

    /**
     * NOVO: Mostra o estado de "nenhuma conversa" (se necessário).
     */
    renderActiveRoomEmpty() {
       
        const container = document.getElementById('active-chats-list');
        if (container) {
            // Este HTML deve ser o mesmo que você tem por padrão
            container.innerHTML = `
                <div class="empty-state text-center p-4">
                    <i class="bi bi-chat-dots" style="font-size: 2rem;"></i>
                    <p class="text-muted mt-2">Nenhuma conversa ativa</p>
                    <small>Clique em "Nova Conversa" para começar</small>
                </div>
            `;
        }
    }

    /**
     * NOVO: Mostra estado de erro na sidebar.
     */
    renderActiveRoomError(message) {
        
        const container = document.getElementById('active-chats-list');
        if (container) {
            container.innerHTML = `
                <div class="error-state text-center p-4">
                     <i class="bi bi-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
                     <p class="text-muted mt-2">${message}</p>
                </div>
            `;
        }
    }

    /**
     * Faz janela ser arrastável
     */
    makeDraggable() {
        const header = document.getElementById('chat-dialog-header-bar');
        const container = document.getElementById('chat-draggable-container');
        
        if (!header || !container) return;

        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;
        let xOffset = 0;
        let yOffset = 0;

        header.addEventListener('mousedown', dragStart);
        header.addEventListener('touchstart', dragStart, { passive: false });

        function dragStart(e) {
            if (e.type === 'touchstart') {
                initialX = e.touches[0].clientX - xOffset;
                initialY = e.touches[0].clientY - yOffset;
            } else {
                initialX = e.clientX - xOffset;
                initialY = e.clientY - yOffset;
            }

            if (e.target === header || header.contains(e.target)) {
                isDragging = true;
            }

            e.preventDefault();
        }

        document.addEventListener('mousemove', drag);
        document.addEventListener('touchmove', drag, { passive: false });

        function drag(e) {
            if (!isDragging) return;

            e.preventDefault();

            if (e.type === 'touchmove') {
                currentX = e.touches[0].clientX - initialX;
                currentY = e.touches[0].clientY - initialY;
            } else {
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;
            }

            xOffset = currentX;
            yOffset = currentY;

            setTranslate(currentX, currentY, container);
        }

        document.addEventListener('mouseup', dragEnd);
        document.addEventListener('touchend', dragEnd);

        function dragEnd() {
            initialX = currentX;
            initialY = currentY;
            isDragging = false;
        }

        function setTranslate(xPos, yPos, el) {
            el.style.left = xPos + 'px';
            el.style.top = yPos + 'px';
        }
    }

    /**
     * Auto-resize da textarea
     */
    autoResizeTextarea() {
        const textarea = document.getElementById('chat-message-input');
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        }
    }

    /**
     * Classes para badges de status
     */
    getStatusBadgeClass(status) {
        const classes = {
            'pendente': 'bg-warning text-dark',
            'em_andamento': 'bg-info',
            'concluida': 'bg-success',
            'cancelada': 'bg-danger'
        };
        return classes[status] || 'bg-secondary';
    }

    /**
     * Classes para badges de prioridade
     */
    getPriorityBadgeClass(prioridade) {
        const classes = {
            'baixa': 'bg-success',
            'media': 'bg-warning text-dark',
            'alta': 'bg-danger',
            'urgente': 'bg-dark'
        };
        return classes[prioridade] || 'bg-secondary';
    }
}

// Inicialização quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM carregado, inicializando ChatManager...');
    
    // Pequeno delay para garantir que tudo está carregado
    setTimeout(() => {
        try {
            window.chatManager = new ChatManager(window.chatUrls);
            
            // Toggle global da sidebar
            window.toggleChatListSidebar = () => {
                console.log('Toggle sidebar chamado');
                window.chatManager.toggleChatListSidebar();
            };
            
            // Abrir chat a partir de elementos HTML
            window.openChatDialog = (roomId, roomName) => {
                console.log(`Abrindo chat: ${roomId} - ${roomName}`);
                window.chatManager.openChatDialog(roomId, roomName);
            };
            
            console.log('Sistema de Chat inicializado com sucesso!');
        } catch (error) {
            console.error('Erro crítico ao inicializar ChatManager:', error);
        }
    }, 100);
});

/// Tratamento de erros globais
window.addEventListener('error', function(e) {
    console.error('Erro global no sistema de chat:'),

    console.error(e.message, 'em', e.filename, 'linha', e.lineno);
});
/**
 * Sistema de Tema Automático
 * Detecta preferência do usuário e aplica tema claro/escuro
 */
class ThemeManager {
    constructor() {
        this.currentTheme = this.getPreferredTheme();
        this.applyTheme();
        this.initializeThemeListener();
    }

    getPreferredTheme() {
        // Verifica se o usuário tem preferência salva
        const savedTheme = localStorage.getItem('chat-theme');
        if (savedTheme) {
            return savedTheme;
        }

        // Verifica preferência do sistema
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }

        return 'light';
    }

    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.currentTheme);
        localStorage.setItem('chat-theme', this.currentTheme);
    }

    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme();
    }

    initializeThemeListener() {
        // Escuta mudanças na preferência do sistema
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
                if (!localStorage.getItem('chat-theme')) {
                    this.currentTheme = e.matches ? 'light' : 'dark';
                    this.applyTheme();
                }
            });
        }
    }
}

// Inicializa o gerenciador de tema
document.addEventListener('DOMContentLoaded', function() {
    window.themeManager = new ThemeManager();
    
    // Adiciona botão de toggle de tema (opcional)
    // Você pode adicionar um botão em sua UI se quiser
});
