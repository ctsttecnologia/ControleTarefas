
// static/js/notificacoes-realtime.js
// Sistema de notificações em tempo real via polling
// Mescla: toast visual + polling robusto + dropdown + visibility API

(function () {
    'use strict';

    // ===== Configuração (sobrescrevível via window.NOTIF_CONFIG) =====
    const config = Object.assign({
        apiUrl: '/notifications/api/novas/',
        contagemUrl: '/notifications/api/contagem/',
        intervalo: 30000,                  // 30s entre polls
        somAtivo: true,
        browserNotifAtivo: true,
        badgeSelector: '#badge-notificacoes',
        listaSelector: '#notif-lista',     // dropdown do sino (opcional)
        toastContainerId: 'toast-container',
        somElementId: 'som-notificacao',
        somUrlFallback: '/static/sounds/notif.mp3',
        iconLogo: '/static/img/logo-cetest.png',
        iconBadge: '/static/img/badge.png',
    }, window.NOTIF_CONFIG || {});

    let ultimoCheck = new Date().toISOString();
    let polling = null;
    let visibilityHandlerRegistrado = false;

    // ===== Permissão de notificação do navegador =====
    if (config.browserNotifAtivo && 'Notification' in window) {
        if (Notification.permission === 'default') {
            setTimeout(() => Notification.requestPermission(), 3000);
        }
    }

    // ===========================================================
    // POLLING
    // ===========================================================
    async function buscarNovas() {
        try {
            const url = `${config.apiUrl}?desde=${encodeURIComponent(ultimoCheck)}`;
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            });

            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    console.warn('[notif] sessão expirou, parando polling');
                    pararPolling();
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Atualiza timestamp do servidor (evita drift de relógio)
            if (data.server_time) {
                ultimoCheck = data.server_time;
            }

            // Atualiza badge do sino
            atualizarBadgeSino(data.total_nao_lidas || 0);

            // Processa novas notificações
            const novas = Array.isArray(data.novas) ? data.novas : [];
            if (novas.length > 0) {
                novas.forEach(notif => {
                    mostrarToast(notif);
                    inserirNoDropdown(notif);
                    mostrarBrowserNotification(notif);
                });
                tocarSom();  // som único pra várias notificações
            }

        } catch (error) {
            console.warn('[notif] erro ao buscar notificações:', error);
        }
    }

    // ===========================================================
    // TOAST VISUAL
    // ===========================================================
    function mostrarToast(notif) {
        const container = document.getElementById(config.toastContainerId);
        if (!container) return;

        const cores = {
            info:    { bg: '#0d6efd', icone: 'ℹ️' },
            sucesso: { bg: '#198754', icone: '✅' },
            aviso:   { bg: '#ffc107', icone: '⚠️' },
            erro:    { bg: '#dc3545', icone: '🚨' },
        };
        const estilo = cores[notif.tipo] || cores.info;
        const rawIcone = notif.icone || estilo.icone;
        // Se vier uma classe do Bootstrap Icons (ex: "bi-clipboard-check"),
        // monta a tag <i>. Senão, usa o emoji direto.
        const iconeHtml = rawIcone.startsWith('bi-')
            ? `<i class="bi ${rawIcone}"></i>`
            : rawIcone;

        const toast = document.createElement('div');
        toast.className = 'cetest-toast';
        toast.dataset.notifId = notif.id;
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
            <div style="font-size: 24px; line-height: 1;">${iconeHtml}</div>
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
            " aria-label="Fechar">&times;</button>
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
        setTimeout(() => removerToast(toast), 8000);
    }

    function removerToast(toast) {
        if (!toast || !toast.parentElement) return;
        toast.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
    }

    // ===========================================================
    // DROPDOWN DO SINO (opcional — só atua se existir #notif-lista)
    // ===========================================================
    function inserirNoDropdown(notif) {
        const lista = document.querySelector(config.listaSelector);
        if (!lista) return;

        // Evita duplicar se a mesma notificação já estiver no dropdown
        if (lista.querySelector(`[data-notif-id="${notif.id}"]`)) return;

        const item = document.createElement('a');
        item.href = notif.url || '#';
        item.className = 'notif-item nova dropdown-item';
        item.dataset.notifId = notif.id;
        item.innerHTML = `
            <div class="notif-titulo" style="font-weight:600;">${escapeHtml(notif.titulo)}</div>
            <div class="notif-msg" style="font-size:13px; color:#6c757d;">${escapeHtml(notif.mensagem)}</div>
            <div class="notif-tempo" style="font-size:11px; color:#adb5bd;">agora</div>
        `;
        lista.prepend(item);
    }

    // ===========================================================
    // BROWSER NOTIFICATION (quando aba está inativa)
    // ===========================================================
    function mostrarBrowserNotification(notif) {
        if (!config.browserNotifAtivo) return;
        if (!('Notification' in window)) return;
        if (Notification.permission !== 'granted') return;
        if (document.hasFocus()) return;  // só notifica fora da aba

        const n = new Notification(notif.titulo, {
            body: notif.mensagem,
            icon: config.iconLogo,
            badge: config.iconBadge,
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

    // ===========================================================
    // SOM
    // ===========================================================
    function tocarSom() {
        if (!config.somAtivo) return;

        // Prefere <audio> no DOM (permite controle de volume via HTML)
        const audio = document.getElementById(config.somElementId);
        if (audio) {
            audio.currentTime = 0;
            audio.play().catch(() => { /* autoplay bloqueado */ });
            return;
        }

        // Fallback: cria Audio em runtime
        try {
            const a = new Audio(config.somUrlFallback);
            a.volume = 0.5;
            a.play().catch(() => {});
        } catch (e) {}
    }

    // ===========================================================
    // BADGE DO SINO
    // ===========================================================
    function atualizarBadgeSino(total) {
        const badge = document.querySelector(config.badgeSelector);
        if (!badge) return;

        if (total > 0) {
            badge.textContent = total > 99 ? '99+' : total;
            badge.style.display = 'inline-block';
            badge.classList.add('tem-novas');
        } else {
            badge.textContent = '0';
            badge.style.display = 'none';
            badge.classList.remove('tem-novas');
        }
    }

    // ===========================================================
    // UTILITÁRIO
    // ===========================================================
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    // ===========================================================
    // CONTROLE DO POLLING
    // ===========================================================
    function iniciarPolling() {
        if (polling) return;
        polling = setInterval(buscarNovas, config.intervalo);

        // Registra visibility listener APENAS UMA VEZ
        if (!visibilityHandlerRegistrado) {
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    pararPolling();
                } else {
                    buscarNovas();        // busca imediata ao voltar
                    iniciarPolling();
                }
            });
            visibilityHandlerRegistrado = true;
        }
    }

    function pararPolling() {
        if (polling) {
            clearInterval(polling);
            polling = null;
        }
    }

    // ===========================================================
    // START!
    // ===========================================================
    // Busca imediata + inicia polling
    buscarNovas();
    iniciarPolling();

    // Expor pra debug no console
    window.NotifRealtime = {
        buscarNovas,
        iniciarPolling,
        pararPolling,
        config,
        get ultimoCheck() { return ultimoCheck; },
    };
})();

