from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Власний DTL-тег для збереження параметрів пошуку, фільтрації та сортування
    при переході між сторінками пагінатора.
    Використання в шаблоні:
        <a href="{% url_replace page=page_obj.next_page_number %}">Наступна</a>
    """
    request = context.get('request')
    if not request:
        return ''
    query = request.GET.copy()
    for key, val in kwargs.items():
        if val is None or val == '':
            query.pop(key, None)
        else:
            query[key] = str(val)
    return f"?{query.urlencode()}" if query else '?'


@register.simple_tag
def stock_status_badge(total_on_hand, min_threshold):
    """
    Власний simple_tag для генерації бейджа наявності компонента на складі.
    """
    qty = total_on_hand or 0
    min_val = min_threshold or 0

    if qty <= 0:
        return mark_safe('<span class="stock-pill stock-none">Немає (0 шт)</span>')
    elif min_val and qty <= min_val:
        return mark_safe(f'<span class="stock-pill stock-low">Закінчується: {qty} шт</span>')
    return mark_safe(f'<span class="stock-pill stock-ok">В наявності: {qty} шт</span>')


@register.inclusion_tag('includes/pagination.html', takes_context=True)
def render_pagination(context, page_obj):
    """
    Власний inclusion_tag для модульного рендерингу пагінатора списків.
    """
    return {
        'page_obj': page_obj,
        'request': context.get('request'),
    }
