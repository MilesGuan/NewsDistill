FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends cron && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# 写入 crontab：8:00–22:00 每 2 小时执行一次 (08:00, 10:00, ..., 22:00)
RUN printf '0 8-22/2 * * * cd /app && /usr/local/bin/python -m core.daily_task >> /proc/1/fd/1 2>> /proc/1/fd/2\n' > /etc/cron.d/news_cron && \
    chmod 0644 /etc/cron.d/news_cron && \
    crontab /etc/cron.d/news_cron

# 容器启动时先立即执行一次，然后前台运行 cron
CMD ["sh", "-c", "cd /app && /usr/local/bin/python -m core.daily_task ; exec cron -f"]

# 容器启动时先立即执行一次 news_task（直接输出到 stdout/stderr），然后前台运行 cron
CMD ["sh", "-c", "cd /app && /usr/local/bin/python -m core.daily_task ; exec cron -f"]

