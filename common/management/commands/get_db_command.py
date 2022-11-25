from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

PCLIP_AVAILABLE = True
try:
    import pyperclip as pc
except ImportError:
    PCLIP_AVAILABLE = False


def get_command(db, user, password):
    line = ""
    line += f"CREATE DATABASE {db};\n"
    line += f"CREATE USER {user} WITH PASSWORD '{password}';\n"
    line += f"ALTER ROLE {user} SET client_encoding TO 'utf8';\n"
    line += f"ALTER ROLE {user} SET default_transaction_isolation TO 'read committed';\n"
    line += f"ALTER ROLE {user} SET timezone TO 'Asia/Kolkata';\n"
    line += f"GRANT ALL PRIVILEGES ON DATABASE {db} TO {user};\n"
    line += f"ALTER ROLE {user} SUPERUSER;"

    return line


class Command(BaseCommand):
    help = "Generates postgres database creation command"

    def handle(self, *args, **options):
        try:
            command = get_command(
                db=settings.DATABASES["default"]["NAME"],
                user=settings.DATABASES["default"]["USER"],
                password=settings.DATABASES["default"]["PASSWORD"],
            )

            if PCLIP_AVAILABLE:
                pc.copy(command)
                self.stdout.write(self.style.SUCCESS("Command copied to clipboard"))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Clipboard not working, Install pyperclip to copy to clipboard, pip install pyperclip"
                    )
                )
                self.stdout.write(self.style.WARNING("-" * 100))
                self.stdout.write(self.style.SUCCESS(command))
        except Exception as e:
            raise CommandError(e)
