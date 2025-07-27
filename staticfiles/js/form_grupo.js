
// static/jsusuario/form_grupo.js

document.addEventListener('DOMContentLoaded', function() {
    const filterInput = document.getElementById('permission-filter');
    const permissionsContainer = document.getElementById('id_permissions'); // O Django gera este ID
    if (!filterInput || !permissionsContainer) return; // Sai se os elementos não existirem

    const permissionItems = permissionsContainer.querySelectorAll('li');
    const selectAllBtn = document.getElementById('select-all-perms');
    const deselectAllBtn = document.getElementById('deselect-all-perms');

    // Função de Filtro
    filterInput.addEventListener('keyup', function() {
        const searchTerm = filterInput.value.toLowerCase();
        permissionItems.forEach(item => {
            const label = item.querySelector('label').textContent.toLowerCase();
            if (label.includes(searchTerm)) {
                item.style.display = 'list-item';
            } else {
                item.style.display = 'none';
            }
        });
    });

    // Função Selecionar Todas (apenas as visíveis)
    selectAllBtn.addEventListener('click', function() {
        permissionItems.forEach(item => {
            if (item.style.display !== 'none') {
                item.querySelector('input[type="checkbox"]').checked = true;
            }
        });
    });

    // Função Limpar Seleção (apenas as visíveis)
    deselectAllBtn.addEventListener('click', function() {
        permissionItems.forEach(item => {
            if (item.style.display !== 'none') {
                item.querySelector('input[type="checkbox"]').checked = false;
            }
        });
    });
});
