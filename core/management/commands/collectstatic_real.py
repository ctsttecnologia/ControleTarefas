
from django.contrib.staticfiles.management.commands.collectstatic import Command as RealCollectstatic

class Command(RealCollectstatic):
    pass

# Para usar: python manage.py collectstatic --noinput
# python manage.py collectstatic_real --noinput