# Telegram Sales Tracker Bot - Setup Guide

## Описание
Telegram-бот для трекинга продаж с интеграцией с Google Sheets. Позволяет работникам добавлять клиентов, отслеживать продажи и запрашивать выплаты.

## Требования
- Python 3.10+
- Google Sheets API доступ
- Telegram Bot Token

## Установка

### 1. Клонирование и подготовка окружения
```bash
git clone <repository-url>
cd sales-tracker-bot
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Настройка Google Sheets API
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API и Google Drive API
4. Создайте Service Account и скачайте credentials.json
5. Поместите credentials.json в корень проекта

### 3. Создание Google Sheets таблицы
Создайте Google Sheets таблицу с тремя листами:

#### Лист "Workers"
Столбцы: `tg_id | username | role | clients_count | balance`

#### Лист "Clients" 
Столбцы: `worker_tg_id | worker_username | phone | name | messenger | order_link | amount | status | receipt_url | timestamp`

#### Лист "Withdrawals"
Столбцы: `id | tg_id | amount | status | created_at`

### 4. Настройка Telegram Bot
1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите Bot Token
3. Добавьте бота в свою таблицу Google Sheets (права редактора)

### 5. Конфигурация
1. Скопируйте `env.example` в `.env`
2. Заполните переменные:
```bash
cp env.example .env
```

Отредактируйте `.env`:
```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
SPREADSHEET_ID=your_google_spreadsheet_id_here
GSPREAD_CREDENTIALS=credentials.json
REPLY_TIMEOUT=10
```

### 6. Запуск
```bash
python bot/__main__.py
```

## Использование

### Для работников:
1. `/start` - регистрация и вход в личный кабинет
2. Добавление клиентов через кнопку "➕ Добавить клиента"
3. Запрос выплат через кнопку "💸 Запросить выплату"

### Для администраторов:
1. `/admin` - панель администратора
2. Просмотр топа работников
3. Управление заявками на выплаты
4. Экспорт данных в CSV

## Структура проекта
```
bot/
├── __main__.py          # Точка входа
├── config.py            # Конфигурация
├── sheets.py            # Работа с Google Sheets
├── handlers/            # Обработчики команд
│   ├── start.py         # Команда /start
│   ├── worker.py        # Функционал работников
│   └── admin.py         # Админ-панель
├── services/            # Бизнес-логика
│   ├── commission.py    # Расчет комиссий
│   └── receipts.py      # Загрузка чеков
└── utils/               # Утилиты
    └── validators.py    # Валидация данных
```

## Система комиссий
- До 10 клиентов: 5% комиссия
- Свыше 10 клиентов: 10% комиссия

## Логи и отладка
Логи выводятся в консоль. Для продакшена рекомендуется настроить файловое логирование.

## Безопасность
- Храните `credentials.json` и `.env` в безопасности
- Не коммитьте секретные данные в репозиторий
- Используйте права доступа Google Sheets для ограничения доступа

## Troubleshooting

### Ошибки Google API
- Проверьте, что включены Google Sheets API и Drive API
- Убедитесь, что Service Account имеет доступ к таблице
- Проверьте путь к credentials.json

### Ошибки Telegram Bot
- Проверьте корректность Bot Token
- Убедитесь, что бот запущен и отвечает
- Проверьте ID администраторов в ADMIN_IDS 