
# treinamentos/privacy.py
import re
import nh3  # pip install nh3

ALLOWED_TAGS = {'p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'h2', 'h3', 'h4',
                'a', 'blockquote', 'code', 'pre', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'img'}
EMBED_HOSTS = ('https://www.youtube.com/embed/', 'https://www.youtube-nocookie.com/embed/',
               'https://player.vimeo.com/video/')


def mascarar_cpf(cpf: str) -> str:
    """123.456.789-01 → ***.456.789-**"""
    d = re.sub(r'\D', '', cpf or '')
    return f'***.{d[3:6]}.{d[6:9]}-**' if len(d) == 11 else '—'


def mascarar_nome(nome: str) -> str:
    """'João Carlos da Silva' → 'João C. d. S.'"""
    partes = (nome or '').split()
    if len(partes) <= 1:
        return nome or '—'
    return ' '.join([partes[0]] + [f'{p[0]}.' for p in partes[1:]])


def sanitizar_html(html: str) -> str:
    return nh3.clean(html or '', tags=ALLOWED_TAGS,
                     attributes={'a': {'href', 'title'}, 'img': {'src', 'alt'}},
                     url_schemes={'https', 'mailto'})


def embed_seguro(url: str) -> str:
    return url if url and url.startswith(EMBED_HOSTS) else ''

