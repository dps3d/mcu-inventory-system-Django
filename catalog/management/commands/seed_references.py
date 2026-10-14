from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import Categories
from inventory.models import StorageLocations, Suppliers


class Command(BaseCommand):
    help = "Заповнює базу даних стандартними категоріями, комірками та постачальниками"

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистити існуючі категорії та довідники перед заповненням',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING("Очищення попередніх довідників..."))
            with transaction.atomic():
                Categories.objects.all().delete()
                StorageLocations.objects.all().delete()
                Suppliers.objects.all().delete()

        with transaction.atomic():
            # =========================================================================
            # 1. КАТЕГОРІЇ (з ієрархією батьківських та дочірніх)
            # =========================================================================
            cat_structure = [
                {
                    "name": "Мікроконтролери та процесори",
                    "description": "Центральні мікроконтролери (MCU), процесори та системи на кристалі (SoC)",
                    "children": [
                        ("STM32 (ARM Cortex-M)", "Мікроконтролери сімейства STM32F0, F1, F4, G0 тощо"),
                        ("AVR / ATmega / ATtiny", "Класичні 8-бітні мікроконтролери Microchip/Atmel"),
                        ("ESP32 / ESP8266 (Wi-Fi/BLE)", "Бездротові мікроконтролери Espressif"),
                        ("Raspberry Pi / RP2040", "Двоядерні ARM Cortex-M0+ чіпи RP2040 та модулі Pico"),
                        ("PIC / dsPIC", "Мікроконтролери серій PIC16, PIC18, dsPIC"),
                    ]
                },
                {
                    "name": "Сенсори та датчики",
                    "description": "Аналогові та цифрові первинні перетворювачі фізичних величин",
                    "children": [
                        ("Датчики температури та вологості", "BME280, DHT22, DS18B20, SHT31, AHT10"),
                        ("Акселерометри, гіроскопи та IMU", "MPU6050, ADXL345, LSM6DS3, BNO055"),
                        ("Датчики відстані та наближення", "Ультразвукові HC-SR04, лазерні ToF VL53L0X"),
                        ("Датчики тиску та висоти", "BMP280, MS5611, DPS310"),
                        ("Датчики газу та якості повітря", "MQ серія, CCS811, SGP30"),
                        ("Оптичні сенсори та струм", "Датчики освітленості BH1750, датчики струму ACS712, INA219"),
                    ]
                },
                {
                    "name": "Драйвери та силова комутація",
                    "description": "Керування навантаженням, двигунами, реле та силовими ключами",
                    "children": [
                        ("Драйвери крокових двигунів", "A4988, DRV8825, TMC2208, TMC2209"),
                        ("H-мостові драйвери двигунів", "L298N, L293D, TB6612FNG, BTS7960"),
                        ("Модулі реле та твердотільні ключі", "Оптоізольовані реле 5V/12V, SSR модулі"),
                        ("Драйвери польових транзисторів (MOSFET)", "TC4420, IR2104, IR2110"),
                    ]
                },
                {
                    "name": "Джерела живлення та перетворювачі",
                    "description": "Стабілізація, перетворення напруги та керування живленням",
                    "children": [
                        ("Лінійні регулятори LDO", "AMS1117 3.3V/5V, LM7805, LM317, LP2985"),
                        ("Понижувальні DC-DC (Step-Down)", "LM2596, MP1584, MP2307, Mini360"),
                        ("Підвищувальні DC-DC (Step-Up)", "MT3608, XL6009, SX1308"),
                        ("Контролери заряду Li-Ion / BMS", "TP4056 з захистом, BMS 2S/3S/4S"),
                    ]
                },
                {
                    "name": "Інтерфейсні мікросхеми та зв'язок",
                    "description": "Перетворювачі шин даних, трансивери та бездротові модулі",
                    "children": [
                        ("Перетворювачі USB-UART / COM", "CH340G, CP2102, FT232RL, PL2303"),
                        ("Трансивери RS-485 / RS-232", "MAX485, SP3485, MAX232, SP3232"),
                        ("Контролери та трансивери CAN-шини", "MCP2515, MCP2551, TJA1050"),
                        ("Бездротові радіомодулі (RF / LoRa)", "NRF24L01+, LoRa SX1278, CC1101"),
                        ("Bluetooth / BLE модулі", "HC-05, HC-06, JDY-31, AT-09"),
                    ]
                },
                {
                    "name": "Логічні мікросхеми",
                    "description": "Стандартна цифрова логіка 74HC/CD4000",
                    "children": [
                        ("Зсувні регістри", "74HC595 (SIPO), 74HC165 (PISO)"),
                        ("Мультиплексори / демультиплексори", "74HC4051 (8-ch), 74HC4067 (16-ch)"),
                        ("Буфери та логічні інвертори", "74HC245, 74HC14 (тригер Шмітта), 74HC00"),
                    ]
                },
                {
                    "name": "Дисплеї та засоби індикації",
                    "description": "Екрани, матриці та світлодіодні індикатори",
                    "children": [
                        ("OLED дисплеї I2C / SPI", "0.96\" SSD1306, 1.3\" SH1106"),
                        ("РК дисплеї символьні", "LCD 1602, LCD 2004 з I2C рюкзаком"),
                        ("Світлодіодні матриці та сегментні індикатори", "MAX7219 8x8 матриці, TM1637 4-digit"),
                        ("Кольорові TFT дисплеї", "ST7735 1.8\", ILI9341 2.4\" SPI"),
                    ]
                },
                {
                    "name": "Пасивні компоненти",
                    "description": "Резистори, конденсатори, індуктивності та кварцові резонатори",
                    "children": [
                        ("Резистори та потенціометри", "Вивідні 0.25W, SMD 0805/0603, підстроєчні 3296W"),
                        ("Конденсатори керамічні та електролітичні", "Кераміка 0.1uF, електроліти 100uF/470uF"),
                        ("Кварцові резонатори", "16MHz, 8MHz, часовий кварц 32.768kHz"),
                    ]
                },
                {
                    "name": "Комутація та роз'єми",
                    "description": "Монтажні роз'єми, клемники, перемикачі",
                    "children": [
                        ("Кнопки та перемикачі", "Тактові кнопки 6x6, тумблери, dip-перемикачі"),
                        ("Штирьові роз'єми (Headers)", "Прямі та кутові рейки 2.54mm (PLS, PBS)"),
                        ("Клемники гвинтові та живлення", "Гвинтові клемники 5.08mm, гнізда 5.5x2.1mm"),
                    ]
                },
            ]

            created_cats = 0
            for item in cat_structure:
                parent, _ = Categories.objects.get_or_create(
                    name=item["name"],
                    defaults={"description": item["description"], "parent": None}
                )
                created_cats += 1

                for child_name, child_desc in item.get("children", []):
                    Categories.objects.get_or_create(
                        name=child_name,
                        defaults={"description": child_desc, "parent": parent}
                    )
                    created_cats += 1

            self.stdout.write(self.style.SUCCESS(f"Заповнено {created_cats} категорій."))

            # =========================================================================
            # 2. СКЛАДСЬКІ КОМІРКИ (Storage Locations)
            # =========================================================================
            locations_data = [
                # Органайзер A (Box A - Основні MCU та драйвери)
                *[("Органайзер A", "Полиця 1", f"A{i:02d}") for i in range(1, 13)],
                # Органайзер B (Box B - Сенсори та зв'язок)
                *[("Органайзер B", "Полиця 1", f"B{i:02d}") for i in range(1, 13)],
                # Органайзер SMD (Касетниця для SMD компонентів)
                *[("Касетниця SMD", "Секція 1", f"SMD-{i:02d}") for i in range(1, 17)],
                # Полиця основна (Великі модулі та плати)
                *[("Стелаж С1", "Полиця 2", f"C1-{i:02d}") for i in range(1, 7)],
            ]

            created_locs = 0
            for box, shelf, cell in locations_data:
                _, created = StorageLocations.objects.get_or_create(
                    box_number=box,
                    shelf=shelf,
                    cell_code=cell
                )
                if created:
                    created_locs += 1

            self.stdout.write(self.style.SUCCESS(f"Створено {created_locs} складських комірок зберігання."))

            # =========================================================================
            # 3. ПОСТАЧАЛЬНИКИ (Suppliers)
            # =========================================================================
            suppliers_data = [
                {
                    "name": "ТОВ «Космодром»",
                    "url": "https://kosmodrom.ua",
                    "contact_notes": "м. Харків / м. Київ. Основний каталог радіодеталей, пасивних компонентів та МК в Україні."
                },
                {
                    "name": "RC-Go Electronics",
                    "url": "https://rc-go.com.ua",
                    "contact_notes": "м. Київ. Модулі Arduino, ESP32, сенсори, робототехніка та датчики."
                },
                {
                    "name": "Biukop Electronics",
                    "url": "https://biukop.com.ua",
                    "contact_notes": "Компоненти, роз'єми, паяльне обладнання, кабелі."
                },
                {
                    "name": "LCSC Electronics",
                    "url": "https://lcsc.com",
                    "contact_notes": "Офіційний дистриб'ютор SMD комплектуючих, оригінальних MCU, швидка поставка фабричних партій."
                },
                {
                    "name": "Mouser Electronics",
                    "url": "https://mouser.com",
                    "contact_notes": "Глобальний авторизований дистриб'ютор напівпровідників та промислових мікросхем."
                },
            ]

            created_sups = 0
            for sup in suppliers_data:
                _, created = Suppliers.objects.get_or_create(
                    name=sup["name"],
                    defaults={"url": sup["url"], "contact_notes": sup["contact_notes"]}
                )
                if created:
                    created_sups += 1

            self.stdout.write(self.style.SUCCESS(f"Додано {created_sups} постачальників."))

        self.stdout.write(self.style.SUCCESS("Усі базові довідники успішно заповнено!"))
