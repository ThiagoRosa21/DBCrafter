FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=5000
WORKDIR /app
COPY requirements.txt .
RUN pip install --require-hashes -r requirements.txt \
    && groupadd --system app \
    && useradd --system --gid app --home /app app
COPY src ./src
COPY gunicorn.conf.py .
USER app
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','5000')+'/healthz', timeout=3)"
CMD ["gunicorn", "--config", "gunicorn.conf.py", "src.wsgi:app"]
