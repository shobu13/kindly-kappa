FROM python:3.10

# Edit with mysql-client, postgresql-client, sqlite3, etc. for your needs.
# Or delete entirely if not needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/server/
RUN pip install --no-cache-dir -r server/requirements.txt

COPY . /usr/src/app/server

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0"]
