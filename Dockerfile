FROM python:3.8-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN python3 -m pip install -r requirements.txt --upgrade pip setuptools

COPY . .

CMD ["python", "main.py"]
