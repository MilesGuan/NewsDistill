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

# 修改后的 Cron 逻辑
# 第一条：偶数小时的整点 (8, 11, 14, 17, 20, 23)
# 第二条：奇数小时的半点 (9:30, 12:30, 15:30, 18:30, 21:30)
RUN printf '0 8,11,14,17,20,23 * * * cd /app && /usr/local/bin/python -m core.daily_task >> /proc/1/fd/1 2>> /proc/1/fd/2\n30 9,12,15,18,21 * * * cd /app && /usr/local/bin/python -m core.daily_task >> /proc/1/fd/1 2>> /proc/1/fd/2\n' > /etc/cron.d/news_cron && \
    chmod 0644 /etc/cron.d/news_cron && \
    crontab /etc/cron.d/news_cron

# 容器启动时先立即执行一次 news_task（直接输出到 stdout/stderr），然后前台运行 cron
CMD ["sh", "-c", "cd /app && /usr/local/bin/python -m core.daily_task ; exec cron -f"]

