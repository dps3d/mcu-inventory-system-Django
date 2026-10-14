from django.core.management.base import BaseCommand
from catalog.models import Categories, Components
from inventory.models import StorageLocations, InventoryStocks


class Command(BaseCommand):
    help = "Наповнює базу даних демонстраційними категоріями, компонентами та залишками"

    def handle(self, *args, **options):
        self.stdout.write("Початок наповнення каталогу компонентів...")

        # 1. Категорії
        cat_mcu, _ = Categories.objects.get_or_create(
            name="Мікроконтролери",
            defaults={"description": "Мікроконтролери STM32, AVR, ESP32, RP2040 тощо"}
        )
        cat_sensors, _ = Categories.objects.get_or_create(
            name="Датчики та сенсори",
            defaults={"description": "Датчики температури, тиску, вологості, IMU"}
        )
        cat_interface, _ = Categories.objects.get_or_create(
            name="Інтерфейсні мікросхеми",
            defaults={"description": "USB-UART перетворювачі, драйвери шин RS-485, CAN"}
        )
        cat_power, _ = Categories.objects.get_or_create(
            name="Джерела живлення",
            defaults={"description": "Лінійні та імпульсні стабілізатори напруги LDO, DC-DC"}
        )
        cat_passives, _ = Categories.objects.get_or_create(
            name="Пасивні компоненти",
            defaults={"description": "Резистори, керамічні та електролітичні конденсатори"}
        )

        # 2. Складські комірки
        loc_mcu1, _ = StorageLocations.objects.get_or_create(
            box_number="MCU-BOX-1",
            shelf="Полиця 1",
            cell_code="M-01"
        )
        loc_mcu2, _ = StorageLocations.objects.get_or_create(
            box_number="MCU-BOX-1",
            shelf="Полиця 1",
            cell_code="M-02"
        )
        loc_sens, _ = StorageLocations.objects.get_or_create(
            box_number="SENSORS-A",
            shelf="Полиця 2",
            cell_code="S-05"
        )
        loc_power, _ = StorageLocations.objects.get_or_create(
            box_number="PWR-MODULES",
            shelf="Полиця 3",
            cell_code="P-12"
        )
        loc_passives, _ = StorageLocations.objects.get_or_create(
            box_number="SMD-REEL-01",
            shelf="Полиця 4",
            cell_code="R-100"
        )

        # 3. Компоненти
        components_data = [
            {
                "category": cat_mcu,
                "part_number": "STM32F103C8T6",
                "package_type": "LQFP-48",
                "value_nominal": "72MHz, 64KB Flash, 20KB RAM",
                "specifications": "32-бітний ARM Cortex-M3 мікроконтролер. Живлення 2.0-3.6V. 2x SPI, 2x I2C, 3x USART, USB 2.0 Full Speed, CAN 2.0B. Робоча температура -40°C..+85°C.",
                "min_threshold": 10,
                "datasheet_url": "https://www.st.com/resource/en/datasheet/stm32f103c8.pdf",
                "stock": (loc_mcu1, 45, 5, 65.50),
            },
            {
                "category": cat_mcu,
                "part_number": "ATmega328P-PU",
                "package_type": "DIP-28",
                "value_nominal": "16MHz, 32KB Flash, 2KB SRAM",
                "specifications": "8-бітний високопродуктивний AVR мікроконтролер з низьким енергоспоживанням. 23 лінії вводу/виводу, 6-канальний 10-бітний АЦП. Ідеально підходить для breadboard-макетування.",
                "min_threshold": 15,
                "datasheet_url": "https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-7810-Automotive-Microcontrollers-ATmega328P_Datasheet.pdf",
                "stock": (loc_mcu1, 30, 2, 85.00),
            },
            {
                "category": cat_mcu,
                "part_number": "ESP32-WROOM-32D",
                "package_type": "Module",
                "value_nominal": "240MHz Dual-Core, 4MB Flash",
                "specifications": "Потужний модуль Wi-Fi + Bluetooth/BLE на базі SoC ESP32-D0WD. Вбудована PCB-антена, багатий набір периферії: ємнісні сенсори, датчик Холла, SDIO, UART, SPI.",
                "min_threshold": 8,
                "datasheet_url": "https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32d_esp32-wroom-32u_datasheet_en.pdf",
                "stock": (loc_mcu2, 18, 0, 140.00),
            },
            {
                "category": cat_mcu,
                "part_number": "RP2040",
                "package_type": "QFN-56",
                "value_nominal": "133MHz Dual Cortex-M0+, 264KB SRAM",
                "specifications": "Перший мікроконтролер від Raspberry Pi. Унікальна периферія програмованого вводу/виводу (PIO), підтримка завантаження через USB UF2.",
                "min_threshold": 12,
                "datasheet_url": "https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf",
                "stock": (loc_mcu2, 8, 3, 42.00),  # низький залишок
            },
            {
                "category": cat_sensors,
                "part_number": "BME280",
                "package_type": "LGA-8",
                "value_nominal": "T/P/H Sensor, I2C/SPI",
                "specifications": "Комбінований високоточний цифровий датчик температури, атмосферного тиску та відносної вологості повітря від Bosch Sensortec.",
                "min_threshold": 5,
                "datasheet_url": "https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf",
                "stock": (loc_sens, 14, 0, 95.00),
            },
            {
                "category": cat_sensors,
                "part_number": "MPU-6050",
                "package_type": "QFN-24",
                "value_nominal": "6-DOF IMU, I2C",
                "specifications": "6-осьовий інерційний вимірювальний модуль (3-осьовий гіроскоп + 3-осьовий акселерометр) з апаратним обчислювачем DMP.",
                "min_threshold": 6,
                "datasheet_url": "https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf",
                "stock": (loc_sens, 0, 0, 110.00),  # немає на складі
            },
            {
                "category": cat_interface,
                "part_number": "CH340G",
                "package_type": "SOP-16",
                "value_nominal": "USB to UART Bridge",
                "specifications": "Популярний USB-UART міст для програмування мікроконтролерів та зв'язку з комп'ютером.",
                "min_threshold": 10,
                "datasheet_url": "https://datasheet.lcsc.com/lcsc/1811151441_Jiangsu-Qin-Heng-CH340G_C14258.pdf",
                "stock": (loc_power, 25, 0, 18.50),
            },
            {
                "category": cat_interface,
                "part_number": "MAX485ESA",
                "package_type": "SOIC-8",
                "value_nominal": "RS-485 / RS-422 Transceiver",
                "specifications": "Диференційний трансівер для напівдуплексних промислових мереж RS-485/422. Живлення 5V.",
                "min_threshold": 10,
                "datasheet_url": "https://www.analog.com/media/en/technical-documentation/data-sheets/MAX1487-MAX491.pdf",
                "stock": (loc_power, 22, 2, 24.00),
            },
            {
                "category": cat_power,
                "part_number": "AMS1117-3.3",
                "package_type": "SOT-223",
                "value_nominal": "LDO 3.3V, 1A",
                "specifications": "Низькопадінковий лінійний стабілізатор напруги 3.3V із вихідним струмом до 1000мА. Захист від теплового перевантаження.",
                "min_threshold": 20,
                "datasheet_url": "http://www.advanced-monolithic.com/pdf/ds1117.pdf",
                "stock": (loc_power, 65, 0, 6.20),
            },
            {
                "category": cat_passives,
                "part_number": "RC0805JR-0710KL",
                "package_type": "0805",
                "value_nominal": "10 кОм, 5%",
                "specifications": "SMD товстоплівковий резистор 0805, розсіювана потужність 0.125W. Для підтяжки ліній I2C/Reset.",
                "min_threshold": 100,
                "datasheet_url": "",
                "stock": (loc_passives, 350, 0, 0.40),
            },
            {
                "category": cat_passives,
                "part_number": "CC0805KRX7R9BB104",
                "package_type": "0805",
                "value_nominal": "100 нФ, 50V, X7R",
                "specifications": "Керамічний SMD конденсатор 0805 для фільтрації високочастотних завад живлення мікросхем.",
                "min_threshold": 150,
                "datasheet_url": "",
                "stock": (loc_passives, 400, 0, 0.60),
            },
        ]

        created_components = 0
        for item in components_data:
            loc, qty, res, price = item.pop("stock")
            comp, created = Components.objects.get_or_create(
                part_number=item["part_number"],
                defaults=item
            )
            if created:
                created_components += 1

            # Створюємо залишок на складі
            InventoryStocks.objects.get_or_create(
                component=comp,
                location=loc,
                defaults={
                    "quantity_on_hand": qty,
                    "quantity_reserved": res,
                    "unit_price": price,
                }
            )

        self.stdout.write(self.style.SUCCESS(
            f"Каталог успішно наповнено! Створено {created_components} нових компонентів з реальними залишками."
        ))
