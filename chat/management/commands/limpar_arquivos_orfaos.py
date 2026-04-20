
# limpar_arquivos_orfaos.py
import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from chat.models import Message  # ajuste o nome do seu model

class Command(BaseCommand):
    help = 'Remove mensagens cujos arquivos foram deletados do disco'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra o que seria deletado, sem apagar',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Busca todas mensagens do tipo file
        file_messages = Message.objects.filter(message_type='file')
        
        orfas = []
        
        for msg in file_messages:
            try:
                file_data = json.loads(msg.file_data) if isinstance(msg.file_data, str) else msg.file_data
                url = file_data.get('url', '')
                
                if not url:
                    continue
                
                # Converte URL em caminho físico
                relative_path = url.replace(settings.MEDIA_URL, '', 1).lstrip('/')
                full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                
                if not os.path.exists(full_path):
                    orfas.append((msg.id, file_data.get('name', 'sem nome'), full_path))
            
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Erro na msg {msg.id}: {e}'))
        
        if not orfas:
            self.stdout.write(self.style.SUCCESS('✅ Nenhuma mensagem órfã encontrada!'))
            return
        
        self.stdout.write(self.style.WARNING(f'\n📋 {len(orfas)} mensagens órfãs:'))
        for msg_id, nome, path in orfas:
            self.stdout.write(f'  - ID {msg_id}: {nome}')
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 Modo dry-run: nenhuma alteração feita.'))
            self.stdout.write('Execute sem --dry-run para deletar de verdade.')
        else:
            ids = [o[0] for o in orfas]
            deleted = Message.objects.filter(id__in=ids).delete()
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ {deleted[0]} mensagens órfãs removidas do banco.'
            ))

