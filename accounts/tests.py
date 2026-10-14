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
