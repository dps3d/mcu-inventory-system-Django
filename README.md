# MCU Inventory System 🔌📦

**MCU Inventory System** — веб-застосунок на базі **Django 6.1.2** та **MariaDB 13.0.2 (InnoDB)**, розроблений для автоматизації обліку мікроконтролерів, електронних компонентів, плат розробки, складських комірок та специфікацій інженерних проєктів (BOM).

---

## 🛠️ Технологічний стек

- **Мова програмування:** Python 3.14 / 3.12+
- **Веб-фреймворк:** Django 6.1.2
- **СУБД:** **MariaDB Server версії 13.0.2** (драйвер `mysqlclient==2.3.0`, рушій таблиць **InnoDB**, кодування `utf8mb4_unicode_ci`)
- **Бібліотеки обробки даних:** Pillow 12.3.0, python-dotenv 1.2.4, sqlparse 0.6.0, asgiref 3.12.1
- **Фронтенд:** Django Template Language (DTL), адаптивний CSS з палітрою Refined Palette Theme, Vanilla JavaScript

---

## 📋 Вимоги до оточення

1. Встановлений інтерпретатор **Python 3.12+**
2. Встановлений та запущений сервер **MariaDB 13.0.2** (або MySQL 8.0+)
3. Системні бібліотеки компіляції клієнта MySQL (`libmysqlclient-dev` / `default-libmysqlclient-dev` або `mariadb-client` для Linux)

---

## 🚀 Інструкція зі швидкого запуску

### 1. Клонування репозиторію та перехід у директорію

```bash
git clone <URL_РЕПОЗИТОРІЮ>
cd mcu-inventory-system
```

### 2. Створення та активація віртуального середовища

```bash
python -m venv .venv
source .venv/bin/activate  # Для Linux/macOS
# або: .venv\Scripts\activate  # Для Windows
```

### 3. Встановлення залежностей

Усі версії пакетів зафіксовані у файлі `requirements.txt`:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Налаштування бази даних MariaDB

Увійдіть у консоль СУБД MariaDB та створіть базу даних з підтримкою UTF-8:

```sql
CREATE DATABASE mcu_inventory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'mcu_user'@'localhost' IDENTIFIED BY 'mcu_password';
GRANT ALL PRIVILEGES ON mcu_inventory.* TO 'mcu_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Конфігурація змінних оточення (.env)

Створіть власний файл `.env` на основі наданого шаблону `.env.example`:

```bash
cp .env.example .env
```

Відредагуйте параметри підключення у файлі `.env`:

```env
SECRET_KEY=django-insecure-mcu-super-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=django.db.backends.mysql
DB_NAME=mcu_inventory
DB_USER=mcu_user
DB_PASSWORD=mcu_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 6. Застосування міграцій

Виконайте міграції для створення реляційних таблиць та запуску data-міграції початкових категорій:

```bash
python manage.py migrate
```

### 7. Завантаження демонстраційних тестових даних

Для демонстрації повного функціоналу в репозиторії присутні готові фікстури:

```bash
# Завантаження комплексної фікстури (компоненти, комірки, залишки, постачальники, проєкти):
python manage.py loaddata fixtures/seed_data.json
```

### 8. Створення адміністратора системи

```bash
python manage.py createsuperuser
```

### 9. Запуск локального веб-сервера розробки

```bash
python manage.py runserver
```

Після запуску застосунок доступний за адресою:
👉 **http://127.0.0.1:8000/**

Панель адміністрування Django:
👉 **http://127.0.0.1:8000/admin/**

---

## 🏛️ Структура застосунків проєкту

- `catalog/` — каталог мікроконтролерів і компонентів, візуалізатор розпіновок (Pinout Viewer & Builder), Generic CBV CRUD;
- `inventory/` — просторовий облік (органайзери, ряди, комірки), складські залишки, журнал транзакцій та списання;
- `projects/` — інженерні проєкти, специфікації BOM (Bill of Materials), резервування та калькулятор збірки;
- `suppliers/` — каталог постачальників, облік замовлень компонентів та історія цін;
- `accounts/` — система реєстрації з пре-модерацією адміністратором, авторизація та розмежування прав доступу.

---

## 🔒 Безпека та права доступу

1. **Гостьовий режим (Anonymous):** доступний перегляд публічного каталогу компонентів, розпіновок та публічних проєктів.
2. **Лаборант / Авторизований користувач (Authenticated):** створення та керування власними інженерними проєктами, резервування складських залишків.
3. **Викладач / Адміністратор (Staff / Superuser):** повний CRUD компонентів, редагування складських комірок, ручні складські транзакції, схвалення заявок реєстрації користувачів.
