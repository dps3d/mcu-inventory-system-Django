from django.db import migrations


def seed_categories(apps, schema_editor):
    Categories = apps.get_model('catalog', 'Categories')
    initial_categories = [
        {
            "name": "Мікроконтролери",
            "description": "MCU мікросхеми архітектур ARM Cortex, AVR, RISC-V, Xtensa (STM32, ESP32, RP2040, ATmega)."
        },
        {
            "name": "Датчики та сенсори",
            "description": "Сенсори фізичних величин: температури, вологості, тиску, освітлення, IMU, газу."
        },
        {
            "name": "Пасивні компоненти",
            "description": "Базові дискретні компоненти: резистори, керамічні й електролітичні конденсатори, котушки."
        },
        {
            "name": "Комунікаційні модулі",
            "description": "Бездротові та інтерфейсні трансивери: Wi-Fi, BLE, LoRa, RS-485, CAN, Ethernet."
        },
        {
            "name": "Джерела живлення",
            "description": "Лінійні та імпульсні стабілізатори (LDO, Buck, Boost), контролери заряду Li-Ion."
        },
    ]
    for item in initial_categories:
        Categories.objects.get_or_create(
            name=item["name"],
            defaults={"description": item["description"]}
        )


def unseed_categories(apps, schema_editor):
    Categories = apps.get_model('catalog', 'Categories')
    names = [
        "Мікроконтролери",
        "Датчики та сенсори",
        "Пасивні компоненти",
        "Комунікаційні модулі",
        "Джерела живлення"
    ]
    Categories.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_code=unseed_categories),
    ]
