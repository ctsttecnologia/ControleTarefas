
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
    
    // Função para definir o tema, salvar a preferência e ATUALIZAR O ÍCONE
    const setTheme = (theme) => {
        // Altera o atributo no <html> que o Bootstrap usa para os estilos
        htmlElement.setAttribute('data-bs-theme', theme);
        
        // Salva a escolha do usuário no localStorage
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

    // --- INICIALIZAÇÃO DA PÁGINA ---
    // Pega o tema salvo no navegador do usuário. Se não houver, usa 'dark' como padrão.
    const savedTheme = localStorage.getItem('theme') || 'dark';
    
    // Chama a função setTheme() com o tema salvo para aplicar o tema e o ícone corretos.
    setTheme(savedTheme);

    // =================================================================
    // OUTROS SCRIPTS GLOBAIS
    // =================================================================

    // Lógica para fechar alertas automaticamente
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert.alert-dismissible');
        alerts.forEach(alert => {
            if (typeof bootstrap !== 'undefined') {
                new bootstrap.Alert(alert).close();
            }
        });
    }, 5000);

    // Lógica para inicializar tooltips do Bootstrap
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggerList.forEach(tooltipTriggerEl => {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});




