FROM python:3.12-slim

WORKDIR /service

COPY requirements.txt /service/requirements.txt
RUN pip install --no-cache-dir -r /service/requirements.txt

COPY app /service/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
