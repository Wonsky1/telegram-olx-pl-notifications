FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run database migrations and start the application
CMD ["sh", "-c", "python migrate.py upgrade && python main.py"]
