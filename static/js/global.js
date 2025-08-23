// static/js/global.js


document.addEventListener('DOMContentLoaded', () => {
    const themeSwitcherBtn = document.getElementById('theme-switcher-btn');
    if (!themeSwitcherBtn) {
        // Se o botão não existir na página, não faz nada.
        return;
    }

    const htmlElement = document.documentElement;
    const lightIcon = themeSwitcherBtn.querySelector('.theme-icon-light');
    const darkIcon = themeSwitcherBtn.querySelector('.theme-icon-dark');
    
    // Função para definir o tema e salvar a preferência
    const setTheme = (theme) => {
        // Altera o atributo no <html> que o seu CSS usa para aplicar os estilos
        htmlElement.setAttribute('data-bs-theme', theme);
        
        // Salva a escolha do usuário no localStorage para lembrar na próxima visita
        localStorage.setItem('theme', theme);

        // Atualiza qual ícone está visível
        if (theme === 'dark') {
            lightIcon.classList.add('d-none');
            darkIcon.classList.remove('d-none');
        } else {
            darkIcon.classList.add('d-none');
            lightIcon.classList.remove('d-none');
        }
    };

    // Adiciona o evento de clique ao botão
    themeSwitcherBtn.addEventListener('click', () => {
        const currentTheme = htmlElement.getAttribute('data-bs-theme');
        // Se o tema atual for escuro, muda para claro, e vice-versa.
        setTheme(currentTheme === 'dark' ? 'light' : 'dark');
    });

    // Garante que o ícone correto seja exibido quando a página carrega
    const currentTheme = localStorage.getItem('theme') || 'light';
    if (currentTheme === 'dark') {
        lightIcon.classList.add('d-none');
        darkIcon.classList.remove('d-none');
    } else {
        darkIcon.classList.add('d-none');
        lightIcon.classList.remove('d-none');
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