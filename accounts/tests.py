from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


class AccountsModerationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')

    def test_registration_creates_inactive_user(self):
        """Перевірка: реєстрація створює користувача з is_active = False"""
        response = self.client.post(self.register_url, {
            'username': 'new_engineer',
            'first_name': 'Тарас',
            'last_name': 'Шевченко',
            'email': 'taras@lab.edu',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!',
        }, follow=True)

        self.assertEqual(response.status_code, 200)

        # Перевіряємо створення в базі
        user = User.objects.filter(username='new_engineer').first()
        self.assertIsNotNone(user)
        self.assertFalse(user.is_active, "Користувач після реєстрації повинен мати is_active = False!")

        # Перевіряємо повідомлення модерації
        messages = list(response.context['messages'])
        self.assertTrue(any("Ваш запит на реєстрацію надіслано адміністратору" in m.message for m in messages))

    def test_inactive_user_cannot_login_until_approved(self):
        """Перевірка: неактивний користувач не може увійти, доки адмін не змінить is_active на True"""
        user = User.objects.create_user(
            username='pending_user',
            email='pending@lab.edu',
            password='Password123!',
            is_active=False
        )

        # Спроба входу неактивного користувача
        response = self.client.post(self.login_url, {
            'username': 'pending_user',
            'password': 'Password123!',
        }, follow=True)

        self.assertFalse(response.context['user'].is_authenticated)

        # Адміністратор схвалює користувача (is_active = True)
        user.is_active = True
        user.save()

        # Тепер користувач успішно входить
        response_approved = self.client.post(self.login_url, {
            'username': 'pending_user',
            'password': 'Password123!',
        }, follow=True)

        self.assertTrue(response_approved.context['user'].is_authenticated)

    def test_admin_account_status_badge_no_typeerror(self):
        """Перевірка: бейдж статусу в адмінці генерується без TypeError (format_html)"""
        from django.contrib.admin.sites import AdminSite
        from accounts.admin import CustomUserAdmin

        admin_instance = CustomUserAdmin(User, AdminSite())
        active_user = User(username='active_guy', is_active=True)
        inactive_user = User(username='pending_guy', is_active=False)

        badge_active = admin_instance.account_status_badge(active_user)
        badge_inactive = admin_instance.account_status_badge(inactive_user)

        self.assertIn("Активний", badge_active)
        self.assertIn("Очікує схвалення", badge_inactive)

    def test_db_health_context_processor(self):
        """Перевірка: контекстний процесор health check повертає db_healthy=True при робочій БД"""
        from config.context_processors import db_health_status
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        status = db_health_status(request)
        self.assertIn('db_healthy', status)
        self.assertTrue(status['db_healthy'])

    def test_admin_user_changelist_and_change_view(self):
        """Перевірка: сторінка списку користувачів та форма редагування відкриваються без помилок"""
        admin_user = User.objects.create_superuser(
            username='super_test',
            email='super@lab.edu',
            password='SuperPassword123!'
        )
        self.client.force_login(admin_user)

        # 1. Список користувачів
        resp_list = self.client.get('/admin/auth/user/')
        self.assertEqual(resp_list.status_code, 200)

        # 2. Форма редагування конкретного користувача
        resp_change = self.client.get(f'/admin/auth/user/{admin_user.id}/change/')
        self.assertEqual(resp_change.status_code, 200)

    def test_admin_top_button_rendered_for_staff(self):
        """Перевірка: кнопка переходу в адмінку зліва зверху відображається для staff і прихована для гостей"""
        # Гість не бачить кнопку
        resp_guest = self.client.get('/')
        self.assertNotContains(resp_guest, 'admin-top-btn')

        # Адміністратор / персонал бачить кнопку
        admin_user = User.objects.create_superuser(
            username='staff_test',
            email='staff@lab.edu',
            password='StaffPassword123!'
        )
        self.client.force_login(admin_user)
        resp_admin = self.client.get('/')
        self.assertContains(resp_admin, 'admin-top-btn')
        self.assertContains(resp_admin, '/admin/')

    def test_passwords_are_securely_hashed(self):
        """Перевірка: паролі в базі даних зберігаються виключно у захешованому вигляді (PBKDF2 SHA256)"""
        raw_password = 'MySecretLabPassword2026!'
        user = User.objects.create_user(
            username='hash_test_user',
            password=raw_password
        )
        # Сирий пароль ніде не збережено
        self.assertNotEqual(user.password, raw_password)
        # Повинен починатися з pbkdf2_sha256 або іншого алгоритму хешування Django
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
        # Перевірка пароля працює коректно
        self.assertTrue(user.check_password(raw_password))
        self.assertFalse(user.check_password('WrongPassword!'))


