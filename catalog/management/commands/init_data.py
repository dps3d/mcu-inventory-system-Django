import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User
from catalog.models import Components


class Command(BaseCommand):
    help = "Автоматично наповнює порожню базу даних фікстурами та створює адміна"

    def handle(self, *args, **options):
        # 1. Завантаження початкових даних (компоненти, склад, категорії, проекти)
        comp_count = Components.objects.count()
        if comp_count == 0:
            self.stdout.write(self.style.NOTICE("==> База порожня. Завантажуємо фікстури fixtures/seed_data.json..."))
            try:
                call_command('loaddata', 'fixtures/seed_data.json')
                new_count = Components.objects.count()
                self.stdout.write(self.style.SUCCESS(f"==> Успішно завантажено {new_count} компонентів та повний склад!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"==> Помилка при завантаженні фікстур: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"==> База вже містить дані ({comp_count} компонентів). Пропускаємо seeding."))

        # 2. Створення адміністратора (суперкористувача), якщо ще немає жодного
        if not User.objects.filter(is_superuser=True).exists():
            admin_username = os.environ.get('ADMIN_USER', 'admin')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin12345')
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

            User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"==> Створено суперкористувача: логін '{admin_username}', пароль '{admin_password}'"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("==> Суперкористувач вже існує. Пропускаємо створення."))
