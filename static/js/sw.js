
/**
 * Service Worker v3.0 - Push Notifications & Cache
 */

const CACHE_NAME = 'chat-app-v3.0';
const urlsToCache = [
    '/static/css/chat-modern.css',
    '/static/js/chat.js',
    '/static/js/chat-loader.js',
    '/static/sounds/notification_1.mp3',
    '/static/images/favicon.ico'
];

// Instalação do Service Worker
self.addEventListener('install', event => {
    console.log('🔧 Service Worker instalando...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('📦 Cache aberto');
                return cache.addAll(urlsToCache);
            })
            .catch(error => {
                console.error('❌ Erro ao criar cache:', error);
            })
    );
});

// Ativação do Service Worker
self.addEventListener('activate', event => {
    console.log('✅ Service Worker ativado');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('🗑️ Removendo cache antigo:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Interceptação de requisições
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Retorna do cache se disponível
                if (response) {
                    return response;
                }
                return fetch(event.request);
            })
    );
});

// Manipulação de Push Notifications
self.addEventListener('push', event => {
    console.log('🔔 Push notification recebida:', event);
    
    let notificationData = {
        title: 'Nova Mensagem',
        body: 'Você recebeu uma nova mensagem no chat',
        icon: '/static/images/favicon.ico',
        badge: '/static/images/notification-badge.png',
        tag: 'chat-message',
        data: {
            url: '/'
        }
    };

    if (event.data) {
        try {
            const data = event.data.json();
            notificationData = {
                title: data.title || 'Nova Mensagem',
                body: data.body || 'Você recebeu uma nova mensagem',
                icon: data.icon || '/static/images/favicon.ico',
                badge: '/static/images/notification-badge.png',
                tag: data.tag || 'chat-message',
                data: {
                    url: data.url || '/',
                    room_id: data.room_id,
                    message_id: data.message_id
                },
                actions: [
                    {
                        action: 'view',
                        title: 'Ver Mensagem',
                        icon: '/static/images/view-icon.png'
                    },
                    {
                        action: 'dismiss',
                        title: 'Dispensar',
                        icon: '/static/images/dismiss-icon.png'
                    }
                ],
                requireInteraction: true,
                timestamp: Date.now()
            };
        } catch (error) {
            console.error('❌ Erro ao processar dados da push notification:', error);
        }
    }

    event.waitUntil(
        self.registration.showNotification(notificationData.title, notificationData)
    );
});

// Clique na notificação
self.addEventListener('notificationclick', event => {
    console.log('👆 Notificação clicada:', event.notification.tag);
    
    event.notification.close();

    if (event.action === 'dismiss') {
        return;
    }

    const urlToOpen = event.notification.data.url || '/';
    
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then(clientList => {
            // Verifica se já existe uma janela/aba aberta
            for (const client of clientList) {
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            
            // Se não existe, abre nova janela
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});

// Background Sync para mensagens offline
self.addEventListener('sync', event => {
    console.log('🔄 Background sync:', event.tag);
    
    if (event.tag === 'background-sync-messages') {
        event.waitUntil(syncPendingMessages());
    }
});

async function syncPendingMessages() {
    try {
        // Implementar sincronização de mensagens pendentes
        console.log('📤 Sincronizando mensagens pendentes...');
        
        // Aqui você implementaria a lógica para enviar mensagens que ficaram na fila
        // quando o usuário estava offline
        
    } catch (error) {
        console.error('❌ Erro na sincronização:', error);
    }
}

// Manipulação de erros
self.addEventListener('error', event => {
    console.error('❌ Erro no Service Worker:', event.error);
});

self.addEventListener('unhandledrejection', event => {
    console.error('❌ Promise rejeitada no Service Worker:', event.reason);
});

