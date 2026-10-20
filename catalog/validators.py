import re
from django.core.exceptions import ValidationError


def validate_part_number(value):
    """
    Власний валідатор формату партнер-номера / маркування електронного компонента.
    Перевіряє, що маркування складається лише з коректних символів:
    латинських літер, цифр, знаків дефісу, підкреслення, крапки, слешу та плюсу.
    """
    if not value or not str(value).strip():
        raise ValidationError(
            "Парт-номер не може бути порожнім.",
            code='empty_part_number'
        )

    clean_value = str(value).strip()
    # Дозволені лише друковані латинські символи, цифри та розповсюджені роздільники
    pattern = r'^[A-Za-z0-9\-_./+\s]+$'
    if not re.match(pattern, clean_value):
        raise ValidationError(
            "Парт-номер містить неприпустимі символи. Дозволяються лише латинські літери (A-Z, a-z), цифри та знаки (-, _, ., /, +).",
            code='invalid_part_number_format'
        )
