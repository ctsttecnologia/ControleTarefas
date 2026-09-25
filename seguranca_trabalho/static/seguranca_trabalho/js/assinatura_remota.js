// Função para gerar link de assinatura remota
async function gerarLinkAssinatura(appLabel, modelName, objectId, btnEl) {
    const url = `/core/assinatura-remota/gerar/${appLabel}/${modelName}/${objectId}/`;
    btnEl.disabled = true;
    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
        });
        const data = await resp.json();
        if (data.ok) {
            await navigator.clipboard.writeText(data.link);
            alert('Link copiado! Válido até ' + new Date(data.expira_em).toLocaleString('pt-BR'));
        } else {
            alert('Erro ao gerar link.');
        }
    } catch (e) {
        alert('Erro na requisição.');
    } finally {
        btnEl.disabled = false;
    }
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}
