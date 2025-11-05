
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
    }

    /**
     * Inicializa todos os event listeners do chat
     */
    /**
     * Inicializa todos os event listeners do chat
     */
    initializeEventListeners() {
        console.log('Inicializando event listeners do chat...');
        
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
                console.error('❌ URL de lista de usuários não definida');
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
                console.log(`✅ ${data.users.length} usuários carregados para DM`);
            }
        } catch (error) {
            console.error('❌ Erro ao carregar usuários:', error);
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
                console.error('❌ URL de lista de usuários não definida');
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
                console.log(`✅ ${data.users.length} usuários carregados para grupo`);
            }
        } catch (error) {
            console.error('❌ Erro ao carregar usuários para grupo:', error);
        }
    }

    /**
     * Carrega tarefas para o chat
     */
    async loadTasks() {
        try {
            if (!this.urls.task_list) {
                console.error('❌ URL de lista de tarefas não definida');
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
                console.log(`✅ ${data.tasks.length} tarefas carregadas`);
            }
        } catch (error) {
            console.error('❌ Erro ao carregar tarefas:', error);
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
                console.error('❌ URL base para DM não definida');
                this.showNotification('Configuração de URL incompleta', 'error');
                return;
            }

            console.log(`Iniciando DM com usuário ${userId}...`);
            this.showLoading('Iniciando conversa...');

            const response = await fetch(`${this.urls.start_dm_base}${userId}/`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log(`✅ DM criada: ${data.room_id}`);
                this.openChatDialog(data.room_id, data.room_name);
                this.hideModal('novaConversaModal');
                this.showNotification('Conversa iniciada com sucesso!', 'success');
            } else {
                console.error('❌ Erro ao criar DM:', data.error);
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('❌ Erro ao iniciar DM:', error);
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
            if (!this.urls.get_task_chat_base) {
                console.error('URL base para chat de tarefa não definida');
                return;
            }

            this.showLoading('Abrindo chat da tarefa...');

            const response = await fetch(`${this.urls.get_task_chat_base}${taskId}/`);
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
     * Abre diálogo de chat
     */
    openChatDialog(roomId, roomName) {
        this.currentRoom = roomId;
        
        // Atualiza UI
        const titleElement = document.getElementById('chat-dialog-header-title');
        const container = document.getElementById('chat-draggable-container');
        
        if (titleElement) titleElement.textContent = roomName;
        if (container) {
            container.style.display = 'block';
            container.classList.remove('minimized');
        }
        
        this.isMinimized = false;
        
        // Conecta WebSocket
        this.connectWebSocket(roomId);
        
        // Carrega histórico
        this.loadChatHistory(roomId);
        
        // Foca no input de mensagem
        setTimeout(() => {
            const input = document.getElementById('chat-message-input');
            if (input) input.focus();
        }, 100);
        
        // Fecha lista de conversas
        this.toggleChatListSidebar();
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
            console.error('❌ Erro WebSocket:', error);
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
            this.showDesktopNotification(data.username, data.message);
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
     * Minimiza/restaura janela do chat
     */
    toggleMinimize() {
        const container = document.getElementById('chat-draggable-container');
        const chatLog = document.getElementById('chat-log');
        const inputArea = document.querySelector('.chat-input-area');
        
        if (!container) return;
        
        this.isMinimized = !this.isMinimized;
        
        if (this.isMinimized) {
            if (chatLog) chatLog.style.display = 'none';
            if (inputArea) inputArea.style.display = 'none';
            container.classList.add('minimized');
        } else {
            if (chatLog) chatLog.style.display = 'block';
            if (inputArea) inputArea.style.display = 'flex';
            container.classList.remove('minimized');
        }
    }

    /**
     * Fecha janela do chat
     */
    closeChat() {
        const container = document.getElementById('chat-draggable-container');
        if (container) {
            container.style.display = 'none';
        }
        
        this.currentRoom = null;
        
        if (this.websocket) {
            this.websocket.close(1000, 'Usuário fechou o chat');
            this.websocket = null;
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

    // ========== MÉTODOS AUXILIARES ==========

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
                    icon: '/static/images/favicon.ico'
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
    console.log('🚀 DOM carregado, inicializando ChatManager...');
    
    // Pequeno delay para garantir que tudo está carregado
    setTimeout(() => {
        try {
            window.chatManager = new ChatManager();
            
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
            
            console.log('✅✅✅ Sistema de Chat inicializado com sucesso!');
        } catch (error) {
            console.error('❌❌❌ Erro crítico ao inicializar ChatManager:', error);
        }
    }, 100);
});

/// Tratamento de erros globais
window.addEventListener('error', function(e) {
    console.error('💥 Erro global no sistema de chat:', e.error);
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
                    this.currentTheme = e.matches ? 'dark' : 'light';
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

