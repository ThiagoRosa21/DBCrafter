
FROM python:3.10


WORKDIR /app


COPY . .

RUN pip install flask pandas


WORKDIR /app/src


EXPOSE 5000


CMD ["python", "main.py"]
