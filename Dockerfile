FROM python:3.10-slim

WORKDIR /app

# ติดตั้ง git และ build dependencies ที่จำเป็นสำหรับ pandas/openpyxl
RUN apt update && apt install -y git gcc g++ libffi-dev libpq-dev build-essential

# clone โค้ดจาก GitHub (Portainer จะ clone ให้ถ้าใช้ Git deployment)
# ถ้าใช้ Portainer Git Stack ไม่ต้อง RUN git clone ก็ได้

COPY . .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "app.py"]
