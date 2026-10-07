
/* chat.js — PARTE 1/3: núcleo, bootstrap lazy, lista de salas, modais */

const $ = (id) => document.getElementById(id);

class ChatManager {
    constructor(urls, currentUserId) {
        if (window.chatManager) return window.chatManager; // singleton
        window.chatManager = this;

        this.urls = {
            bootstrap_url: '/chat/api/bootstrap/',
            active_room_list: '/chat/api/rooms/',
            start_dm_base: '/chat/api/start-dm/0/',
            create_group_url: '/chat/api/create-group/',
            get_task_chat_base: '/chat/api/task/0/',
            upload_file_url: '/chat/api/upload/',
            get_chat_history: '/chat/api/history/00000000-0000-0000-0000-000000000000/',
            ...urls,
        };
        this.currentUserId = currentUserId;
        this.currentRoom = null;
        this.currentRoomName = null;
        this.cache = { rooms: [], users: [], tasks: [], messages: {} };
        this.loaded = false;
        this.debug = localStorage.getItem('chat-debug-mode') === 'true';

        this.actions = {
            'open-room': (t) => this.openRoom(t.dataset.roomId, t.dataset.roomName),
            'start-dm': (t) => this.startDM(t.dataset.userId),
            'open-task': (t) => this.openTaskChat(t.dataset.taskId),
            'view-image': (t) => this.viewImage?.(t.dataset.url),
            'download': (t) => this.downloadFile?.(t.dataset.url, t.dataset.name),
            'reconnect': () => this.manualReconnect?.(),
            'reload-rooms': () => this.loadBootstrap(true),
        };

        this.init();
    }

    // ───────────── infra ─────────────
    log(level, ...a) {
        if (level === 'debug' && !this.debug) return;
        (console[level] || console.log)('[chat]', ...a);
    }

    esc(v) {
        return String(v ?? '').replace(/[&<>"']/g, (c) => (
            { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
        ));
    }

    csrf() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    /** Troca o "0" final da URL base pelo id. */
    buildUrl(base, id) {
        return base.replace(/\/0\/?$/, `/${encodeURIComponent(id)}/`);
    }

    async getJSON(url) {
        const r = await fetch(url, { credentials: 'same-origin' });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const d = await r.json();
        if (d.status && d.status !== 'success') throw new Error(d.error || 'Erro');
        return d;
    }

    async postForm(url, body) {
        const r = await fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': this.csrf() },
            body,
        });
        const d = await r.json().catch(() => ({}));
        if (!r.ok || d.status === 'error') throw new Error(d.error || `HTTP ${r.status}`);
        return d;
    }

    toast(message, type = 'info') {
        document.querySelector('.chat-notification')?.remove();
        const bs = { info: 'primary', success: 'success', warning: 'warning', error: 'danger' }[type] || 'primary';
        const el = document.createElement('div');
        el.className = `chat-notification notification-${type}`;
        el.textContent = message; // sem innerHTML
        el.style.cssText = `position:fixed;top:20px;right:20px;z-index:9999;max-width:300px;
            padding:12px 20px;border-radius:8px;color:#fff;background:var(--bs-${bs});
            box-shadow:0 4px 12px rgba(0,0,0,.2)`;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 5000);
    }
    showNotification(m, t) { this.toast(m, t); } // compat

    closeModal(id) {
        const el = $(id);
        if (el) bootstrap.Modal.getInstance(el)?.hide();
    }

    // ───────────── init ─────────────
    async init() {
        if (document.readyState === 'loading') {
            await new Promise((r) => document.addEventListener('DOMContentLoaded', r, { once: true }));
        }
        this.bindUI();
        this.bindDelegation();
        this.setupMessaging?.();      // Parte 2
        this.setupNotifications?.();  // Parte 3
        document.dispatchEvent(new CustomEvent('chatSystemFullyReady'));
        this.log('info', 'ChatManager pronto');
    }

    bindUI() {
        const on = (id, ev, fn) => $(id)?.addEventListener(ev, fn);

        on('chat-modal-trigger', 'click', (e) => { e.preventDefault(); this.toggleSidebar(); });
        on('chatOverlay', 'click', (e) => { e.preventDefault(); this.toggleSidebar(false); });
        on('chat-list-btn', 'click', () => this.toggleSidebar());
        document.querySelector('.chat-close-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleSidebar(false);
        });

        on('iniciar-nova-conversa', 'click', (e) => {
            e.preventDefault();
            bootstrap.Modal.getOrCreateInstance($('novaConversaModal')).show();
        });
        $('novaConversaModal')?.addEventListener('shown.bs.modal', () => this.loadModalData());

        // busca de conversas (filtra o cache local)
        on('global-search-btn', 'click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const box = $('global-search-container');
            if (!box) return;
            const show = box.style.display === 'none';
            box.style.display = show ? 'block' : 'none';
            if (show) setTimeout(() => $('global-search-input')?.focus(), 50);
        });
        on('global-search-input', 'input', (e) => this.filterRooms(e.target.value));

        // modais
        on('dm-user-search', 'input', (e) => this.renderUsers(e.target.value));
        on('task-search', 'input', (e) => this.renderTasks(e.target.value));
        on('create-group-form', 'submit', (e) => this.createGroupChat(e));
    }

    /** Um único listener para todos os [data-action] (substitui onclick inline). */
    bindDelegation() {
        document.addEventListener('click', (e) => {
            const t = e.target.closest('[data-action]');
            const fn = t && this.actions[t.dataset.action];
            if (fn) { e.preventDefault(); fn(t); }
        });
    }

    // ───────────── sidebar + bootstrap lazy ─────────────
    toggleSidebar(show = null) {
        const sb = $('chatListContainer'), ov = $('chatOverlay');
        if (!sb || !ov) return;

        const on = show ?? !sb.classList.contains('active');
        sb.classList.toggle('active', on);
        ov.classList.toggle('active', on);
        clearTimeout(this._sbTimer);

        if (on) {
            sb.style.visibility = 'visible';
            sb.style.transform = 'translateX(0)';
            ov.style.display = 'block';
            requestAnimationFrame(() => { ov.style.opacity = '1'; });
            if (!this.loaded) this.loadBootstrap();
        } else {
            sb.style.transform = 'translateX(100%)';
            ov.style.opacity = '0';
            this._sbTimer = setTimeout(() => {
                sb.style.visibility = 'hidden';
                ov.style.display = 'none';
            }, 300);
        }
    }
    toggleChatListSidebar(show) { this.toggleSidebar(show); } // compat

    /** 1 request: salas + usuários + tarefas. Só roda quando o usuário abre o chat. */
    async loadBootstrap(force = false) {
        if (this._loading || (this.loaded && !force)) return;
        this._loading = true;
        const box = $('active-chats-list');
        try {
            const d = await this.getJSON(this.urls.bootstrap_url);
            this.cache.rooms = d.rooms || [];
            this.cache.users = d.users || [];
            this.cache.tasks = d.tasks || [];
            this.loaded = true;
            this.renderRooms(this.cache.rooms);
        } catch (err) {
            this.log('error', 'bootstrap', err);
            if (box) {
                box.innerHTML = `<div class="error-state text-center p-4">
                    <p class="text-muted">Erro ao carregar conversas</p>
                    <button class="btn btn-sm btn-outline-warning" data-action="reload-rooms">
                        Tentar novamente</button></div>`;
            }
        } finally {
            this._loading = false;
        }
    }

    // ───────────── lista de salas ─────────────
    renderRooms(rooms) {
        const box = $('active-chats-list');
        if (!box) return;

        if (!rooms.length) {
            box.innerHTML = `<div class="empty-state text-center p-4 text-muted">
                <i class="bi bi-chat-dots" style="font-size:2rem"></i>
                <p class="mt-2 mb-0">Nenhuma conversa</p>
                <small>Clique em "Nova Conversa" para começar</small></div>`;
        } else {
            box.innerHTML = rooms.map((r) => `
                <div class="chat-list-item ${r.unread_count > 0 ? 'has-unread' : ''}"
                     data-room-id="${this.esc(r.room_id)}"
                     data-room-name="${this.esc(r.room_name)}" data-action="open-room">
                    <div class="chat-list-avatar">
                        <i class="bi ${r.room_type === 'DM' ? 'bi-person' : 'bi-people'}"></i>
                    </div>
                    <div class="chat-list-info">
                        <div class="chat-list-name">${this.esc(r.room_name)}</div>
                        <div class="chat-list-preview">${this.esc(r.last_message)}</div>
                    </div>
                    <div class="chat-list-meta">
                        ${r.unread_count > 0 ? `<div class="chat-list-unread">${r.unread_count}</div>` : ''}
                    </div>
                </div>`).join('');
        }
        this.updateTotalBadge();
    }

    filterRooms(q) {
        const s = (q || '').toLowerCase().trim();
        const list = s
            ? this.cache.rooms.filter((r) => r.room_name.toLowerCase().includes(s))
            : this.cache.rooms;
        if (s && !list.length) {
            const box = $('active-chats-list');
            if (box) box.innerHTML = `<div class="text-center p-3 text-muted">
                <i class="bi bi-search"></i><p class="mb-0">Nenhum resultado</p></div>`;
            return;
        }
        this.renderRooms(list);
    }

    updateTotalBadge() {
        const total = this.cache.rooms.reduce((n, r) => n + (r.unread_count || 0), 0);
        const el = document.querySelector('.notification-indicator');
        if (!el) return;
        el.textContent = total;
        el.style.display = total > 0 ? 'block' : 'none';
    }

    /** Mensagem nova em sala que não está aberta. */
    bumpUnread(roomId, preview = '') {
        const r = this.cache.rooms.find((x) => x.room_id === roomId);
        if (!r) return this.loadBootstrap(true); // sala desconhecida → recarrega
        r.unread_count = (r.unread_count || 0) + 1;
        if (preview) r.last_message = preview;
        this.cache.rooms = [r, ...this.cache.rooms.filter((x) => x !== r)];
        this.renderRooms(this.cache.rooms);
    }

    clearUnread(roomId) {
        const r = this.cache.rooms.find((x) => x.room_id === roomId);
        if (!r || !r.unread_count) return;
        r.unread_count = 0;
        this.renderRooms(this.cache.rooms);
    }

    /** Sala criada por outra pessoa (evento new_chat_notification). */
    addRoomFromEvent(d) {
        if (this.cache.rooms.some((r) => r.room_id === d.room_id)) return;
        this.cache.rooms.unshift({
            room_id: d.room_id, room_name: d.room_name, room_type: 'DM',
            last_message: 'Nova conversa iniciada', unread_count: 1,
        });
        this.renderRooms(this.cache.rooms);
    }

    // ───────────── modais ─────────────
    async loadModalData() {
        if (!this.loaded) await this.loadBootstrap();
        this.renderUsers();
        this.renderTasks();
        this.renderGroupSelect();
    }

    renderUsers(q = '') {
        const box = $('dm-user-list-container');
        if (!box) return;
        const s = q.toLowerCase();
        const list = this.cache.users.filter((u) =>
            u.username.toLowerCase().includes(s) || (u.display_name || '').toLowerCase().includes(s));
        box.innerHTML = list.length ? list.map((u) => `
            <div class="user-list-item" data-action="start-dm" data-user-id="${u.id}">
                <div class="user-avatar"><i class="bi bi-person-fill"></i></div>
                <div class="user-info">
                    <div class="user-name">${this.esc(u.display_name || u.username)}</div>
                    <div class="user-email">@${this.esc(u.username)}</div>
                </div>
            </div>`).join('')
            : `<div class="text-center p-3 text-muted"><i class="bi bi-search"></i>
               <p class="mb-0">Nenhum usuário encontrado</p></div>`;
    }

    renderTasks(q = '') {
        const box = $('task-list-container');
        if (!box) return;
        const s = q.toLowerCase();
        const list = this.cache.tasks.filter((t) => t.titulo.toLowerCase().includes(s));
        box.innerHTML = list.length ? list.map((t) => `
            <div class="task-list-item" data-action="open-task" data-task-id="${t.id}">
                <div class="task-icon"><i class="bi bi-check-square-fill"></i></div>
                <div class="task-info">
                    <div class="task-title">${this.esc(t.titulo)}</div>
                    <span class="badge bg-secondary">${this.esc(t.status || 'N/A')}</span>
                </div>
            </div>`).join('')
            : `<div class="text-center p-3 text-muted"><i class="bi bi-list-task"></i>
               <p class="mb-0">Nenhuma tarefa encontrada</p></div>`;
    }

    renderGroupSelect() {
        const sel = $('group-participants-select');
        if (!sel) return;
        sel.innerHTML = this.cache.users.map((u) =>
            `<option value="${u.id}">${this.esc(u.display_name || u.username)}</option>`).join('');
    }

    // ───────────── criar / abrir conversas ─────────────
    async startDM(userId) {
        try {
            const d = await this.getJSON(this.buildUrl(this.urls.start_dm_base, userId));
            this.closeModal('novaConversaModal');
            await this.openRoom(d.room_id, d.room_name);
            if (d.created) this.loadBootstrap(true);
        } catch (e) {
            this.log('error', 'startDM', e);
            this.toast('Falha ao iniciar conversa', 'error');
        }
    }

    async createGroupChat(ev) {
        ev.preventDefault();
        const fd = new FormData(ev.target);
        if (!fd.get('name')?.trim()) return this.toast('Nome obrigatório', 'warning');
        if (!fd.getAll('participants').length) return this.toast('Selecione participantes', 'warning');
        try {
            const d = await this.postForm(this.urls.create_group_url, fd);
            ev.target.reset();
            this.closeModal('novaConversaModal');
            await this.openRoom(d.room_id, d.room_name);
            this.loadBootstrap(true);
        } catch (e) {
            this.log('error', 'createGroup', e);
            this.toast(e.message || 'Falha ao criar grupo', 'error');
        }
    }

    async openTaskChat(taskId) {
        try {
            const d = await this.getJSON(this.buildUrl(this.urls.get_task_chat_base, taskId));
            this.closeModal('novaConversaModal');
            await this.openRoom(d.room_id, d.room_name);
            this.loadBootstrap(true);
        } catch (e) {
            this.log('error', 'openTaskChat', e);
            this.toast('Falha ao acessar chat da tarefa', 'error');
        }
    }
}

window.ChatManager = ChatManager;
window.toggleChatListSidebar = () => window.chatManager?.toggleSidebar();
window.openChatDialog = (id, name) => window.chatManager?.openRoom(id, name);

/* chat.js — PARTE 2/3: sala aberta (histórico, WebSocket, envio, upload, leitura) */

const ZERO_UUID = '00000000-0000-0000-0000-000000000000';

Object.assign(ChatManager.prototype, {

    // ───────────── setup (chamado pelo init da Parte 1) ─────────────
    setupMessaging() {
        this.ws = null;
        this.wsAttempts = 0;
        this.wsTimer = null;
        this.maxAttempts = 5;
        this.reconnectOnShow = false;
        this.openToken = 0;
        this.uploadQueue = [];
        this.uploading = false;
        this.uploadSeq = 0;
        this.maxFileSize = 10 * 1024 * 1024;

        Object.assign(this.actions, {
            'retry-room': () => this.openRoom(this.currentRoom, this.currentRoomName),
        });

        const on = (id, ev, fn) => $(id)?.addEventListener(ev, fn);

        on('chat-message-submit', 'click', () => this.sendMessage());
        on('chat-message-input', 'keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        on('chat-message-input', 'input', (e) => {
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
        });
        on('close-dialog-btn', 'click', (e) => { e.stopPropagation(); this.closeRoom(); });

        const fi = $('image-upload-input');
        if (fi) {
            fi.multiple = true;
            fi.accept = 'image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.zip,.rar';
            fi.addEventListener('change', () => {
                this.enqueueFiles(Array.from(fi.files));
                fi.value = '';
            });
            on('attach-image-btn', 'click', () => fi.click());
        }

        // listeners globais da sala (singleton → registrados uma única vez)
        window.addEventListener('focus', () => this.markRead());
        window.addEventListener('beforeunload', () => this.closeSocket());
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) return;
            if (this.reconnectOnShow && this.currentRoom && !this.ws) {
                this.reconnectOnShow = false;
                this.connectRoom(this.currentRoom);
            }
            this.markRead();
        });
    },

    // ───────────── abrir / fechar sala ─────────────
    async openRoom(roomId, roomName) {
        const box = $('chat-draggable-container');
        const log = $('chat-log');
        if (!roomId) return;
        if (!box || !log) return this.toast('Janela de chat indisponível', 'error');

        const token = ++this.openToken;      // invalida aberturas anteriores em andamento
        this.closeSocket();
        this.toggleSidebar(false);

        this.currentRoom = roomId;
        this.currentRoomName = roomName || 'Chat';
        this.uploadQueue = [];
        this.wsAttempts = 0;

        const title = $('chat-dialog-header-title');
        if (title) title.textContent = this.currentRoomName;
        box.style.display = 'flex';
        box.classList.remove('minimized');
        this.hideConnError();

        log.innerHTML = `<div class="loading-state text-center p-4">
            <div class="spinner-border spinner-border-sm" role="status"></div>
            <p class="mt-2 mb-0">Carregando mensagens...</p></div>`;

        await this.loadHistory(roomId, token);
        if (token !== this.openToken) return;

        this.connectRoom(roomId);
        this.clearUnread(roomId);
    },

    closeRoom() {
        this.openToken++;
        this.closeSocket();
        this.uploadQueue = [];
        this.currentRoom = null;
        this.currentRoomName = null;
        this.hideConnError();
        const box = $('chat-draggable-container');
        if (box) {
            box.style.display = 'none';
            box.classList.remove('minimized');
        }
    },

    // ───────────── histórico ─────────────
    async loadHistory(roomId, token) {
        const log = $('chat-log');
        try {
            const url = this.urls.get_chat_history.replace(ZERO_UUID, encodeURIComponent(roomId));
            const d = await this.getJSON(url);
            if (token !== this.openToken) return;

            log.innerHTML = '';
            if (!d.messages?.length) {
                log.innerHTML = `<div class="welcome-state">
                    <i class="bi bi-chat-heart" style="font-size:3rem"></i>
                    <p>Nenhuma mensagem ainda</p><small>Seja o primeiro a enviar!</small></div>`;
                return;
            }
            const frag = document.createDocumentFragment();
            d.messages.forEach((m) => frag.appendChild(this.buildMessage(m)));
            log.appendChild(frag);
            log.scrollTop = log.scrollHeight;
        } catch (e) {
            if (token !== this.openToken) return;
            this.log('error', 'history', e);
            log.innerHTML = `<div class="error-state text-center p-4">
                <i class="bi bi-exclamation-triangle"></i>
                <p>Erro ao carregar mensagens</p>
                <button class="btn btn-sm btn-outline-danger" data-action="retry-room">Tentar novamente</button></div>`;
        }
    },

    // ───────────── renderização de mensagens ─────────────
    safeUrl(u) {
        return typeof u === 'string' && /^(https?:\/\/|\/(?!\/))/i.test(u) ? u : '';
    },

    fmtTime(ts) {
        const d = ts ? new Date(ts) : null;
        return d && !isNaN(d) ? d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : 'Agora';
    },

    fmtSize(b) {
        if (!b) return '';
        const i = Math.min(Math.floor(Math.log(b) / Math.log(1024)), 3);
        return `${parseFloat((b / 1024 ** i).toFixed(1))} ${['B', 'KB', 'MB', 'GB'][i]}`;
    },

    /** Escapa primeiro, depois aplica links/menções/quebras (sem brecha de XSS). */
    formatText(text) {
        return this.esc(text)
            .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" class="message-link">$1</a>')
            .replace(/(^|\s)@(\w+)/g, '$1<span class="mention">@$2</span>')
            .replace(/\n/g, '<br>');
    },

    fileIcon(type = '') {
        if (type.includes('image')) return 'bi-file-image';
        if (type.includes('pdf')) return 'bi-file-pdf';
        if (type.includes('word') || type.includes('document')) return 'bi-file-word';
        if (type.includes('excel') || type.includes('sheet')) return 'bi-file-excel';
        if (type.includes('video')) return 'bi-file-play';
        if (type.includes('audio')) return 'bi-file-music';
        if (type.includes('zip') || type.includes('compressed')) return 'bi-file-zip';
        return 'bi-file-earmark';
    },

    parseFile(m) {
        if (m.message_type !== 'file' || !m.file_data) return null;
        try {
            return typeof m.file_data === 'string' ? JSON.parse(m.file_data) : m.file_data;
        } catch { return null; }
    },

    fileHtml(f) {
        const name = this.esc(f.name || 'arquivo');
        const url = this.esc(this.safeUrl(f.url));
        const type = f.type || '';
        const size = this.fmtSize(f.size);
        const info = `<div class="file-icon"><i class="bi ${this.fileIcon(type)}"></i></div>
            <div class="file-info"><div class="file-name">${name}</div>
            ${size ? `<div class="file-size">${size}</div>` : ''}</div>`;

        if (type.includes('image') && url) {
            return `<div class="message-file">${info}</div>
                <div class="image-preview mt-2">
                    <img src="${url}" alt="${name}" class="img-fluid rounded"
                         style="max-width:200px;cursor:pointer" data-action="view-image" data-url="${url}">
                </div>`;
        }
        return `<div class="message-file" style="cursor:pointer" data-action="download"
                     data-url="${url}" data-name="${name}">
                ${info}
                <button type="button" class="btn btn-sm btn-outline-primary ms-2"><i class="bi bi-download"></i></button>
            </div>`;
    },

    messageBody(m) {
        const f = this.parseFile(m);
        if (f) return this.fileHtml(f);

        const img = this.esc(this.safeUrl(m.image_url));
        if (m.message_type === 'image' && img) {
            return `<div class="message-image"><img src="${img}" alt="Imagem" class="img-fluid rounded"
                    style="max-width:200px;cursor:pointer" data-action="view-image" data-url="${img}"></div>`;
        }
        return `<div class="message-text">${this.formatText(m.message ?? m.content ?? '')}</div>`;
    },

    isOwn(m) {
        return String(m.user_id) === String(this.currentUserId);
    },

    buildMessage(m) {
        const el = document.createElement('div');
        el.className = `message ${this.isOwn(m) ? 'own-message' : 'other-message'}`;
        const id = m.id ?? m.message_id;
        if (id != null) el.dataset.messageId = id;

        el.innerHTML = `<div class="message-content">
            <div class="message-header">
                <span class="message-sender">${this.esc(m.username || 'Usuário')}</span>
                <span class="message-time">${this.fmtTime(m.timestamp)}</span>
            </div>
            ${this.messageBody(m)}
            ${m.is_edited ? '<small class="message-edited text-muted"><i class="bi bi-pencil"></i> editado</small>' : ''}
        </div>`;

        // imagem quebrada → placeholder (sem onerror inline)
        el.querySelectorAll('img').forEach((img) => img.addEventListener('error', () => {
            const ph = document.createElement('div');
            ph.className = 'image-unavailable text-muted small p-2 border rounded';
            ph.textContent = 'Imagem indisponível';
            img.replaceWith(ph);
        }, { once: true }));
        return el;
    },

    findMessage(id) {
        return $('chat-log')?.querySelector(`[data-message-id="${CSS.escape(String(id))}"]`);
    },

    appendMessage(m) {
        const log = $('chat-log');
        if (!log) return;
        const id = m.id ?? m.message_id;
        if (id != null && this.findMessage(id)) return; // dedupe

        log.querySelectorAll('.welcome-state,.loading-state,.error-state').forEach((n) => n.remove());
        const nearBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 120;
        log.appendChild(this.buildMessage(m));
        if (nearBottom || this.isOwn(m)) log.scrollTop = log.scrollHeight;
    },

    // ───────────── WebSocket da sala ─────────────
    wsSend(obj) {
        if (this.ws?.readyState !== WebSocket.OPEN) return false;
        this.ws.send(JSON.stringify(obj));
        return true;
    },

    closeSocket() {
        clearTimeout(this.wsTimer);
        const ws = this.ws;
        this.ws = null; // handlers antigos se ignoram via checagem `this.ws !== ws`
        if (ws) { try { ws.close(1000); } catch { /* noop */ } }
    },

    connectRoom(roomId) {
        clearTimeout(this.wsTimer);
        if (this.ws || !roomId) return;

        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const ws = new WebSocket(`${proto}://${location.host}/ws/chat/${encodeURIComponent(roomId)}/`);
        this.ws = ws;
        this.setStatus('connecting');

        const connTimeout = setTimeout(() => {
            if (ws.readyState === WebSocket.CONNECTING) ws.close();
        }, 10000);

        ws.onopen = () => {
            clearTimeout(connTimeout);
            if (this.ws !== ws) return;
            this.wsAttempts = 0;
            this.setStatus('online');
            this.hideConnError();
            this.markRead();
        };

        ws.onmessage = (e) => {
            if (this.ws !== ws) return;
            let data;
            try { data = JSON.parse(e.data); } catch { return; }
            this.onRoomEvent(data);
        };

        ws.onclose = (e) => {
            clearTimeout(connTimeout);
            if (this.ws !== ws) return; // fechado de propósito / sala trocada
            this.ws = null;
            this.setStatus('offline');
            if (e.code === 1000 || e.code === 1001 || this.currentRoom !== roomId) return;
            this.scheduleReconnect(roomId);
        };

        ws.onerror = () => { /* onclose sempre vem em seguida */ };
    },

    scheduleReconnect(roomId) {
        if (this.wsAttempts >= this.maxAttempts) {
            this.setStatus('error');
            return this.showConnError('Falha de conexão.', true);
        }
        this.wsAttempts++;
        const delay = Math.min((2 ** this.wsAttempts) * 1000, 30000);
        this.showConnError(`Reconectando em ${delay / 1000}s...`);
        this.wsTimer = setTimeout(() => {
            if (this.currentRoom !== roomId || this.ws) return;
            if (document.hidden) { this.reconnectOnShow = true; return; }
            this.connectRoom(roomId);
        }, delay);
    },

    manualReconnect() {
        if (!this.currentRoom) return;
        this.wsAttempts = 0;
        this.closeSocket();
        this.hideConnError();
        this.connectRoom(this.currentRoom);
    },

    onRoomEvent(d) {
        switch (d.type) {
            case 'chat_message':
            case 'new_message':
            case 'file_message':
                return this.onIncoming(d);
            case 'read_receipt':
                return d.room_id && this.clearUnread(d.room_id);
            case 'message_edited': {
                const t = this.findMessage(d.message_id)?.querySelector('.message-text');
                if (!t) return;
                t.innerHTML = this.formatText(d.new_content);
                const c = t.closest('.message-content');
                if (c && !c.querySelector('.message-edited')) {
                    c.insertAdjacentHTML('beforeend',
                        '<small class="message-edited text-muted"><i class="bi bi-pencil"></i> editado</small>');
                }
                return;
            }
            case 'message_deleted': {
                const el = this.findMessage(d.message_id);
                if (!el) return;
                el.classList.add('deleted-message');
                el.innerHTML = `<div class="message-content"><div class="message-deleted">
                    <i class="bi bi-trash"></i> <span>Mensagem excluída</span></div></div>`;
                return;
            }
            default:
                this.log('debug', 'evento ignorado', d);
        }
    },

    onIncoming(d) {
        if (d.room_id && d.room_id !== this.currentRoom) {
            return this.bumpUnread(d.room_id, d.message || '📎 Arquivo');
        }
        this.appendMessage(d);
        if (this.isOwn(d)) return;

        this.playSound?.('message');                       // Parte 3
        if (document.hidden || !document.hasFocus()) {
            this.showBrowserNotification?.({               // Parte 3
                id: `msg-${d.message_id ?? d.id ?? Date.now()}`,
                titulo: d.username || 'Nova mensagem',
                mensagem: d.message_type === 'file' ? '📎 Arquivo' : String(d.message || '').slice(0, 80),
            });
        } else {
            this.markRead();
        }
    },

    /** Marca a sala aberta como lida — só se a aba estiver visível e focada. */
    markRead() {
        const id = this.currentRoom;
        if (!id || document.hidden || !document.hasFocus()) return;
        if (this.wsSend({ type: 'mark_as_read', all: true, room_id: id })) this.clearUnread(id);
    },

    // ───────────── envio de texto ─────────────
    sendMessage() {
        const input = $('chat-message-input');
        const text = input?.value.trim();
        if (!text || !this.currentRoom) return;

        const ok = this.wsSend({ type: 'chat_message', message: text, room_id: this.currentRoom });
        if (!ok) {
            this.toast('Sem conexão. Reconectando...', 'warning');
            if (!this.ws) this.connectRoom(this.currentRoom);
            return; // mantém o texto no campo
        }
        input.value = '';
        input.style.height = 'auto';
    },

    // ───────────── upload (fila sequencial) ─────────────
    enqueueFiles(files) {
        if (!this.currentRoom) return this.toast('Abra uma conversa primeiro', 'warning');
        const roomId = this.currentRoom;
        files.forEach((file) => {
            if (file.size > this.maxFileSize) {
                return this.toast(`"${file.name}" excede 10MB`, 'warning');
            }
            this.uploadQueue.push({ file, roomId });
        });
        this.drainUploads();
    },

    async drainUploads() {
        if (this.uploading) return;
        this.uploading = true;
        try {
            let job;
            while ((job = this.uploadQueue.shift())) {
                if (job.roomId !== this.currentRoom) continue; // usuário trocou de sala
                const tmp = this.uploadIndicator(job.file.name);
                try {
                    await this.uploadFile(job.file, job.roomId);
                } catch (e) {
                    this.log('error', 'upload', e);
                    this.toast(`Falha ao enviar ${job.file.name}`, 'error');
                } finally {
                    tmp?.remove();
                }
            }
        } finally {
            this.uploading = false;
        }
    },

    async uploadFile(file, roomId) {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('room_id', roomId);
        fd.append('message_type', 'file');

        const d = await this.postForm(this.urls.upload_file_url, fd);
        if (!d.file_data) throw new Error('Resposta inválida do servidor');
        if (!this.wsSend({ type: 'file_message', file_data: d.file_data, room_id: roomId })) {
            throw new Error('Sem conexão');
        }
    },

    uploadIndicator(name) {
        const log = $('chat-log');
        if (!log) return null;
        const el = document.createElement('div');
        el.className = 'message own-message uploading';
        el.dataset.uploadId = ++this.uploadSeq;
        el.innerHTML = `<div class="message-content">
            <div class="message-header"><span class="message-sender">Você</span>
            <span class="message-time">Enviando...</span></div>
            <div class="message-file"><div class="file-icon"><i class="bi bi-cloud-upload"></i></div>
            <div class="file-info"><div class="file-name">${this.esc(name)}</div>
            <div class="progress" style="height:4px"><div class="progress-bar progress-bar-striped progress-bar-animated" style="width:100%"></div></div>
            </div></div></div>`;
        log.appendChild(el);
        log.scrollTop = log.scrollHeight;
        return el;
    },

    // ───────────── imagem / download ─────────────
    viewImage(url) {
        const src = this.safeUrl(url);
        if (!src) return;
        $('imageViewModal')?.remove();

        const m = document.createElement('div');
        m.className = 'modal fade';
        m.id = 'imageViewModal';
        m.tabIndex = -1;
        m.innerHTML = `<div class="modal-dialog modal-dialog-centered modal-lg"><div class="modal-content">
            <div class="modal-header"><h5 class="modal-title">Imagem</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button></div>
            <div class="modal-body text-center"><img class="img-fluid" style="max-height:70vh" alt="Imagem"></div>
            <div class="modal-footer">
                <a download class="btn btn-primary"><i class="bi bi-download"></i> Download</a>
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button></div>
            </div></div>`;
        m.querySelector('img').src = src;   // via propriedade, não via template
        m.querySelector('a').href = src;
        document.body.appendChild(m);
        m.addEventListener('hidden.bs.modal', () => m.remove(), { once: true });
        bootstrap.Modal.getOrCreateInstance(m).show();
    },

    async downloadFile(url, name) {
        const src = this.safeUrl(url);
        if (!src) return this.toast('Arquivo não disponível', 'warning');
        try {
            const r = await fetch(src, { credentials: 'same-origin' });
            if (!r.ok) {
                return this.toast(r.status === 404
                    ? `"${name}" não está mais disponível`
                    : `Erro ${r.status} ao baixar`, r.status === 404 ? 'warning' : 'error');
            }
            const blobUrl = URL.createObjectURL(await r.blob());
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = name || 'arquivo';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(blobUrl);
        } catch (e) {
            this.log('error', 'download', e);
            this.toast('Falha ao baixar arquivo', 'error');
        }
    },

    // ───────────── status de conexão ─────────────
    setStatus(status) {
        const ind = document.querySelector('.status-indicator');
        const seen = document.querySelector('.last-seen');
        const labels = { online: 'Online', offline: 'Offline', connecting: 'Conectando...', error: 'Erro de conexão' };
        if (ind) {
            ind.classList.remove('online', 'offline', 'connecting', 'error');
            ind.classList.add(labels[status] ? status : 'offline');
        }
        if (seen) seen.textContent = labels[status] || 'Offline';
    },

    showConnError(msg, withButton = false) {
        let el = $('chat-connection-error');
        if (!el) {
            el = document.createElement('div');
            el.id = 'chat-connection-error';
            el.className = 'alert alert-warning mb-2';
            el.style.cssText = 'margin:10px;font-size:12px';
            const host = $('chat-dialog-content');
            if (!host) return;
            host.insertBefore(el, host.firstChild);
        }
        el.innerHTML = `<div class="d-flex justify-content-between align-items-center">
            <span>${this.esc(msg)}</span>
            ${withButton ? '<button class="btn btn-sm btn-outline-dark" data-action="reconnect"><i class="bi bi-arrow-clockwise"></i> Reconectar</button>' : ''}
            </div>`;
        el.style.display = 'block';
    },

    hideConnError() {
        const el = $('chat-connection-error');
        if (el) el.style.display = 'none';
    },
});

/* chat.js — PARTE 3/3: WS de notificações, som, janela (drag/minimizar), busca, info */

const SOUND_URLS = {
    alert: 'https://storage.googleapis.com/ctst-bucket-estatico-2026/static/sounds/notification_1.mp3',
    message: 'https://storage.googleapis.com/ctst-bucket-estatico-2026/static/sounds/notification_2.mp3',
    connect: 'https://storage.googleapis.com/ctst-bucket-estatico-2026/static/sounds/notification_2.mp3',
};
const BEEP_HZ = { alert: 900, message: 500, connect: 700 };
const NO_RETRY_CODES = [1000, 1001, 4401];

Object.assign(ChatManager.prototype, {

    // ───────────── entrada (chamada pelo init da Parte 1) ─────────────
    setupNotifications() {
        this.nws = null;
        this.nAttempts = 0;
        this.nTimer = null;
        this.nReconnectOnShow = false;
        this.minimized = false;

        Object.assign(this.actions, {
            'goto-message': (t) => this.gotoMessage(t.dataset.messageId),
        });

        this.setupSound();
        this.setupWindow();
        this.setupSearch();
        this.connectNotifications();

        // O badge do botão flutuante precisa da contagem de não lidas.
        // 1 request, fora do caminho crítico de carregamento da página.
        setTimeout(() => this.loadBootstrap(), 2000);

        window.addEventListener('beforeunload', () => this.closeNotifications());
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.nReconnectOnShow && !this.nws) {
                this.nReconnectOnShow = false;
                this.nAttempts = 0;
                this.connectNotifications();
            }
        });
        window.addEventListener('resize', () => this.clampWindow());
    },

    // ───────────── WebSocket de notificações ─────────────
    connectNotifications() {
        clearTimeout(this.nTimer);
        if (this.nws) return;

        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const ws = new WebSocket(`${proto}://${location.host}/ws/notifications/`);
        this.nws = ws;

        ws.onopen = () => {
            if (this.nws !== ws) return;
            this.nAttempts = 0;
            this.emitWsStatus(true);
        };

        ws.onmessage = (e) => {
            if (this.nws !== ws) return;
            let d;
            try { d = JSON.parse(e.data); } catch { return; }
            try { this.onNotificationEvent(d); } catch (err) { this.log('error', 'notif event', err); }
        };

        ws.onclose = (e) => {
            if (this.nws !== ws) return;
            this.nws = null;
            this.emitWsStatus(false);
            if (NO_RETRY_CODES.includes(e.code)) return;

            // backoff com teto de 60s e jitter; sem limite de tentativas
            // (o polling do NotificacoesAPI cobre enquanto estiver offline)
            this.nAttempts++;
            const delay = Math.min(2 ** this.nAttempts * 1000, 60000) + Math.random() * 1000;
            this.nTimer = setTimeout(() => {
                if (this.nws) return;
                if (document.hidden) { this.nReconnectOnShow = true; return; }
                this.connectNotifications();
            }, delay);
        };

        ws.onerror = () => { /* onclose vem em seguida */ };
    },

    closeNotifications() {
        clearTimeout(this.nTimer);
        const ws = this.nws;
        this.nws = null;
        if (ws) { try { ws.close(1000); } catch { /* noop */ } }
    },

    /** Permite ao NotificacoesAPI ligar/desligar o polling de fallback. */
    emitWsStatus(connected) {
        window.dispatchEvent(new CustomEvent('notifications:ws', { detail: { connected } }));
    },

    /** count_update + new_notification chegam juntos → 1 só recarga do dropdown. */
    refreshBell() {
        clearTimeout(this._bellTimer);
        this._bellTimer = setTimeout(() => window.NotificacoesAPI?.recarregarDropdown?.(), 300);
    },

    onNotificationEvent(d) {
        switch (d.type) {
            case 'notification_count_update':
                window.NotificacoesAPI?.atualizarBadge?.(d.count);
                return this.refreshBell();

            case 'new_notification': {
                const n = d.notification || {};
                window.NotificacoesAPI?.marcarVista?.(n);
                const urgent = n.prioridade === 'critica' || n.prioridade === 'alta';
                this.playSound(urgent ? 'alert' : 'message');
                this.toast(n.mensagem ? `${n.titulo}: ${n.mensagem}` : (n.titulo || 'Nova notificação'),
                    n.prioridade === 'critica' ? 'error' : 'info');
                this.showBrowserNotification(n);
                return this.refreshBell();
            }

            case 'notification_read':
                window.NotificacoesAPI?.marcarVista?.(d.notification);
                return this.refreshBell();

            case 'new_message_notification': {
                // sala aberta com WS ativo: o socket da sala já cuida de tudo
                if (d.room_id === this.currentRoom && this.ws) return;
                this.bumpUnread(d.room_id, d.preview || '');
                this.playSound('message');
                this.showBrowserNotification({
                    id: `msg-${d.message_id}`,
                    titulo: d.sender || 'Nova mensagem',
                    mensagem: d.preview || '',
                });
                return;
            }

            case 'new_chat_notification':
                this.addRoomFromEvent(d);
                return this.playSound('connect');

            case 'chat_room_read':
                return this.clearUnread(d.room_id);

            default:
                this.log('debug', 'evento de notificação ignorado', d);
        }
    },

    // ───────────── notificação nativa do navegador ─────────────
    /** Só chamada a partir de um gesto do usuário (política dos navegadores). */
    askBrowserPermission() {
        if (!('Notification' in window) || Notification.permission !== 'default') return;
        Notification.requestPermission().catch(() => {});
    },

    showBrowserNotification(n) {
        if (!n || !('Notification' in window)) return;
        if (Notification.permission !== 'granted' || document.hasFocus()) return;
        try {
            const critical = n.prioridade === 'critica';
            const bn = new Notification(n.titulo || 'Nova notificação', {
                body: n.mensagem || '',
                icon: '/static/images/logocetest.png',
                tag: `notif-${n.id}`,
                requireInteraction: critical,
            });
            bn.onclick = () => {
                window.focus();
                const url = this.safeUrl(n.url_destino);
                if (url) location.href = url;
                bn.close();
            };
            if (!critical) setTimeout(() => bn.close(), 8000);
        } catch (e) {
            this.log('warn', 'notificação nativa', e);
        }
    },

    // ───────────── som (carregado sob demanda) ─────────────
    setupSound() {
        this.soundEnabled = localStorage.getItem('chat-sound-enabled') !== 'false';
        this.sounds = {};
        this.audioCtx = null;
        this._lastSound = 0;
        this.updateSoundButton();

        $('chat-sound-toggle')?.addEventListener('click', () => {
            this.soundEnabled = !this.soundEnabled;
            localStorage.setItem('chat-sound-enabled', String(this.soundEnabled));
            this.updateSoundButton();
            if (this.soundEnabled) this.playSound('connect', true);
            this.toast(`Som ${this.soundEnabled ? 'ativado' : 'desativado'}`, 'info');
        });

        // primeiro gesto do usuário: libera permissão de notificação nativa
        document.addEventListener('click', () => this.askBrowserPermission(), { once: true });
    },

    updateSoundButton() {
        const b = $('chat-sound-toggle');
        if (!b) return;
        const i = b.querySelector('i');
        if (i) i.className = this.soundEnabled ? 'bi bi-volume-up-fill' : 'bi bi-volume-mute-fill';
        b.title = this.soundEnabled ? 'Desativar som' : 'Ativar som';
        b.classList.toggle('active', this.soundEnabled);
    },

    playSound(type = 'message', force = false) {
        if (!this.soundEnabled) return;
        const now = Date.now();
        if (!force && now - this._lastSound < 700) return; // evita rajadas
        this._lastSound = now;

        let a = this.sounds[type];
        if (!a) {
            a = this.sounds[type] = new Audio(SOUND_URLS[type] || SOUND_URLS.message);
            a.volume = 0.3;
        }
        a.currentTime = 0;
        a.play().catch(() => this.beep(type)); // arquivo falhou ou autoplay bloqueado
    },

    beep(type) {
        try {
            const Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) return;
            this.audioCtx ||= new Ctx();
            const ctx = this.audioCtx;
            if (ctx.state === 'suspended') ctx.resume();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.frequency.value = BEEP_HZ[type] || 600;
            gain.gain.setValueAtTime(0.001, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.1, ctx.currentTime + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
            osc.connect(gain).connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.3);
        } catch { /* sem áudio, sem problema */ }
    },

    // ───────────── janela: drag + minimizar ─────────────
    setupWindow() {
        const box = $('chat-draggable-container');
        const head = $('chat-dialog-header');
        if (box && head) {
            box.style.position = 'fixed';
            if (!box.style.left && !box.style.top) {
                box.style.right = '20px';
                box.style.bottom = '80px';
            }
            head.style.cursor = 'grab';

            let drag = null;
            head.addEventListener('pointerdown', (e) => {
                if (e.button !== 0 || e.target.closest('button, .btn, .header-buttons')) return;
                const r = box.getBoundingClientRect();
                drag = { dx: e.clientX - r.left, dy: e.clientY - r.top };
                head.setPointerCapture(e.pointerId);
                head.style.cursor = 'grabbing';
            });
            head.addEventListener('pointermove', (e) => {
                if (!drag) return;
                const x = Math.max(0, Math.min(window.innerWidth - box.offsetWidth, e.clientX - drag.dx));
                const y = Math.max(0, Math.min(window.innerHeight - box.offsetHeight, e.clientY - drag.dy));
                Object.assign(box.style, { left: `${x}px`, top: `${y}px`, right: 'auto', bottom: 'auto' });
            });
            const end = () => { drag = null; head.style.cursor = 'grab'; };
            head.addEventListener('pointerup', end);
            head.addEventListener('pointercancel', end);
        }

        const toggle = (e) => { e.stopPropagation(); this.toggleMinimize(); };
        $('minimize-chat-btn')?.addEventListener('click', toggle);
        $('maximize-chat-btn')?.addEventListener('click', toggle);
        $('chat-info-btn')?.addEventListener('click', () => this.showChatInfo());
    },

    clampWindow() {
        const box = $('chat-draggable-container');
        if (!box || box.style.left === '' || box.style.display === 'none') return;
        const x = Math.max(0, Math.min(window.innerWidth - box.offsetWidth, box.offsetLeft));
        const y = Math.max(0, Math.min(window.innerHeight - box.offsetHeight, box.offsetTop));
        box.style.left = `${x}px`;
        box.style.top = `${y}px`;
    },

    toggleMinimize() {
        const box = $('chat-draggable-container');
        const content = $('chat-dialog-content');
        if (!box || !content) return;

        this.minimized = !this.minimized;
        content.style.display = this.minimized ? 'none' : 'flex';
        box.style.height = this.minimized ? '60px' : '500px';
        box.classList.toggle('minimized', this.minimized);

        const min = $('minimize-chat-btn'), max = $('maximize-chat-btn');
        if (min) min.style.display = this.minimized ? 'none' : 'inline-block';
        if (max) max.style.display = this.minimized ? 'inline-block' : 'none';

        if (!this.minimized) this.markRead();
    },

    // ───────────── busca dentro da conversa (mensagens carregadas) ─────────────
    setupSearch() {
        const box = $('chat-search-container');
        const input = $('chat-search-input');

        $('toggle-chat-search-btn')?.addEventListener('click', () => {
            if (!box) return;
            const show = box.style.display === 'none' || !box.style.display;
            show ? (box.style.display = 'block', input?.focus(), input?.select()) : this.closeSearch();
        });
        $('close-chat-search-btn')?.addEventListener('click', () => this.closeSearch());

        let t;
        input?.addEventListener('input', (e) => {
            clearTimeout(t);
            t = setTimeout(() => this.searchChat(e.target.value), 200);
        });
        input?.addEventListener('keydown', (e) => { if (e.key === 'Escape') this.closeSearch(); });
    },

    closeSearch() {
        const box = $('chat-search-container');
        if (box) box.style.display = 'none';
        const out = $('chat-search-results');
        if (out) out.innerHTML = '';
        this.clearHighlights();
    },

    clearHighlights() {
        document.querySelectorAll('.search-highlighted').forEach((el) => el.classList.remove('search-highlighted'));
    },

    searchChat(query) {
        const out = $('chat-search-results');
        const log = $('chat-log');
        if (!out || !log) return;
        this.clearHighlights();

        const q = (query || '').trim();
        if (q.length < 2) { out.innerHTML = ''; return; }

        const needle = q.toLowerCase();
        const hits = [];
        log.querySelectorAll('.message[data-message-id]').forEach((el) => {
            const text = (el.querySelector('.message-text') || el.querySelector('.file-name'))?.textContent || '';
            if (!text.toLowerCase().includes(needle)) return;
            el.classList.add('search-highlighted');
            hits.push({
                id: el.dataset.messageId,
                sender: el.querySelector('.message-sender')?.textContent || '',
                time: el.querySelector('.message-time')?.textContent || '',
                text,
            });
        });

        if (!hits.length) {
            out.innerHTML = `<div class="text-center p-3 text-muted"><i class="bi bi-search"></i>
                <p class="mb-0">Nenhum resultado para "${this.esc(q)}"</p></div>`;
            return;
        }

        const re = new RegExp(`(${this.esc(q).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        out.innerHTML = `<div class="search-results-header p-2 border-bottom">
            <small class="text-muted">${hits.length} resultado(s)</small></div>` +
            hits.map((h) => `
            <div class="search-result-item p-2 border-bottom" style="cursor:pointer"
                 data-action="goto-message" data-message-id="${this.esc(h.id)}">
                <strong>${this.esc(h.sender)}</strong>
                <small class="text-muted ms-2">${this.esc(h.time)}</small>
                <div class="search-result-text">${this.esc(h.text).replace(re, '<mark>$1</mark>')}</div>
            </div>`).join('');
    },

    gotoMessage(id) {
        const el = this.findMessage(id);
        if (!el) return;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.style.transition = 'background-color .4s';
        el.style.backgroundColor = 'rgba(var(--bs-primary-rgb), .15)';
        setTimeout(() => { el.style.backgroundColor = ''; }, 2000);
    },

    // ───────────── informações da conversa ─────────────
    showChatInfo() {
        const modal = $('chatInfoModal');
        const body = $('chat-info-content');
        if (!modal || !body) return;

        const msgs = $('chat-log')?.querySelectorAll('.message[data-message-id]').length || 0;
        const files = $('chat-log')?.querySelectorAll('.message-file:not(.uploading *)').length || 0;
        const online = this.ws?.readyState === WebSocket.OPEN;

        body.innerHTML = `<div class="chat-info-details">
            <h6>Detalhes da Conversa</h6>
            <p><strong>Nome:</strong> ${this.esc(this.currentRoomName || 'N/A')}</p>
            <p><strong>ID da sala:</strong> ${this.esc(this.currentRoom || 'N/A')}</p>
            <p><strong>Status:</strong> ${online ? '🟢 Conectado' : '🔴 Desconectado'}</p>
            <p><strong>Som:</strong> ${this.soundEnabled ? 'Ativado' : 'Desativado'}</p>
            <hr>
            <p><strong>Mensagens carregadas:</strong> ${msgs}</p>
            <p><strong>Arquivos:</strong> ${files}</p>
        </div>`;
        bootstrap.Modal.getOrCreateInstance(modal).show();
    },
});

// ───────────── instância global ─────────────
// O template deve instanciar uma única vez, depois de carregar este arquivo:
//   new ChatManager({ bootstrap_url: "...", active_room_list: "...", ... }, {{ request.user.id }});
// O construtor é singleton: chamadas repetidas devolvem window.chatManager.

