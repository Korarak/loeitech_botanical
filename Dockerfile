FROM python:3.10-slim

WORKDIR /app

RUN apt update && apt install -y git

RUN git clone https://github.com/Korarak/loeitech_botanical.git /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "app.py"]
