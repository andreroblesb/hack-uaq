from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.sessions.models import Session

class Command(BaseCommand):
    help = 'Elimina todas las sesiones almacenadas.'

    def handle(self, *args, **kwargs):
        call_command('clearsessions')
        Session.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Todas las sesiones han sido eliminadas.'))
