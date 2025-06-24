document.addEventListener('DOMContentLoaded', function() {
    // Adicionar novo formulário de participante
    document.getElementById('add-participante').addEventListener('click', function() {
        const formCount = document.getElementById('id_participantes-TOTAL_FORMS');
        const container = document.getElementById('participantes-form-container');
        const newForm = container.querySelector('.participante-form').cloneNode(true);
        const newIndex = parseInt(formCount.value);
        
        // Atualizar todos os IDs e names do novo formulário
        newForm.innerHTML = newForm.innerHTML.replace(/participantes-\d+-/g, `participantes-${newIndex}-`);
        newForm.innerHTML = newForm.innerHTML.replace(/id_participantes-\d+-/g, `id_participantes-${newIndex}-`);
        
        // Limpar valores do novo formulário
        newForm.querySelectorAll('input, select').forEach(input => {
            if (input.type !== 'hidden' && input.name.indexOf('DELETE') === -1) {
                input.value = '';
            }
        });
        
        // Adicionar o novo formulário ao container
        container.appendChild(newForm);
        formCount.value = newIndex + 1;
    });
});
