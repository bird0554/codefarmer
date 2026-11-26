FROM docker.m.daocloud.io/library/python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser
COPY main.py entrypoint.sh ./
RUN chmod 0755 /app/entrypoint.sh && mkdir -p /data && chown appuser:appuser /data
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "main.py"]
