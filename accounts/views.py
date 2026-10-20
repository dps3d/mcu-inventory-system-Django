from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from .forms import UserRegistrationForm, UserLoginForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            # Повідомлення строго за п. 3.А ТЗ:
            messages.success(
                request,
                "Ваш запит на реєстрацію надіслано адміністратору. Доступ буде активовано після підтвердження заявки."
            )
            return redirect('accounts:login')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    next_url = request.GET.get('next', 'home')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f"Вітаємо, {user.first_name or user.username}! Ви успішно увійшли як авторизований лаборант.")
                    return redirect(request.POST.get('next') or 'home')
                else:
                    messages.warning(
                        request,
                        "Ваш акаунт ще не активовано адміністратором. Будь ласка, зачекайте на схвалення заявки."
                    )
        else:
            # Перевіряємо, чи існує користувач, але він неактивний
            username = request.POST.get('username')
            user_exists = User.objects.filter(username=username).first()
            if user_exists and not user_exists.is_active:
                messages.warning(
                    request,
                    "Ваш акаунт очікує на модерацію. Доступ буде активовано після підтвердження адміністратором."
                )
            else:
                messages.error(request, "Невірний логін або пароль. Спробуйте ще раз.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "Ви вийшли з системи. Режим змінено на гостьовий перегляд.")
    return redirect('home')
