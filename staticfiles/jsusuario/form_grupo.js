
/// static/jsusuario/form_grupo.js
// Responsabilidade: Filtro e seleção de permissões no formulário de Grupo

document.addEventListener('DOMContentLoaded', function () {
    const filterInput = document.getElementById('permission-filter');
    const permissionsContainer = document.getElementById('id_permissions');

    // Guard: só executa se os elementos existirem
    if (!filterInput || !permissionsContainer) return;

    const permissionItems = permissionsContainer.querySelectorAll('li');
    const selectAllBtn = document.getElementById('select-all-perms');
    const deselectAllBtn = document.getElementById('deselect-all-perms');

    // ═══════════════════════════════════════
    // FILTRO DE PERMISSÕES
    // ═══════════════════════════════════════
    filterInput.addEventListener('keyup', function () {
        const searchTerm = this.value.toLowerCase().trim();

        permissionItems.forEach(item => {
            const label = item.querySelector('label');
            if (!label) return;

            const text = label.textContent.toLowerCase();
            item.style.display = text.includes(searchTerm) ? '' : 'none';
        });

        // Atualiza contador de visíveis
        updateVisibleCount();
    });

    // ═══════════════════════════════════════
    // SELECIONAR TODAS (apenas visíveis)
    // ═══════════════════════════════════════
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function () {
            permissionItems.forEach(item => {
                if (item.style.display !== 'none') {
                    const checkbox = item.querySelector('input[type="checkbox"]');
                    if (checkbox) checkbox.checked = true;
                }
            });
            updateSelectedCount();
        });
    }

    // ═══════════════════════════════════════
    // LIMPAR SELEÇÃO (apenas visíveis)
    // ═══════════════════════════════════════
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', function () {
            permissionItems.forEach(item => {
                if (item.style.display !== 'none') {
                    const checkbox = item.querySelector('input[type="checkbox"]');
                    if (checkbox) checkbox.checked = false;
                }
            });
            updateSelectedCount();
        });
    }

    // ═══════════════════════════════════════
    // CONTADORES (opcional, mas útil)
    // ═══════════════════════════════════════
    const countDisplay = document.getElementById('permission-count');

    function updateVisibleCount() {
        if (!countDisplay) return;
        const visible = [...permissionItems].filter(item => item.style.display !== 'none').length;
        const total = permissionItems.length;
        countDisplay.textContent = `${visible} de ${total} permissões`;
    }

    function updateSelectedCount() {
        const selected = permissionsContainer.querySelectorAll('input[type="checkbox"]:checked').length;
        const badge = document.getElementById('selected-perms-count');
        if (badge) badge.textContent = `${selected} selecionadas`;
    }

    // Atualiza contagem ao carregar
    updateVisibleCount();
    updateSelectedCount();

    // Atualiza ao clicar em qualquer checkbox
    permissionsContainer.addEventListener('change', updateSelectedCount);
});
