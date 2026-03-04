
// static/js/global.js

document.addEventListener('DOMContentLoaded', () => {

    const themeSwitcherBtn = document.getElementById('theme-switcher-btn');

    if (themeSwitcherBtn) {
        const htmlElement = document.documentElement;
        const lightIcon = themeSwitcherBtn.querySelector('.theme-icon-light');
        const darkIcon = themeSwitcherBtn.querySelector('.theme-icon-dark');
        const navbar = document.querySelector('#global-header .navbar');

        const setTheme = (theme) => {
            htmlElement.setAttribute('data-bs-theme', theme);
            localStorage.setItem('theme', theme);

            // Atualiza ícone
            if (theme === 'dark') {
                lightIcon?.classList.add('d-none');
                darkIcon?.classList.remove('d-none');
            } else {
                darkIcon?.classList.add('d-none');
                lightIcon?.classList.remove('d-none');
            }

            // Atualiza cor do header
            if (navbar) {
                navbar.style.backgroundColor = theme === 'dark' 
                    ? '#1e2d3d' 
                    : '#00b8d4';
            }
        };

        themeSwitcherBtn.addEventListener('click', () => {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            setTheme(currentTheme === 'dark' ? 'light' : 'dark');
        });

        // Inicialização
        const savedTheme = localStorage.getItem('theme') || 'dark';
        setTheme(savedTheme);
    }

    // Auto-dismiss alertas
    setTimeout(() => {
        document.querySelectorAll('#messages-container .alert, .alert.alert-dismissible').forEach(alert => {
            if (typeof bootstrap !== 'undefined') {
                try {
                    const instance = bootstrap.Alert.getOrCreateInstance(alert);
                    if (instance) instance.close();
                } catch (e) {}
            }
        });
    }, 5000);

    // Tooltips
    if (typeof bootstrap !== 'undefined') {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
            new bootstrap.Tooltip(el);
        });
    }

    // HTMX CSRF
    document.body.addEventListener('htmx:configRequest', (event) => {
        const csrfToken = getCookie('csrftoken') ||
            document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (csrfToken) {
            event.detail.headers['X-CSRFToken'] = csrfToken;
        }
    });

    // Confirmação genérica
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', (e) => {
            if (!confirm(el.dataset.confirm || 'Tem certeza?')) {
                e.preventDefault();
            }
        });
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
