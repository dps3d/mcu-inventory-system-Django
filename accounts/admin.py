from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe


admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'account_status_badge',
        'is_staff',
        'date_joined',
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined')
    actions = ['approve_selected_users', 'deactivate_selected_users']

    def account_status_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span style="background: rgba(139, 179, 129, 0.2); color: #2d7a22; font-weight: 600; padding: 2px 8px; border-radius: 9999px; font-size: 11px;">Активний</span>'
            )
        return mark_safe(
            '<span style="background: rgba(194, 155, 56, 0.2); color: #9c6c0a; font-weight: 600; padding: 2px 8px; border-radius: 9999px; font-size: 11px;">Очікує схвалення</span>'
        )
    account_status_badge.short_description = "Статус модерації"

    @admin.action(description="Схвалити вибрані заявки (активувати користувачів)")
    def approve_selected_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Успішно активовано {updated} користувачів. Тепер вони мають доступ до системи.")

    @admin.action(description="Деактивувати вибраних користувачів")
    def deactivate_selected_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивовано {updated} користувачів.")
