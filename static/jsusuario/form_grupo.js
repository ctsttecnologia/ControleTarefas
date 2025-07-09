
// static/js/form_grupo.js

document.addEventListener('DOMContentLoaded', function() {
    const filterInput = document.getElementById('permission-filter');
    // CORREÇÃO: Buscamos pela classe que definimos no widget
    const permissionsContainer = document.querySelector('.permissions-list'); 
    
    if (!filterInput || !permissionsContainer) {
        console.warn("Componentes do formulário de grupo (filtro ou container de permissões) não encontrados.");
        return; // Sai se os elementos não existirem
    }

    // O Django renderiza cada checkbox dentro de um <label>, vamos usá-lo como item.
    const permissionItems = permissionsContainer.querySelectorAll('label'); 
    const selectAllBtn = document.getElementById('select-all-perms');
    const deselectAllBtn = document.getElementById('deselect-all-perms');

    // Função de Filtro (continua igual)
    filterInput.addEventListener('keyup', function() {
        const searchTerm = filterInput.value.toLowerCase();
        permissionItems.forEach(item => {
            const labelText = item.textContent.toLowerCase();
            // CORREÇÃO: O elemento pai do <label> é o <li> ou <div> que queremos esconder
            if (labelText.includes(searchTerm)) {
                item.parentElement.style.display = 'block';
            } else {
                item.parentElement.style.display = 'none';
            }
        });
    });

    // Função Selecionar Todas
    selectAllBtn.addEventListener('click', function() {
        permissionItems.forEach(item => {
            if (item.parentElement.style.display !== 'none') {
                item.querySelector('input[type="checkbox"]').checked = true;
            }
        });
    });

    // Função Limpar Seleção
    deselectAllBtn.addEventListener('click', function() {
        permissionItems.forEach(item => {
            if (item.parentElement.style.display !== 'none') {
                item.querySelector('input[type="checkbox"]').checked = false;
            }
        });
    });
});
