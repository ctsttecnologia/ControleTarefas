
# core/upload_config.py

"""
Configurações centralizadas de upload por app.
Importado pelo settings.py
"""

# Tipos MIME reutilizáveis
MIME_IMAGES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/webp': ['.webp'],
}

MIME_PDF = {
    'application/pdf': ['.pdf'],
}

MIME_OFFICE = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
}

MIME_PPTX = {
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
}

MIME_XML = {
    'application/xml': ['.xml'],
    'text/xml': ['.xml'],
}


# Configuração por app
UPLOAD_CONFIG = {

    'default': {
        'max_size_mb': 4,
        'allowed_types': {**MIME_IMAGES, **MIME_PDF},
    },

    'usuario': {
        'max_size_mb': 4,
        'allowed_types': {**MIME_IMAGES},
    },

    'cliente': {
        'max_size_mb': 15,
        'allowed_types': {**MIME_PDF, **MIME_IMAGES, **MIME_OFFICE},
    },

    'departamento_pessoal': {
        'max_size_mb': 10,
        'allowed_types': {**MIME_PDF, **MIME_IMAGES},
    },

    'departamento_pessoal_foto': {
        'max_size_mb': 4,
        'allowed_types': {**MIME_IMAGES},
    },

    # ══════════════════════════════════════════════════════
    # AUTOMÓVEL — corrigidos de 'extensions' → 'allowed_types'
    # ══════════════════════════════════════════════════════
    'automovel_foto': {
        'max_size_mb': 4,
        'allowed_types': {**MIME_IMAGES},
    },

    'automovel_agendamento': {
        'max_size_mb': 5,
        'allowed_types': {**MIME_IMAGES},
    },

    'automovel_checklist': {
        'max_size_mb': 5,
        'allowed_types': {**MIME_IMAGES},
    },

    'automovel_foto_agendamento': {
        'max_size_mb': 5,
        'allowed_types': {**MIME_IMAGES},
    },

    'seguranca_trabalho': {
        'max_size_mb': 25,
        'allowed_types': {**MIME_PDF, **MIME_IMAGES, **MIME_OFFICE},
    },

    # ══════════════════════════════════════════════════════
    # SUPRIMENTOS — corrigidos de 'extensions' → 'allowed_types'
    # ══════════════════════════════════════════════════════
    'suprimentos_pedido': {
        'max_size_mb': 10,
        'allowed_types': {**MIME_PDF, **MIME_IMAGES},
    },

    'suprimentos_solicitacao': {
        'max_size_mb': 10,
        'allowed_types': {**MIME_PDF, **MIME_IMAGES},
    },

    'tributacao': {
        'max_size_mb': 10,
        'allowed_types': {**MIME_PDF, **MIME_XML},
    },

    'tarefas': {
        'max_size_mb': 15,
        'allowed_types': {**MIME_PDF, **MIME_IMAGES, **MIME_OFFICE},
    },

    'treinamentos': {
        'max_size_mb': 500,                          # vídeos podem ser grandes
        'allowed_extensions': [
            'pdf',                                   # documentos e certificados
            'jpg', 'jpeg', 'png', 'webp',            # imagens de capa e fundo
            'mp4', 'webm', 'ogg',                    # vídeos EAD
        ],
        'allowed_mimes': [
            'application/pdf',
            'image/jpeg', 'image/png', 'image/webp',
            'video/mp4', 'video/webm', 'video/ogg',
        ],
    },

    'gestao_riscos': {
        'max_size_mb': 20,
        'allowed_types': {**MIME_PDF, **MIME_IMAGES, **MIME_OFFICE},
    },

    'ata_reuniao': {
        'max_size_mb': 10,
        'allowed_types': {**MIME_PDF, **MIME_IMAGES},
    },

    'chat_imagens': {
    'max_size_mb': 10,
    'allowed_extensions': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
    'allowed_mimes': [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    ],
    },
    'chat_arquivos': {
        'max_size_mb': 25,
        'allowed_extensions': [
            'pdf', 'doc', 'docx', 'xls', 'xlsx',
            'txt', 'zip', 'rar', 'mp4', 'mp3',
        ],
        'allowed_mimes': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain',
            'application/zip', 'application/x-rar-compressed', 'application/vnd.rar',
            'video/mp4', 'audio/mpeg',
        ],
    },

    'documentos': {
        'max_size_mb': 50,
        'allowed_extensions': [
            'pdf',
            'doc', 'docx',
            'xls', 'xlsx',
            'jpg', 'jpeg', 'png',
            'zip', 'rar',
        ],
        'allowed_mimes': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/jpeg', 'image/png',
            'application/zip',
            'application/x-rar-compressed', 'application/vnd.rar',
        ],
    },

    'pgr_laudos': {
        'max_size_mb': 50,
        'allowed_extensions': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'],
        'allowed_mimes': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/jpeg', 'image/png',
        ],
    },
    'pgr_evidencias': {
        'max_size_mb': 25,
        'allowed_extensions': ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'mp4'],
        'allowed_mimes': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg', 'image/png', 'video/mp4',
        ],
    },
    'pgr_planos_acao_anexos': {
        'max_size_mb': 25,
        'allowed_extensions': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'],
        'allowed_mimes': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/jpeg', 'image/png',
        ],
    },
    'pgr_acompanhamentos': {
        'max_size_mb': 10,
        'allowed_extensions': ['pdf', 'jpg', 'jpeg', 'png'],
        'allowed_mimes': [
            'application/pdf', 'image/jpeg', 'image/png',
        ],
    },
    'pgr_anexos': {
        'max_size_mb': 50,
        'allowed_extensions': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'],
        'allowed_mimes': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/jpeg', 'image/png',
        ],
    },

    'ltcat': {
        'max_size_mb': 25,
        'allowed_types': {**MIME_PDF, **MIME_IMAGES},
    },

    'ltcat_anexos': {
        'max_size_mb': 50,
        'allowed_types': {**MIME_PDF, **MIME_IMAGES, **MIME_OFFICE},
    },

    'ltcat_assinatura': {
        'max_size_mb': 2,
        'allowed_types': {**MIME_IMAGES},
    },
}
