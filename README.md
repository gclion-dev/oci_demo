# OCI Manager

基于 FastAPI + Vue 3 + PostgreSQL 的 Oracle Cloud 多租户管理平台，覆盖实例管理、抢机、网络配置、账单监控、IP 数据、Cloudflare DNS 等核心场景。

## 功能概览

### 云账户管理
- 多租户配置（User OCID / Fingerprint / Tenancy OCID / 私钥 / 多 Region）
- 启用/禁用开关，禁用后自动从抢机、账单等模块中排除
- 连接测试（遍历所有区域）
- 加密导出/导入备份（AES-256-GCM）
- OCI Config 粘贴/文件导入快速填表

### 实例管理
- 按区域分组展示所有实例
- 开机 / 关机 / 强制关机 / 重启
- 更改实例配置（Shape、OCPU、内存、实例名称）
- VNC 控制台连接
- 附加 IPv6
- AMD 实例开启/关闭 500Mbps 下行
- 删除实例（二次确认）
- Web SSH 终端（密码/私钥认证，凭据持久化）

### 抢机任务
- ARM / AMD 实例规格可视化配置
- 自定义抢机频率（秒级）
- 实时日志查看
- 断点续抢（服务重启自动恢复）
- 抢机成功自动通知

### 网络与安全
- 安全列表管理（入站/出站规则增删）
- VCN 管理（查看/删除）
- 流量统计
- 引导卷管理
- 配额查询

### IP 数据
- 全球服务器地图（Leaflet）
- 从 OCI 自动加载实例公网 IP
- IP 归属地查询（ip-api.com）
- 地图标记点击测 Ping（itdog.cn）
- 批量管理（添加/刷新/删除）

### Cloudflare DNS
- 多 Cloudflare 账户管理
- DNS 记录增删改查
- 代理状态切换

### 账单监控
- 实时拉取当月账单（OCI Usage API）
- 按日消费趋势图表
- 自动换算 CNY
- 历史账单记录

### 通知配置
- 邮件通知（SMTP）
- 企业微信 Webhook
- 按用户独立配置

### 用户与权限
- 管理员 / 普通用户角色
- JWT 认证
- 各用户独立管理自己的云账户和任务
- 默认 OCI 私钥 / SSH 公钥设置
- SSH 凭据管理（个人设置中可查看/编辑/删除）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11 · FastAPI · SQLAlchemy (async) · OCI SDK · Paramiko |
| 前端 | Vue 3 · TypeScript · Tailwind CSS · Leaflet · Chart.js · xterm.js · Pinia · Vite |
| 数据库 | PostgreSQL 16 (asyncpg) |
| 部署 | Docker Compose · Nginx |

## 目录结构

```
├── backend/
│   ├── app/
│   │   ├── main.py              # 入口（自动建库/建表/初始化）
│   │   ├── config.py            # 环境变量配置
│   │   ├── database.py          # 异步数据库引擎
│   │   ├── models.py            # SQLAlchemy 模型
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── auth.py              # JWT 认证
│   │   ├── notify.py            # 通知模块
│   │   ├── oci_client.py        # OCI SDK 封装
│   │   ├── snipe_worker.py      # 抢机后台线程
│   │   └── routers/
│   │       ├── tenants.py       # 云账户 CRUD / 导入导出
│   │       ├── instances.py     # 实例管理 / 配置变更
│   │       ├── snipe.py         # 抢机任务
│   │       ├── bills.py         # 账单查询
│   │       ├── ip_data.py       # IP 数据 / 地图
│   │       ├── cloudflare.py    # Cloudflare DNS
│   │       ├── security_rules.py # 安全列表
│   │       ├── traffic.py       # 流量统计
│   │       ├── boot_volumes.py  # 引导卷
│   │       ├── vcn.py           # VCN 管理
│   │       ├── limits.py        # 配额查询
│   │       ├── network_features.py # IPv6 / 500M
│   │       ├── console_connection.py # VNC 控制台
│   │       ├── notify.py        # 通知配置
│   │       ├── terminal.py      # WebSocket SSH
│   │       ├── ssh_credentials.py # SSH 凭据
│   │       ├── oci_users.py     # OCI IAM 用户
│   │       ├── regions.py       # 区域字典
│   │       ├── users.py         # 用户管理
│   │       └── auth.py          # 登录 / Token
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/               # 页面组件
│   │   ├── components/          # 通用组件
│   │   ├── layouts/             # 布局
│   │   ├── api/                 # Axios 封装
│   │   ├── router/              # 路由
│   │   ├── stores/              # Pinia 状态
│   │   ├── composables/         # 组合式函数
│   │   └── types/               # TypeScript 类型
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 快速部署

### Docker Compose

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 SECRET_KEY、ADMIN_PASSWORD、DB_PASSWORD 等

# 2. 启动
docker-compose up -d --build
```

启动后的服务：

| 容器 | 说明 | 端口 |
|------|------|------|
| oci-manager-db | PostgreSQL | 5432 |
| oci-manager-backend | FastAPI | 8000 |
| oci-manager-frontend | Nginx 静态前端 | 80 |

默认管理员账号：`admin` / `admin123`（请立即修改密码）

### 本地开发

**后端：**

```bash
cd backend
cp ../.env.example .env  # 编辑数据库连接等配置
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> 后端启动时自动检查并创建数据库和表。

**前端：**

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

> Vite 开发服务器将 `/api` 代理到 `http://localhost:8000`。

## API 模块

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 认证 | `/api/auth` | 登录、修改密码 |
| 用户 | `/api/users` | 用户 CRUD、默认密钥 |
| 云账户 | `/api/tenants` | 租户 CRUD、测试、导入导出 |
| 实例 | `/api/instances` | 列表、操作、配置变更 |
| 抢机 | `/api/snipe` | 任务 CRUD、启动/停止 |
| 账单 | `/api/bills` | 当月账单、历史记录 |
| IP 数据 | `/api/ip-data` | IP 查询、地图、OCI 加载 |
| Cloudflare | `/api/cloudflare` | DNS 记录管理 |
| 安全列表 | `/api/security-rules` | 入站/出站规则 |
| 流量 | `/api/traffic` | 流量统计 |
| 引导卷 | `/api/boot-volumes` | 引导卷管理 |
| VCN | `/api/vcn` | VCN 管理 |
| 配额 | `/api/limits` | 配额查询 |
| 网络 | `/api/network` | IPv6 / 500M |
| VNC | `/api/console` | 控制台连接 |
| 通知 | `/api/notify` | 通知配置、测试 |
| SSH 终端 | `/api/terminal` | WebSocket SSH |
| SSH 凭据 | `/api/ssh-credentials` | 凭据 CRUD |
| OCI 用户 | `/api/oci-users` | IAM 用户列表 |
| 区域 | `/api/regions` | 区域字典 |

## License

MIT
