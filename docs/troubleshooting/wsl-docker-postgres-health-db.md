# WSL2 Docker Desktop Postgres `/health/db` 503 排障

这份文档记录一次本地开发排障经验，适用于下面这种现象：

```text
INFO:     127.0.0.1:60956 - "GET /health/db HTTP/1.1" 503 Service Unavailable
```

在 MeterDesk 中，`/health/db` 返回 503 表示 FastAPI 已经启动，但后端没有完成 Postgres 健康检查。常见根因不是前端页面，而是 Postgres 不可用，或 WSL2 里的后端进程无法访问 Docker Desktop 发布出来的 Postgres 端口。

## 快速定位

先确认 Postgres 容器内部是否正常：

```bash
docker compose exec -T postgres psql -U meterdesk -d meterdesk -c 'SELECT 1;'
```

如果返回 `1`，说明容器、数据库名、用户名和密码都没有问题。

再确认 WSL2 里的普通进程能否访问 Docker 发布到宿主侧的端口：

```bash
PGPASSWORD=meterdesk psql -h 127.0.0.1 -p 5432 -U meterdesk -d meterdesk -c 'SELECT 1;'
```

如果这里返回 `Connection refused`，但容器内部的 `SELECT 1` 成功，说明失败点在 Docker Desktop 和 WSL2 的端口发布边界。FastAPI 会从 `.env` 读取 `DATABASE_URL`，所以 `postgresql+psycopg://meterdesk:meterdesk@localhost:5432/meterdesk` 也会以同样方式失败。

如果没有 `psql`，也可以只测试 TCP 连通性：

```bash
python3 -c "import socket; s=socket.create_connection(('127.0.0.1',5432),timeout=2); s.close(); print('ok')"
```

## 检查 Docker 端口发布

检查 Compose 服务和端口映射：

```bash
docker compose ps postgres
docker compose port postgres 5432
docker inspect -f '{{json .NetworkSettings.Ports}}' meterdesk-postgres
```

如果 Docker 显示 `0.0.0.0:5432->5432/tcp`，但 WSL2 仍然无法连接 `127.0.0.1:5432`，通常说明容器本身没问题，而是当前 WSL2 网络环境无法访问这个 host 端口。

也可以检查 Docker context 和 daemon 信息：

```bash
docker context show
docker context ls
docker info --format '{{.OperatingSystem}} / {{.Name}}'
```

在 WSL2 中使用 Docker Desktop 时，即使当前 context 是 `default`，endpoint 是 `/var/run/docker.sock`，`docker info` 仍可能显示 daemon 是 Docker Desktop。这本身不一定是问题。

## 快速本地修复

将 host 端口换成其他值，例如 `55432`，同时保持容器内端口仍为 `5432`：

```bash
POSTGRES_PORT=55432 docker compose up -d --force-recreate postgres
```

同步更新本地 `.env`：

```env
POSTGRES_PORT=55432
DATABASE_URL=postgresql+psycopg://meterdesk:meterdesk@localhost:55432/meterdesk
```

从 WSL2 验证新端口：

```bash
PGPASSWORD=meterdesk psql -h 127.0.0.1 -p 55432 -U meterdesk -d meterdesk -c 'SELECT 1;'
```

再运行项目自带的 smoke check：

```bash
make seed
make health
```

预期数据库健康检查响应：

```json
{"service":"meterdesk-api","status":"ok","database":"reachable"}
```

## WSL2 和 Docker Desktop 检查项

如果换 host 端口后仍然失败，继续检查 Windows/WSL2 网络配置。

mirrored networking 场景下，`.wslconfig` 可能包含：

```ini
[experimental]
networkingMode=mirrored
dnsTunneling=true
firewall=true
autoProxy=false
```

当 `firewall=true` 时，Windows Firewall 和 Hyper-V 网络规则可能过滤 WSL2 流量。可以检查 Docker Desktop：

- `Settings -> Resources -> WSL Integration`
- 确认当前 WSL distribution 已启用。
- 重启 Docker Desktop。
- 在 Windows PowerShell 中执行：

```powershell
wsl --shutdown
```

然后重新打开 WSL2，再执行：

```bash
docker compose up -d postgres
make health
```

## 判断规则

按下面的边界判断：

- 容器内部 `SELECT 1` 失败：排查 Postgres 容器、账号密码或数据库初始化。
- 容器内部 `SELECT 1` 成功，但 WSL2 访问 `127.0.0.1:5432` 失败：排查 Docker Desktop/WSL2 端口发布。
- 如果只是 `5432` 失败，优先将 host 端口换成 `55432`，并同步更新本地 `.env`。
