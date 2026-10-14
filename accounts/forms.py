from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError


class UserRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label="Ім'я",
        widget=forms.TextInput(attrs={'placeholder': "Введіть ваше ім'я", 'class': 'form-input'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label="Прізвище",
        widget=forms.TextInput(attrs={'placeholder': 'Введіть ваше прізвище', 'class': 'form-input'})
    )
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={'placeholder': 'lab@university.edu', 'class': 'form-input'})
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={'placeholder': 'Надійний пароль', 'class': 'form-input'})
    )
    password_confirm = forms.CharField(
        label="Підтвердження паролю",
        widget=forms.PasswordInput(attrs={'placeholder': 'Повторіть пароль', 'class': 'form-input'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        labels = {
            'username': "Логін (ім'я користувача)",
        }
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'напр. engineer_alex', 'class': 'form-input'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Користувач із такою електронною поштою вже зареєстрований.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Введені паролі не збігаються.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        # За ТЗ (п. 3.А): новостворений користувач НЕАКТИВНИЙ до модерації адміністратором
        user.is_active = False
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Логін",
        widget=forms.TextInput(attrs={'placeholder': "Введіть логін", 'class': 'form-input', 'autofocus': True})
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={'placeholder': "Введіть пароль", 'class': 'form-input'})
    )
