
// static/js/notificacoes-realtime.js

(function () {
    'use strict';

    const config = window.NOTIF_CONFIG || {};
    let ultimoCheck = new Date().toISOString();
    let polling = null;

    // ===== Permissão de notificação do navegador =====
    if (config.browserNotifAtivo && 'Notification' in window) {
        if (Notification.permission === 'default') {
            // Pede permissão após 3s pra não ser intrusivo
            setTimeout(() => Notification.requestPermission(), 3000);
        }
    }

    // ===== Função: buscar novas notificações =====
    async function buscarNovas() {
        try {
            const url = `${config.apiUrl}?desde=${encodeURIComponent(ultimoCheck)}`;
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            });

            if (!response.ok) {
                if (response.status === 403) {
                    // Sessão expirou, para o polling
                    pararPolling();
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            ultimoCheck = data.server_time;

            // Atualiza badge do sino
            atualizarBadgeSino(data.total_nao_lidas);

            // Mostra cada nova notificação
            data.novas.forEach(notif => {
                mostrarToast(notif);
                mostrarBrowserNotification(notif);
                tocarSom();
            });

        } catch (error) {
            console.warn('Erro ao buscar notificações:', error);
        }
    }

    // ===== Função: mostrar toast bonitão =====
    function mostrarToast(notif) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const cores = {
            info: { bg: '#0d6efd', icone: 'ℹ️' },
            sucesso: { bg: '#198754', icone: '✅' },
            aviso: { bg: '#ffc107', icone: '⚠️' },
            erro: { bg: '#dc3545', icone: '🚨' },
        };
        const estilo = cores[notif.tipo] || cores.info;
        const icone = notif.icone || estilo.icone;

        const toast = document.createElement('div');
        toast.className = 'cetest-toast';
        toast.style.cssText = `
            background: white;
            border-left: 5px solid ${estilo.bg};
            border-radius: 8px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
            padding: 14px 16px;
            margin-bottom: 12px;
            display: flex;
            gap: 12px;
            animation: slideInRight 0.4s ease-out;
            cursor: ${notif.url ? 'pointer' : 'default'};
            position: relative;
        `;

        toast.innerHTML = `
            <div style="font-size: 24px; line-height: 1;">${icone}</div>
            <div style="flex: 1; min-width: 0;">
                <div style="font-weight: 600; color: #212529; margin-bottom: 4px;">
                    ${escapeHtml(notif.titulo)}
                </div>
                <div style="font-size: 13px; color: #6c757d; line-height: 1.4;">
                    ${escapeHtml(notif.mensagem)}
                </div>
            </div>
            <button class="toast-close" style="
                background: none; border: none; color: #adb5bd;
                cursor: pointer; font-size: 18px; line-height: 1;
                padding: 0; align-self: flex-start;
            ">&times;</button>
        `;

        // Click no toast → vai pra URL
        if (notif.url) {
            toast.addEventListener('click', (e) => {
                if (!e.target.classList.contains('toast-close')) {
                    window.location.href = notif.url;
                }
            });
        }

        // Botão fechar
        toast.querySelector('.toast-close').addEventListener('click', (e) => {
            e.stopPropagation();
            removerToast(toast);
        });

        container.appendChild(toast);

        // Auto-remove após 8 segundos
        setTimeout(() => removerToast(toast), 8000);
    }

    function removerToast(toast) {
        toast.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
    }

    // ===== Browser Notification (quando aba não está ativa) =====
    function mostrarBrowserNotification(notif) {
        if (!config.browserNotifAtivo) return;
        if (!('Notification' in window)) return;
        if (Notification.permission !== 'granted') return;
        if (document.hasFocus()) return;  // só mostra se aba estiver inativa

        const n = new Notification(notif.titulo, {
            body: notif.mensagem,
            icon: '/static/img/logo-cetest.png',
            badge: '/static/img/badge.png',
            tag: `notif-${notif.id}`,
            requireInteraction: false,
        });

        n.onclick = () => {
            window.focus();
            if (notif.url) window.location.href = notif.url;
            n.close();
        };

        setTimeout(() => n.close(), 10000);
    }

    // ===== Som =====
    function tocarSom() {
        if (!config.somAtivo) return;
        const audio = document.getElementById('som-notificacao');
        if (audio) {
            audio.currentTime = 0;
            audio.play().catch(() => { /* navegador bloqueou autoplay */ });
        }
    }

    // ===== Atualiza contador do sino =====
    function atualizarBadgeSino(total) {
        const badge = document.querySelector('#badge-notificacoes');
        if (!badge) return;

        if (total > 0) {
            badge.textContent = total > 99 ? '99+' : total;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }

    // ===== Utilitário =====
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    // ===== Controle do polling =====
    function iniciarPolling() {
        if (polling) return;
        polling = setInterval(buscarNovas, config.intervalo);
        // Pausa quando aba fica oculta (economia de recurso)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                pararPolling();
            } else {
                buscarNovas();  // busca imediata ao voltar
                iniciarPolling();
            }
        });
    }

    function pararPolling() {
        if (polling) {
            clearInterval(polling);
            polling = null;
        }
    }

    // ===== Start! =====
    iniciarPolling();
})();

