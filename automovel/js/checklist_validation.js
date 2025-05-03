document.addEventListener('DOMContentLoaded', function() {
    // Obtém referências aos campos
    const kmInicial = document.querySelector('#id_km_inicial');
    const kmFinal = document.querySelector('#id_km_final');
    const tipo = document.querySelector('#id_tipo');
    
    // Função de validação
    function validateKm() {
        if (kmInicial.value && kmFinal.value) {
            if (parseInt(kmFinal.value) < parseInt(kmInicial.value)) {
                alert('A quilometragem final não pode ser menor que a inicial!');
                kmFinal.value = '';
                kmFinal.focus();
            }
        }
    }
    
    // Adiciona listeners
    if (kmFinal) {
        kmFinal.addEventListener('change', validateKm);
    }
    
    // Validação para tipo 'retorno'
    if (tipo) {
        tipo.addEventListener('change', function() {
            if (this.value === 'retorno' && !kmFinal.value) {
                alert('Checklist de retorno requer quilometragem final!');
            }
        });
    }
});

