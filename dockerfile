# Используем официальный образ Python 3.10
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем все остальные файлы проекта
COPY . .

# Ожидаем, что credentials.json и .env будут скопированы вместе с проектом
# (или монтироваться как volume в продакшене)

# Указываем команду запуска
CMD ["python", "bot/__main__.py"]