FROM python:3.11-slim

# نصب بسته‌های سیستم مورد نیاز
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements.txt requirements.txt

# نصب dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# ایجاد دایرکتوری برای آپلودها
RUN mkdir -p static/uploads

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
