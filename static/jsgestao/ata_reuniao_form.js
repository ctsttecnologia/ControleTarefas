
// static/jsgestao/ata_reuniao_form.js
// Responsabilidade: Formset dinâmico de participantes da Ata de Reunião

document.addEventListener('DOMContentLoaded', function () {
    const addButton = document.getElementById('add-participante');
    const formCountInput = document.getElementById('id_participantes-TOTAL_FORMS');
    const container = document.getElementById('participantes-form-container');

    // Guard: só executa na página de Ata de Reunião
    if (!addButton || !formCountInput || !container) return;

    addButton.addEventListener('click', function () {
        const templateForm = container.querySelector('.participante-form');
        if (!templateForm) {
            console.warn('[AtaReuniao] Template de formulário de participante não encontrado.');
            return;
        }

        const newIndex = parseInt(formCountInput.value, 10);
        const newForm = templateForm.cloneNode(true);

        // Atualiza IDs e names para o novo índice
        newForm.innerHTML = newForm.innerHTML
            .replace(/participantes-\d+-/g, `participantes-${newIndex}-`)
            .replace(/id_participantes-\d+-/g, `id_participantes-${newIndex}-`);

        // Limpa valores do novo formulário
        newForm.querySelectorAll('input, select, textarea').forEach(input => {
            if (input.type === 'hidden' && input.name.includes('DELETE')) return;
            if (input.type === 'hidden' && input.name.includes('id')) {
                input.value = '';
                return;
            }
            if (input.tagName === 'SELECT') {
                input.selectedIndex = 0;
            } else if (input.type !== 'hidden') {
                input.value = '';
            }
        });

        // Adiciona botão de remover
        const removeBtn = newForm.querySelector('[data-remove-form]');
        if (removeBtn) {
            removeBtn.addEventListener('click', function () {
                newForm.style.display = 'none';
                const deleteInput = newForm.querySelector('input[name*="DELETE"]');
                if (deleteInput) deleteInput.value = 'on';
            });
        }

        container.appendChild(newForm);
        formCountInput.value = newIndex + 1;

        // Anima entrada
        newForm.classList.add('fade-in');
    });

    // Event delegation para botões de remover existentes
    container.addEventListener('click', function (e) {
        const removeBtn = e.target.closest('[data-remove-form]');
        if (!removeBtn) return;

        const formRow = removeBtn.closest('.participante-form');
        if (!formRow) return;

        formRow.style.display = 'none';
        const deleteInput = formRow.querySelector('input[name*="DELETE"]');
        if (deleteInput) deleteInput.value = 'on';
    });
});
