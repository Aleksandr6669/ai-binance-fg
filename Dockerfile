FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Hugging Face Spaces ожидает, что приложение будет работать на порту 7860
EXPOSE 7860

# Запуск сервера
CMD ["python", "mcp_server.py"]
