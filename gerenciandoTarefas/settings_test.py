
from gerenciandoTarefas.settings import *

# Desativa redirecionamento SSL nos testes
SECURE_SSL_REDIRECT = False

# Permite o host 'testserver' usado pelo Django TestClient
ALLOWED_HOSTS = ['*']




# Adicione ao seu perfil do PowerShell (~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1)

#function djtest { python manage.py test $args --settings=gerenciandoTarefas.settings_test -v 2 }

#djtest notifications
#djtest chat
#djtest tarefas



