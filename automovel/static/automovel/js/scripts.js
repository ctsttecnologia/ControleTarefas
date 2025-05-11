document.addEventListener('DOMContentLoaded', function() {
    // Assinatura digital
    const signaturePads = document.querySelectorAll('.signature-pad');
    signaturePads.forEach(function(pad) {
        const canvas = pad.querySelector('canvas');
        const clearBtn = pad.querySelector('.clear-signature');
        const hiddenInput = pad.querySelector('input[type="hidden"]');
        
        if (canvas) {
            const signaturePad = new SignaturePad(canvas);
            
            // Redimensionar canvas quando a janela mudar de tamanho
            function resizeCanvas() {
                const ratio = Math.max(window.devicePixelRatio || 1, 1);
                canvas.width = canvas.offsetWidth * ratio;
                canvas.height = canvas.offsetHeight * ratio;
                canvas.getContext('2d').scale(ratio, ratio);
                signaturePad.clear(); // Limpar após redimensionar
            }
            
            window.addEventListener('resize', resizeCanvas);
            resizeCanvas();
            
            // Limpar assinatura
            if (clearBtn) {
                clearBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    signaturePad.clear();
                    if (hiddenInput) hiddenInput.value = '';
                });
            }
            
            // Atualizar campo hidden quando a assinatura mudar
            canvas.addEventListener('mouseup', function() {
                if (!signaturePad.isEmpty()) {
                    if (hiddenInput) hiddenInput.value = signaturePad.toDataURL();
                }
            });
        }
    });
    
    // Modal de manutenções
    const verManutencoesBtn = document.getElementById('verManutencoes');
    if (verManutencoesBtn) {
        verManutencoesBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            fetch('/automovel/api/proxima-manutencao/')
                .then(response => response.json())
                .then(data => {
                    const modalBody = document.getElementById('manutencaoModalBody');
                    let html = '';
                    
                    if (data.length > 0) {
                        html += '<div class="list-group">';
                        data.forEach(function(item) {
                            html += `
                            <a href="/automovel/carros/${item.id}/" class="list-group-item list-group-item-action">
                                <div class="d-flex w-100 justify-content-between">
                                    <h6 class="mb-1">${item.placa} - ${item.modelo}</h6>
                                    <small class="text-${item.dias_restantes <= 0 ? 'danger' : 'warning'}">
                                        ${item.dias_restantes <= 0 ? 'Vencida' : item.dias_restantes + ' dias'}
                                    </small>
                                </div>
                                <small>Próxima manutenção: ${item.data_proxima_manutencao}</small>
                            </a>
                            `;
                        });
                        html += '</div>';
                    } else {
                        html = '<p>Nenhuma manutenção próxima encontrada.</p>';
                    }
                    
                    modalBody.innerHTML = html;
                    
                    // Mostrar modal
                    const modal = new bootstrap.Modal(document.getElementById('manutencaoModal'));
                    modal.show();
                })
                .catch(error => {
                    console.error('Erro ao buscar manutenções:', error);
                });
        });
    }
    
});

