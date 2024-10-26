# установка базового образа (host OS)
FROM python:3.11.4

ENV WORKDIR=/usr/src/app

# Не позволяет Python записывать файлы pyc на диск (эквивалентно опции python -B)
# Запрещает Python буферизовать stdout и stderr (эквивалентно опции python -u)
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# установка рабочей директории в контейнере
WORKDIR $WORKDIR

# копирование файла зависимостей в рабочую директорию
COPY ./ ./backend
COPY requirements.txt .

# установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082", "--log-level", "debug", "--loop", "uvloop", "--http", "httptools", "--workers", "2"]
