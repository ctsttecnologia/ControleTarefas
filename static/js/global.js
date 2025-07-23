// static/js/global.js

document.addEventListener('DOMContentLoaded', () => {

    // =================================================================
    // LÓGICA DO TEMA CLARO/ESCURO
    // =================================================================
    
    const themeToggleButton = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;
    
    // RECOMENDAÇÃO: Mover a definição dos ícones para constantes no topo
    const sunIcon = `<i class="bi bi-sun-fill"></i>`;
    const moonIcon = `<i class="bi bi-moon-stars-fill"></i>`;

    // Função única para atualizar o ícone do botão com base no tema atual
    const updateThemeIcon = () => {
        const currentTheme = htmlElement.getAttribute('data-bs-theme');
        if (themeToggleButton) {
            themeToggleButton.innerHTML = currentTheme === 'dark' ? sunIcon : moonIcon;
        }
    };

    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', () => {
            // Alterna o tema
            const newTheme = htmlElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
            htmlElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Atualiza o ícone
            updateThemeIcon();

            // Recria os gráficos se as funções existirem (ótima prática!)
            if (typeof window.recreateAnalyticCharts === 'function') {
                window.recreateAnalyticCharts();
            }
            if (typeof window.recreateTaskCharts === 'function') {
                window.recreateTaskCharts();
            }
        });
    }

    // --- INICIALIZAÇÃO DA PÁGINA ---
    // Apenas atualiza o ícone na carga inicial. O tema já foi setado pelo script no <head>.
    updateThemeIcon();


    // =================================================================
    // OUTROS SCRIPTS GLOBAIS
    // =================================================================

    // Lógica para fechar alertas automaticamente (código já está ótimo)
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert.alert-dismissible');
        alerts.forEach(alert => {
            if (typeof bootstrap !== 'undefined') {
                new bootstrap.Alert(alert).close();
            }
        });
    }, 5000); // Fecha após 5 segundos

    // Lógica para inicializar tooltips do Bootstrap
    if (typeof bootstrap !== 'undefined') {
        // RECOMENDAÇÃO: Sintaxe mais moderna e semanticamente correta com forEach
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggerList.forEach(tooltipTriggerEl => {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

});