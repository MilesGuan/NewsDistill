# NewsDistill Docker 部署说明

本项目通过定时抓取新闻、调用大模型进行聚合，并把结果发送到飞书/邮件等渠道。本文档说明如何使用 Docker 部署，并在每天早上 8 点到 11 点之间，每隔 1.5 小时自动执行一次 `news_task`。

## 1. 前置条件

- 已安装 Docker（建议 20.10+）
- 可以访问外网以安装 Python 依赖和调用大模型 / 飞书等外部服务

## 2. 环境变量配置

项目使用 `envUtils.py` 通过 `.env` 读取各种密钥/配置，例如：

- 飞书 Webhook / App Id / App Secret
- 邮箱账号、密码和 SMTP 配置
- 大模型相关的 API Key（如 Google、DeepSeek、OpenAI 等）

在项目根目录创建 `.env` 文件，示例：

```bash
FEISHU_WEBHOOK_URL=...
EMAIL_USER=...
EMAIL_PASS=...
GOOGLE_API_KEY=...
DEEPSEEK_API_KEY=...
OPENAI_API_KEY=...
```

具体变量名请参考 `envUtils.py` 及各 notifier / model_provider 模块中的使用。

## 3. 使用 Docker Compose 部署（本地构建镜像）

推荐直接使用 `docker compose`，一条命令完成构建+启动。

在项目根目录执行：

```bash
docker compose up -d --build
```

这一步会：

- 使用当前目录下的 `Dockerfile` 构建镜像 `newsdistill:latest`
- 按 `docker-compose.yml` 启动 `newsdistill` 服务
- 自动挂载 `.env` 和 `output` 目录

之后如果你修改了代码，只需要在项目根目录再次执行同一条命令即可滚动更新：

```bash
docker compose up -d --build
```

## 4. 手动构建 Docker 镜像（可选）

在项目根目录（包含 `Dockerfile` 的目录）执行：

```bash
docker build -t newsdistill:latest .
```

这一步会：

- 安装 Python 3.11 运行环境
- 安装 `requirements.txt` 中列出的依赖
- 拷贝项目代码到镜像中
- 安装 `cron` 并写入定时任务

## 5. 定时任务说明（8:00–11:00 每 1.5 小时）

镜像内已经配置好 `cron`，crontab 内容位于 `/etc/cron.d/news_cron`（8:00–11:00 每 1.5 小时执行一次）：

```cron
0 8,11 * * * cd /app && /usr/local/bin/python -m core.daily_task >> /var/log/cron.log 2>&1
30 9 * * * cd /app && /usr/local/bin/python -m core.daily_task >> /var/log/cron.log 2>&1
```

这组规则的含义是：

- 每天从 **08:00 到 11:00（含）**，约每 1.5 小时执行一次（08:00, 09:30, 11:00）
- 在 `/app` 目录下运行 `python -m core.daily_task`
  - 实际会执行 `core/daily_task.py` 中的 `news_task()`（默认只处理增量）
- 输出日志追加到 `/var/log/cron.log`

容器的启动命令会：

- 启动 `cron`
- `tail -F /var/log/cron.log` 持续输出日志到容器标准输出，方便用 `docker logs` 查看

## 6. 手动触发一次任务

如果想临时在容器内手动执行一次 `news_task`，可以：

```bash
docker exec -it newsdistill /bin/sh -c "cd /app && python -m core.daily_task"
```

如果希望处理「全量」而不是增量，可以修改 `core/daily_task.py` 中 `news_task` 的默认参数，或在需要时改成在模块里增加一个入口函数专门处理全量。

## 7. 查看日志

查看容器运行日志（包括启动时那次执行 + 定时任务的输出）：

```bash
docker compose logs -f
```

（也可以在 Docker Desktop 的 **Logs** 标签页实时看到 `print` 输出。）

