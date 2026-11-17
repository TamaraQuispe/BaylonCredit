FROM python:3.12.14-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY codigo-base /app
COPY revision /revision
COPY tools/reproduce.py /tools/reproduce.py
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1
WORKDIR /results
ENTRYPOINT ["python", "/tools/reproduce.py"]
