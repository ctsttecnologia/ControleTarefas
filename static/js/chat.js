
// --- VARIÁVEIS GLOBAIS (APENAS ESTADO) ---
let activeChatSocket = null;
let currentRoomId = null;
let isDraggableInitialized = false;

// --- FUNÇÕES UTILITÁRIAS ---

/**
 * Rola o chat para o final
 */
function scrollToBottom() {
    const chatLog = document.getElementById('chat-log'); 
    if (chatLog && chatLog.scrollHeight > chatLog.clientHeight) {
        chatLog.scrollTop = chatLog.scrollHeight;
    }
}

/**
 * Converte timestamp para formato legível
 */
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

/**
 * Cria elemento de mensagem
 */
function createMessageElement(data, isSender) {
    const messageRow = document.createElement('div');
    messageRow.classList.add('message-row', isSender ? 'sender' : 'receiver');
    
    const bubble = document.createElement('div');
    bubble.classList.add('message-bubble', isSender ? 'sender-bubble' : 'receiver-bubble');

    if (data.image_url) {
        const img = document.createElement('img');
        img.src = data.image_url;
        img.classList.add('img-fluid', 'chat-img');
        img.alt = 'Imagem enviada no chat';
        bubble.appendChild(img);
    } else if (data.message) {
        const contentP = document.createElement('p');
        contentP.textContent = data.message; 
        bubble.appendChild(contentP);
    }
    
    const info = document.createElement('small');
    info.classList.add('message-info');
    info.textContent = `${data.username} - ${formatTimestamp(data.timestamp)}`;

    messageRow.appendChild(bubble);
    messageRow.appendChild(info);

    return messageRow;
}

// --- FUNÇÕES GLOBAIS PRINCIPAIS ---

/**
 * Abre/fecha o sidebar de lista de chats
 */
window.toggleChatListSidebar = function() {
    const body = document.body;
    const isClosing = body.classList.contains('chat-list-open');
    
    body.classList.toggle('chat-list-open');
    
    if (isClosing) {
        window.closeActiveChat();
    }
};

/**
 * Renderiza uma mensagem no chat
 */
window.renderMessage = function(data) {
    const chatLog = document.getElementById('chat-log');
    const userNameEl = document.getElementById('json-username');
    const userName = userNameEl ? JSON.parse(userNameEl.textContent) : '""';
    
    if (!chatLog) return; 

    const isSender = (data.username === userName);
    const messageElement = createMessageElement(data, isSender);
    
    chatLog.appendChild(messageElement);
    scrollToBottom();
};

/**
 * Abre o diálogo de chat
 */
window.openChatDialog = function(roomId, roomName) {
    // Esconde a lista
    document.body.classList.remove('chat-list-open');
    
    // Mostra o painel de diálogo
    const chatDialogContainer = document.getElementById('chat-draggable-container');
    if (chatDialogContainer) {
        chatDialogContainer.style.display = 'flex';
        chatDialogContainer.classList.remove('minimized');
    }

    // Carrega o novo chat
    window.loadAndConnectChat(roomId, roomName); 
};

/**
 * Carrega o chat e conecta WebSocket
 */
window.loadAndConnectChat = function(newRoomId, roomName) {
    const chatLog = document.getElementById('chat-log'); 
    const chatDialogHeaderTitle = document.getElementById('chat-dialog-header-title'); 
    
    // Se já está conectado à mesma sala, não faz nada
    if (currentRoomId === newRoomId && activeChatSocket) {
        console.log(`Já conectado à sala ${newRoomId}.`);
        return;
    }

    // Fecha conexão anterior
    window.closeActiveChat();

    // Limpa e atualiza interface
    if (chatLog) chatLog.innerHTML = '';
    if (chatDialogHeaderTitle) {
        chatDialogHeaderTitle.textContent = 'Conversa com: ' + roomName; 
    }

    currentRoomId = newRoomId;
    
    // Conecta WebSocket
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    activeChatSocket = new WebSocket(
        `${wsProtocol}://${window.location.host}/ws/chat/${currentRoomId}/`
    );
    
    activeChatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        window.renderMessage(data);
    };

    activeChatSocket.onclose = function(e) {
        console.error(`Socket de chat fechado para sala ${currentRoomId}.`, e);
    };
    
    // Busca histórico
    window.loadChatHistory(currentRoomId);
};

/**
 * Carrega histórico do chat
 */
window.loadChatHistory = function(roomId) {
    fetch(`/chat/historico/${roomId}/`) 
        .then(response => {
            if (!response.ok) throw new Error('Erro ao carregar histórico');
            return response.json();
        })
        .then(data => {
            data.messages.forEach(msg => {
                window.renderMessage(msg); 
            });
            scrollToBottom();
        })
        .catch(error => console.error('Erro ao carregar histórico:', error));
        
    // Garante rolagem após renderização
    setTimeout(scrollToBottom, 350); 
};

/**
 * Inicia chat individual (DM)
 */
window.startChat = function(userId) {
    console.log("Tentando iniciar chat com usuário:", userId);
    
    const modalElement = document.getElementById('novaConversaModal');
    const modal = bootstrap.Modal.getInstance(modalElement); 
    
    if (modal) {
        modal.hide();
    }
    
    fetch(`/chat/start_chat/${userId}/`)
        .then(response => {
            if (!response.ok) throw new Error('Erro na resposta do servidor');
            return response.json();
        })
        .then(data => {
            if (data.room_id) {
                window.openChatDialog(data.room_id, data.room_name);
            } else {
                throw new Error(data.error || 'Erro desconhecido');
            }
        })
        .catch(err => {
            console.error('Erro ao iniciar chat:', err);
            alert("Não foi possível iniciar o chat.");
        });
};

/**
 * Fecha chat ativo
 */
window.closeActiveChat = function() {
    if (activeChatSocket) {
        activeChatSocket.close();
        activeChatSocket = null;
    }
    currentRoomId = null;
};

/**
 * Envia mensagem via WebSocket
 */
window.sendChatMessage = function(message) {
    if (!message.trim() || !activeChatSocket) return false;
    
    activeChatSocket.send(JSON.stringify({
        'type': 'chat_message', 
        'message': message
    }));
    return true;
};

/**
 * Envia imagem via WebSocket
 */
window.sendImageMessage = function(file) {
    if (!file || !activeChatSocket) return false;
    
    if (file.size > 5 * 1024 * 1024) {
        alert('A imagem é muito grande (máx 5MB).'); 
        return false;
    }

    const reader = new FileReader();
    reader.onload = function(event) {
        activeChatSocket.send(JSON.stringify({
            'type': 'image_message', 
            'image': event.target.result
        }));
    };
    reader.readAsDataURL(file);
    return true;
};

// --- FUNÇÕES DE UI ---

/**
 * Toggle estado minimizado do chat
 */
window.toggleChatMinimize = function() {
    const chatDialogContainer = document.getElementById('chat-draggable-container');
    const minimizeBtn = document.getElementById('minimize-chat-btn');
    
    if (!chatDialogContainer || !minimizeBtn) return;
    
    chatDialogContainer.classList.toggle('minimized');
    
    // Atualiza tooltip e aria-label
    if (chatDialogContainer.classList.contains('minimized')) {
        minimizeBtn.title = "Restaurar";
        minimizeBtn.setAttribute('aria-label', 'Restaurar chat');
    } else {
        minimizeBtn.title = "Minimizar";
        minimizeBtn.setAttribute('aria-label', 'Minimizar chat');
    }
};

/**
 * Fecha diálogo de chat
 */
window.closeChatDialog = function() {
    const chatDialogContainer = document.getElementById('chat-draggable-container');
    if (chatDialogContainer) {
        chatDialogContainer.style.display = 'none';
    }
    document.body.classList.add('chat-list-open'); 
    window.closeActiveChat();
};

// --- DRAG & DROP FUNCTIONALITY ---

function makeElementDraggable(elmnt, header) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    
    header.onmousedown = dragMouseDown;

    function dragMouseDown(e) {
        e.preventDefault();
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e.preventDefault();
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;
        elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
        elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
    }

    function closeDragElement() {
        document.onmouseup = null;
        document.onmousemove = null;
    }
}

// --- EVENT LISTENERS ---

document.addEventListener('DOMContentLoaded', function() {
    const chatDialogContainer = document.getElementById('chat-draggable-container');
    const novaConversaModalEl = document.getElementById('novaConversaModal'); 
    const userListBody = document.getElementById('user-list-body');

    // Inicializa draggable na primeira abertura do chat
    const originalOpenChatDialog = window.openChatDialog;
    window.openChatDialog = function(roomId, roomName) {
        originalOpenChatDialog(roomId, roomName); 

        if (!isDraggableInitialized && chatDialogContainer) {
            const chatDialogHeaderBar = document.getElementById('chat-dialog-header-bar');
            if (chatDialogHeaderBar) {
                makeElementDraggable(chatDialogContainer, chatDialogHeaderBar);
                isDraggableInitialized = true;
            }
        }
    };

    // Event Delegation para clicks
    document.addEventListener('click', function(e) {
        // Enviar mensagem
        if (e.target.closest('#chat-message-submit')) {
            const chatInput = document.getElementById('chat-message-input');
            if (!chatInput) return;
            
            const message = chatInput.value;
            if (window.sendChatMessage(message)) {
                chatInput.value = ''; 
                chatInput.focus();
            }
        }

        // Upload de imagem
        if (e.target.closest('#upload-image-btn')) {
            const imageUploadInput = document.getElementById('image-upload-input');
            if (imageUploadInput) imageUploadInput.click();
        }

        // Fechar diálogo
        if (e.target.closest('#close-dialog-btn')) {
            window.closeChatDialog();
        }

        // Minimizar/Restaurar
        if (e.target.closest('#minimize-chat-btn')) {
            window.toggleChatMinimize();
            e.stopPropagation();
        }

        // Restaurar ao clicar no header minimizado
        if (e.target.closest('.chat-dialog-header') && 
            chatDialogContainer && 
            chatDialogContainer.classList.contains('minimized')) {
            
            chatDialogContainer.classList.remove('minimized');
            const minimizeBtn = document.getElementById('minimize-chat-btn');
            if (minimizeBtn) {
                minimizeBtn.title = "Minimizar";
                minimizeBtn.setAttribute('aria-label', 'Minimizar chat');
            }
        }

        // Iniciar nova conversa
        if (e.target.closest('#iniciar-nova-conversa')) {
            e.preventDefault();
            handleNewConversation(novaConversaModalEl, userListBody);
        }
    });

    // Eventos de teclado
    document.addEventListener('keyup', function(e) {
        if (e.target.closest('#chat-message-input') && e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const chatSubmit = document.getElementById('chat-message-submit');
            if (chatSubmit) chatSubmit.click();
        }
    });
    
    // Eventos de change
    document.addEventListener('change', function(e) {
        if (e.target.closest('#image-upload-input')) {
            const file = e.target.files[0];
            const imageUploadInput = e.target;
            
            if (window.sendImageMessage(file)) {
                imageUploadInput.value = '';
            }
        }
    });

    // Eventos do modal
    if (novaConversaModalEl) {
        novaConversaModalEl.addEventListener('hidden.bs.modal', function() {
            if (userListBody) {
                userListBody.innerHTML = `
                    <div class="text-center">
                        <div class="spinner-border" role="status">
                            <span class="visually-hidden">Carregando usuários...</span>
                        </div>
                    </div>`;
            }
        });
    }
});

/**
 * Manipula abertura do modal de nova conversa
 */
function handleNewConversation(modalEl, userListBody) {
    if (!modalEl) {
        console.error("Elemento do modal '#novaConversaModal' não encontrado.");
        return;
    }

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
    
    const userListUrl = modalEl.dataset.userListUrl;

    if (userListUrl && userListBody) {
        userListBody.innerHTML = `
            <div class="text-center">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Carregando usuários...</span>
                </div>
            </div>`;
        
        fetch(userListUrl) 
            .then(response => {
                if (!response.ok) throw new Error('Erro ao carregar usuários');
                return response.text();
            })
            .then(html => {
                userListBody.innerHTML = html;
            })
            .catch(err => {
                console.error("Erro ao carregar lista de usuários:", err);
                userListBody.innerHTML = "<p class='text-danger'>Erro ao carregar usuários.</p>";
            });
    }
}

