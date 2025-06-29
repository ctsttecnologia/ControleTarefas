
// static/js/global.js

document.addEventListener('DOMContentLoaded', () => {

    // --- LÓGICA DO TEMA CLARO/ESCURO ---
    
    // Elementos que vamos manipular
    const themeToggleButton = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement; // A tag <html>

    // Ícones de Sol e Lua (do Bootstrap Icons)
    const sunIcon = `<i class="bi bi-sun-fill"></i>`;
    const moonIcon = `<i class="bi bi-moon-stars-fill"></i>`;

    // Função que aplica o tema visualmente e salva a escolha
    const applyTheme = (theme) => {
        // Define o atributo 'data-bs-theme' no elemento <html>, que o CSS usa para mudar as cores
        htmlElement.setAttribute('data-bs-theme', theme);
        // Salva a escolha no localStorage do navegador para lembrar na próxima visita
        localStorage.setItem('theme', theme);
        // Atualiza o ícone do botão
        themeToggleButton.innerHTML = theme === 'dark' ? sunIcon : moonIcon;
    };

    // Adiciona o evento de clique ao botão
    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', () => {
            // Verifica qual é o tema atual para saber para qual tema mudar
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(newTheme);

            if (typeof window.recreateAnalyticCharts === 'function') {
                window.recreateAnalyticCharts(); // Para o novo dashboard
            }
            if (typeof window.recreateTaskCharts === 'function') {
                window.recreateTaskCharts();
            }
        });
    }

    // Aplica o tema salvo quando a página carrega pela primeira vez
    const savedTheme = localStorage.getItem('theme') || 'light'; // Se não houver nada salvo, o padrão é 'light'
    applyTheme(savedTheme);


    // --- OUTROS SCRIPTS GLOBAIS ---

    // Lógica para fechar alertas automaticamente
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert.alert-dismissible');
        alerts.forEach(alert => {
            // Garante que o Bootstrap já carregou antes de tentar usar
            if (typeof bootstrap !== 'undefined') {
                new bootstrap.Alert(alert).close();
            }
        });
    }, 5000);

    // Lógica para inicializar tooltips
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

});

