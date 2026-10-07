// static/js/notificacoes-realtime.js
// Sino de notificações: API usada pelo chat.js (WebSocket) + polling de fallback.
// O polling só roda quando o WS de notificações está fora (evento `notifications:ws`).
(function () {
    'use strict';
    if (window.NotificacoesAPI) return;

    const config = Object.assign({
        apiUrl: '/notifications/api/novas/',
        contagemUrl: '/notifications/api/contagem/',
        dropdownUrl: '/notifications/dropdown-html/',  // ← ajuste para a URL da view dropdown_html
        intervalo: 30000,       // polling quando o WS está fora
        wsGraceMs: 5000,        // espera o WS conectar antes de ligar o polling
        overlapMs: 5000,        // sobreposição entre polls (a dedupe por id evita toast repetido)
        debounceMs: 300,
        somAtivo: true,
        browserNotifAtivo: true,
        badgeSelector: '#badge-notificacoes',
        listaSelector: '#notif-lista',
        toastContainerId: 'toast-container',
        somElementId: 'som-notificacao',
        somUrlFallback: '/static/sounds/notif.mp3',
        iconLogo: '/static/images/logocetest.png',
        iconBadge: '/static/images/logocetest.png',
    }, window.NOTIF_CONFIG || {});

    let ultimoCheck = null;          // Date (hora do servidor)
    let polling = null;
    let wsConnected = false;
    let buscando = false;
    let debounceTimer = null;
    let dropAbort = null;
    const vistas = new Set();        // ids já exibidos (WS ou polling)

    const AJAX = { 'X-Requested-With': 'XMLHttpRequest' };

    // ───────── utilitários ─────────
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str == null ? '' : String(str);
        return div.innerHTML;
    }

    function safeUrl(u) {
        return typeof u === 'string' && /^(https?:\/\/|\/(?!\/))/i.test(u) ? u : '';
    }

    function marcarVista(n) {
        const id = n && typeof n === 'object' ? n.id : n;
        if (id == null) return;
        vistas.add(String(id));
        if (vistas.size > 500) vistas.delete(vistas.values().next().value);
    }

    async function getJSON(url) {
        const r = await fetch(url, { headers: AJAX, credentials: 'same-origin' });
        if (r.status === 401 || r.status === 403 || r.redirected) {
            const e = new Error('sessão expirada');
            e.auth = true;
            throw e;
        }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    }

    function marcaServidor(iso) {
        const t = Date.parse(iso);
        return Number.isNaN(t) ? new Date() : new Date(t - config.overlapMs);
    }

    // ───────── badge ─────────
    function atualizarBadge(total) {
        const n = Math.max(0, parseInt(total, 10) || 0);
        const badge = document.querySelector(config.badgeSelector);
        if (!badge) return;
        badge.textContent = n > 99 ? '99+' : String(n);
        badge.style.display = n > 0 ? 'inline-block' : 'none';
        badge.classList.toggle('tem-novas', n > 0);
    }

    // ───────── dropdown (HTML renderizado pelo servidor) ─────────
    function recarregarDropdown() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(carregarDropdown, config.debounceMs);
    }

    async function carregarDropdown() {
        const lista = document.querySelector(config.listaSelector);
        if (!lista || !config.dropdownUrl) return;
        dropAbort?.abort();
        dropAbort = new AbortController();
        try {
            const r = await fetch(config.dropdownUrl, {
                headers: AJAX, credentials: 'same-origin', signal: dropAbort.signal,
            });
            if (!r.ok || r.redirected) throw new Error(`HTTP ${r.status}`);
            lista.innerHTML = await r.text();
        } catch (e) {
            if (e.name !== 'AbortError') console.warn('[notif] dropdown:', e);
        }
    }

    // ───────── polling ─────────
    async function sincronizarInicial() {
        try {
            const d = await getJSON(config.contagemUrl);
            ultimoCheck = marcaServidor(d.server_time);
            atualizarBadge(d.count ?? d.total_nao_lidas);
        } catch (e) {
            ultimoCheck = new Date();
            if (e.auth) pararPolling();
        }
        recarregarDropdown();
    }

    let ready = null;

    async function buscarNovas() {
        if (buscando) return;
        buscando = true;
        try {
            await ready;
            const url = `${config.apiUrl}?desde=${encodeURIComponent(ultimoCheck.toISOString())}`;
            const data = await getJSON(url);

            if (data.server_time) ultimoCheck = marcaServidor(data.server_time);
            atualizarBadge(data.total_nao_lidas);

            const novas = (Array.isArray(data.novas) ? data.novas : [])
                .filter((n) => !vistas.has(String(n.id)));
            if (!novas.length) return;

            novas.forEach((n) => {
                marcarVista(n);
                mostrarToast(n);
                mostrarBrowserNotification(n);
            });
            tocarSom();
            recarregarDropdown();
        } catch (e) {
            if (e.auth) {
                console.warn('[notif] sessão expirou, parando polling');
                pararPolling();
            } else {
                console.warn('[notif] erro ao buscar notificações:', e);
            }
        } finally {
            buscando = false;
        }
    }

    function iniciarPolling() {
        if (polling || wsConnected || document.hidden) return;
        polling = setInterval(buscarNovas, config.intervalo);
    }

    function pararPolling() {
        clearInterval(polling);
        polling = null;
    }

    function onWsState(connected) {
        const mudou = connected !== wsConnected;
        wsConnected = connected;
        if (connected) {
            pararPolling();
            if (mudou) buscarNovas();            // recupera o que chegou durante a queda
        } else if (mudou) {
            buscarNovas();
            iniciarPolling();
        }
    }

    // ───────── toast ─────────
    function garantirEstilos() {
        if (document.getElementById('cetest-toast-css')) return;
        const s = document.createElement('style');
        s.id = 'cetest-toast-css';
        s.textContent = `
            @keyframes slideInRight{from{transform:translateX(110%);opacity:0}to{transform:none;opacity:1}}
            @keyframes slideOutRight{from{transform:none;opacity:1}to{transform:translateX(110%);opacity:0}}`;
        document.head.appendChild(s);
    }

    function containerToast() {
        let c = document.getElementById(config.toastContainerId);
        if (!c) {
            c = document.createElement('div');
            c.id = config.toastContainerId;
            c.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;width:320px;max-width:calc(100vw - 40px)';
            document.body.appendChild(c);
        }
        return c;
    }

    function mostrarToast(notif) {
        garantirEstilos();
        const cores = {
            info: { bg: '#0d6efd', icone: 'ℹ️' },
            sucesso: { bg: '#198754', icone: '✅' },
            aviso: { bg: '#ffc107', icone: '⚠️' },
            erro: { bg: '#dc3545', icone: '🚨' },
        };
        const estilo = cores[notif.tipo] || cores.info;
        const raw = String(notif.icone || '').trim();
        const iconeHtml = /^bi[\s-]/.test(raw)
            ? `<i class="${raw.startsWith('bi ') ? '' : 'bi '}${escapeHtml(raw)}"></i>`
            : escapeHtml(raw || estilo.icone);
        const url = safeUrl(notif.url);

        const toast = document.createElement('div');
        toast.className = 'cetest-toast';
        toast.dataset.notifId = notif.id;
        toast.style.cssText = `background:#fff;border-left:5px solid ${estilo.bg};border-radius:8px;
            box-shadow:0 6px 20px rgba(0,0,0,.15);padding:14px 16px;margin-bottom:12px;display:flex;
            gap:12px;animation:slideInRight .4s ease-out;cursor:${url ? 'pointer' : 'default'}`;
        toast.innerHTML = `
            <div style="font-size:24px;line-height:1">${iconeHtml}</div>
            <div style="flex:1;min-width:0">
                <div style="font-weight:600;color:#212529;margin-bottom:4px">${escapeHtml(notif.titulo)}</div>
                <div style="font-size:13px;color:#6c757d;line-height:1.4">${escapeHtml(notif.mensagem)}</div>
            </div>
            <button type="button" class="toast-close" aria-label="Fechar"
                style="background:none;border:none;color:#adb5bd;cursor:pointer;font-size:18px;line-height:1;
                padding:0;align-self:flex-start">&times;</button>`;

        toast.addEventListener('click', (e) => {
            if (e.target.closest('.toast-close')) {
                e.stopPropagation();
                return removerToast(toast);
            }
            if (url) window.location.href = url;
        });

        containerToast().appendChild(toast);
        setTimeout(() => removerToast(toast), 8000);
    }

    function removerToast(toast) {
        if (!toast?.parentElement || toast.dataset.saindo) return;
        toast.dataset.saindo = '1';
        toast.style.animation = 'slideOutRight .3s ease-in forwards';
        setTimeout(() => toast.remove(), 300);
    }

    // ───────── notificação nativa + som ─────────
    function mostrarBrowserNotification(notif) {
        if (!config.browserNotifAtivo || !('Notification' in window)) return;
        if (Notification.permission !== 'granted' || document.hasFocus()) return;
        try {
            const n = new Notification(notif.titulo || 'Nova notificação', {
                body: notif.mensagem || '',
                icon: config.iconLogo,
                badge: config.iconBadge,
                tag: `notif-${notif.id}`,
            });
            n.onclick = () => {
                window.focus();
                const url = safeUrl(notif.url);
                if (url) window.location.href = url;
                n.close();
            };
            setTimeout(() => n.close(), 10000);
        } catch (e) { /* noop */ }
    }

    function tocarSom() {
        if (!config.somAtivo || localStorage.getItem('chat-sound-enabled') === 'false') return;
        if (window.chatManager?.playSound) return window.chatManager.playSound('message');

        const audio = document.getElementById(config.somElementId);
        if (audio) {
            audio.currentTime = 0;
            audio.play().catch(() => {});
            return;
        }
        try {
            const a = new Audio(config.somUrlFallback);
            a.volume = 0.5;
            a.play().catch(() => {});
        } catch (e) { /* noop */ }
    }

    // ───────── API pública (usada pelo chat.js) ─────────
    window.NotificacoesAPI = {
        atualizarBadge,
        recarregarDropdown,
        marcarVista,                       // chat.js avisa o que já mostrou via WS
        buscarNovas,
        iniciarPolling,
        pararPolling,
        config,
        get wsConnected() { return wsConnected; },
        get ultimoCheck() { return ultimoCheck; },
    };
    window.NotifRealtime = window.NotificacoesAPI;   // compatibilidade com o nome antigo

    // ───────── start ─────────
    window.addEventListener('notifications:ws', (e) => onWsState(!!e.detail?.connected));

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) return pararPolling();
        if (!wsConnected) {
            buscarNovas();
            iniciarPolling();
        }
    });

    // permissão de notificação nativa só após um gesto do usuário
    document.addEventListener('click', () => {
        if (config.browserNotifAtivo && 'Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().catch(() => {});
        }
    }, { once: true });

    ready = sincronizarInicial();
    // dá tempo ao WS de conectar; se não conectar, o polling assume
    setTimeout(() => { if (!wsConnected) iniciarPolling(); }, config.wsGraceMs);
})();

