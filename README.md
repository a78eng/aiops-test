# 轻量 AIOps 智能运维平台 · 架构说明

> 一句话介绍：一套 **「监控 + 日志 + AI 故障诊断 + 知识库问答 + 脚本自动化」** 的智能运维平台，
> 用 **大模型（LLM）+ 向量检索（RAG）** 把团队的 SOP 文档、历史故障案例沉淀成**可检索、可问答、可复用**的运维知识资产。

---

## 一、解决了什么痛点

| 痛点 | 本平台的解决方案 |
|------|------------------|
| 运维经验散落在人脑、Word、聊天记录里，**新人上手难、老故障反复踩坑** | 把 SOP 文档 + 历史故障**向量化入库**，语义检索秒级找到相似案例 |
| 传统监控只有冷冰冰的图表，**数据要靠人自己分析** | 大模型自动把指标/日志**变成结论**：分钟简报、AI 巡检报告、AI 日报 |
| **故障排查靠老师傅**，相似问题重复排查 | 语义检索历史故障 + 大模型辅助分析，给出根因与处置步骤 |
| **脚本反复手写**，重复劳动、易出错 | 脚本模板参数化渲染 + AI 按需求一键生成脚本 |
| 指标（Prometheus）和日志（Loki）**分散割裂**，没有统一视角 | 统一接入后端，喂给大模型做**跨数据源综合诊断** |
| 知识沉淀**没有闭环**，沉淀了也不会被用起来 | 「知识空白录用」：AI 答不上 → 用户录入 → 审批 → 自动入库，**越用越聪明** |

---

## 二、实现了什么效果

1. **监控可视化**：实时 CPU/内存/磁盘/GPU 指标 + 近 1 小时趋势图，超阈值自动变红告警。
2. **智能分析中心**：
   - 每 60 秒自动生成「实时简报」（指标 + 错误日志 → 大模型总结）
   - 系统全局巡检：Docker / K8s 容器与 Pod 概况 + 一键生成「AI 巡检报告」
   - 故障统计（总数/待处理/处理中/已关闭 + 高频故障 Top10）
   - 处置效率（平均处置时长统计）
3. **SOP 知识库**：上传 → 切片 → 向量化 → 审批 → 可检索，支持在线查看/编辑/下载。
4. **AI 知识问答（RAG）**：语义检索 SOP + 故障案例，**带来源**回答；未命中时可直接让大模型作答，并一键回录知识库。
5. **故障工单**：录入 → 语义检索相似案例 → 流转闭环（待处理→处理中→已关闭），高频故障识别。
6. **脚本自动化**：模板增删改查 + 参数渲染 + AI 生成脚本 + 一键复制。
7. **团队管理**：成员/角色/启停管理 + 每人贡献统计（SOP/故障/脚本数量）。

---

## 三、总体架构（文本图）

```
                        ┌──────────────────────────────────────┐
                        │            浏览器（用户）              │
                        │   仪表盘 · 智能分析 · 知识库 · AI问答   │
                        │   处理中心 · 脚本模板 · 团队管理         │
                        └───────────────────┬──────────────────┘
                                            │ HTTP
                                            ▼
                        ┌──────────────────────────────────────┐
                        │         Nginx（网关 / 静态托管）        │
                        │  /api/* → 后端                         │
                        │  /grafana /prometheus /loki → 监控组件  │
                        └───────┬──────────────────┬───────────┘
                     /api/*     │                  │ 监控子路径
                                ▼                  ▼
                     ┌──────────────────┐   ┌────────────────────────┐
                     │  FastAPI 后端     │   │  Grafana / Prometheus   │
                     │  （8000 端口）     │   │  / Loki（可观测性栈）     │
                     └──┬────┬────┬─────┘   └────────────────────────┘
                        │    │    │
           ┌────────────┘    │    └─────────────┐
           ▼                 ▼                  ▼
  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐
  │ PostgreSQL 16   │  │    Ollama    │  │  bge-m3 嵌入模型  │
  │ + pgvector      │  │ Qwen2.5-7B   │  │  （本地 CPU 加载） │
  │ 业务数据 + 向量  │  │ 大模型推理    │  │  文本 → 1024维向量 │
  └────────────────┘  └──────────────┘  └──────────────────┘
```

**监控数据来源**（独立于主流程，由后端定时拉取）：

```
  node-exporter ──采集主机指标──▶ Prometheus ──查询──▶ FastAPI 后端
  Promtail ──────采集系统/容器日志─▶ Loki ──────查询──▶ FastAPI 后端
```

---

## 四、技术栈总览

| 分层 | 技术 | 作用 |
|------|------|------|
| **前端** | Vue 3（组合式 API） | 页面框架 |
| | Vite 8 | 构建工具，打包成 `dist` 静态文件 |
| | Element Plus | UI 组件库（表格/表单/弹窗），中文语言包 |
| | ECharts 6 | 监控趋势图、指标可视化 |
| | Pinia + Vue Router | 状态管理 + 路由 |
| | Axios | HTTP 请求，统一携带 JWT |
| | marked | 把大模型返回的 Markdown 渲染成网页 |
| **后端** | Python FastAPI（异步） | Web 框架，RESTful API |
| | SQLAlchemy + asyncpg | 异步 ORM + PostgreSQL 驱动 |
| | pgvector | 向量存储与余弦相似度检索 |
| | python-jose + passlib(bcrypt) | JWT 鉴权 + 密码加密 |
| | sentence-transformers | 加载 bge-m3 做文本向量化 |
| | httpx | 调用 Ollama 大模型接口 |
| | 内置调度器（scheduler.py） | 定时任务（分钟简报、日报） |
| **AI** | Ollama | 本地大模型推理服务 |
| | Qwen2.5-7B-Instruct | 对话 / 分析 / 脚本生成 大模型 |
| | bge-m3 | 文本嵌入模型（中英双语，1024 维） |
| **数据库** | PostgreSQL 16 + pgvector | 业务数据 + 向量库（一体，不用外挂） |
| **监控栈** | Prometheus + node-exporter | 指标采集与存储 |
| | Loki + Promtail | 日志采集与存储 |
| | Grafana | 监控可视化 |
| **网关/部署** | Nginx | 静态托管 + 反向代理 |
| | Docker Compose | 编排监控栈、DB、Ollama 等 8 个容器 |
| | systemd | 管理 FastAPI 后端服务（自动拉起） |

---

## 五、核心组件详解

### 1. 前端（Vue 3 单页应用）

纯静态文件，Nginx 托管；通过 `/api` 前缀访问后端（开发走 Vite 代理、生产走 Nginx 转发，前端代码无需区分环境）。

| 页面（路由） | 功能 |
|---|---|
| `/dashboard` 监控仪表盘 | 实时指标 + 近 1 小时趋势图 |
| `/report` 智能分析中心 | 分钟简报、全局巡检、AI 巡检报告、故障统计、处置效率 |
| `/sop` SOP 知识库 | 上传/查看/编辑/删除/下载，审批后入库 |
| `/rag` AI 知识问答 | 语义检索 + 大模型回答，可回录知识库 |
| `/work` 处理中心 | 文档审批、知识空白录用、故障工单 |
| `/scripts` 脚本模板 | 增删改查、参数渲染、AI 生成、复制 |
| `/team` 团队管理 | 成员管理、角色权限、贡献统计 |

### 2. 后端（FastAPI 异步服务）

- systemd 服务 `aiops-backend` 管理，**8000 端口**，单 worker，崩溃自动重启。
- 启动时自动：建表（`CREATE EXTENSION vector` + 建表）→ 初始化默认管理员 `admin` → 启动定时调度器。

| 模块 | 作用 |
|---|---|
| `main.py` | 入口、路由注册、生命周期 |
| `config.py` | 读取 `.env` 配置（数据库地址、模型、密钥） |
| `database.py` | 异步数据库引擎 |
| `models.py` | 7 张表 ORM 定义 |
| `schemas.py` | 接口入参校验 |
| `security.py` | JWT、密码加密、管理员权限依赖 |
| `embedding.py` | bge-m3 懒加载 + 文本向量化 |
| `llm_client.py` | 调用 Ollama |
| `rag.py` | 切片、入库、语义检索、故障分析、统一问答 |
| `monitor.py` | 拉取 Prometheus 指标、Loki 日志 |
| `infra_inspect.py` | 采集 Docker / K8s 概况 |
| `scheduler.py` | 定时生成分钟简报、AI 日报 |
| `routers/` | 9 个路由模块 |

### 3. 数据库（PostgreSQL 16 + pgvector）

单库 `aiops` 同时承担**业务数据**和**向量数据**。

| 表 | 内容 | 向量字段 |
|---|---|---|
| `users` | 用户、角色、密码 | — |
| `sop_documents` | SOP 文档（按 `doc_key` 分组多切片） | ✅ 1024 维 |
| `qa_gaps` | 待录用的 AI 答案（知识空白） | — |
| `fault_records` | 故障工单 | ✅ 1024 维 |
| `script_templates` | 脚本模板 | — |
| `daily_reports` | 每日 AI 日报 | — |
| `minute_briefs` | 每分钟实时简报 | — |

> 向量检索用 pgvector 的 `embedding.cosine_distance()` 算余弦相似度，SQL 直接完成，无需外挂向量库。

### 4. AI 层（双模型）

| 模型 | 用途 | 部署 |
|---|---|---|
| Qwen2.5-7B-Instruct | 对话、故障分析、AI 日报、脚本生成 | Ollama 容器（11434） |
| bge-m3 | 文本嵌入（检索用），1024 维 | 本地文件，后端 CPU 加载 |

> 检索：提问 → bge-m3 向量化 → pgvector 余弦相似度召回 top3 → 命中片段拼进 Prompt → 大模型生成带来源回答。

### 5. 可观测性监控栈

| 组件 | 端口 | 作用 |
|---|---|---|
| node-exporter | 9100 | 采集主机 CPU/内存/磁盘/GPU 指标 |
| Prometheus | 9090 | 指标存储与查询 |
| Grafana | 3000 | 监控大盘可视化 |
| Promtail | — | 采集 `/var/log` 与 Docker 容器日志 |
| Loki | 3100 | 日志存储与查询 |

后端 `monitor.py` 定时查询 Prometheus / Loki，把原始数据喂给大模型生成「分钟简报」「AI 巡检报告」「AI 日报」。

### 6. 网关与部署

- **Nginx**：托管前端静态页；`/api/*` → 后端 8000；`/grafana/`、`/prometheus/`、`/loki/` → 对应监控组件。
- **Docker Compose**：一键编排 8 个容器（postgres / prometheus / grafana / loki / promtail / node-exporter / nginx / ollama）。
- **systemd**：管理 FastAPI 后端（`Restart=always` 自动拉起）。

---

## 六、核心业务链路

**1. 监控 → 告警可视化**

```
node-exporter → Prometheus → 后端 monitor.py → 前端仪表盘（超阈值变红）
                                       └──→ 大模型生成「分钟简报 / AI 日报」
```

**2. 日志分析**

```
Promtail 采集 /var/log + Docker 日志 → Loki → 后端查询 → 大模型提取错误摘要
```

**3. 知识库（SOP）入库与问答（核心 RAG 闭环）**

```
上传 .md/.txt → 切片 → bge-m3 向量化 → 存入 pgvector（待审批）
                                            ↓ 管理员审批通过
                                        可被语义检索
                                            ↓
  用户提问 → 向量检索命中 SOP + 故障案例 → 大模型回答（带来源）
                                            ↓ 未命中
                   大模型直接答 + 提示「录入知识库」→ 审批 → 自动入库（知识空白录用）
```

**4. 故障工单处理**

```
录入现象 → 向量化入库 → 相似故障语义检索 → 工单流转（待处理→处理中→已关闭）
                                      → 累计发生次数（高频故障 Top10）
```

**5. 脚本自动化**

```
模板库（增删改查）→ 填参数 → 渲染成可执行脚本 → 一键复制
                              └── 或：AI 按需求生成脚本 → 保存为模板
```

---

## 七、目录结构

```
/opt/aiops/
├── backend/                # FastAPI 后端
│   ├── main.py             # 入口
│   ├── config.py           # 配置
│   ├── models.py           # 数据表
│   ├── routers/            # 9 个路由
│   ├── rag.py              # RAG 核心
│   ├── scheduler.py        # 定时任务
│   ├── .env                # 环境变量（密钥/地址）
│   └── venv/               # 虚拟环境
├── frontend/               # Vue3 前端
│   ├── src/
│   │   ├── App.vue         # 布局（侧边栏/顶栏）
│   │   ├── views/          # 7 个页面
│   │   ├── api/            # Axios 封装
│   │   ├── router/         # 路由
│   │   └── style.css       # 全局毛玻璃主题
│   └── dist/               # 构建产物（Nginx 托管）
├── deploy/                 # 部署配置
│   ├── docker-compose.yml  # 容器编排
│   ├── nginx.conf          # Nginx 配置
│   ├── prometheus.yml      # Prometheus 配置
│   ├── promtail-config.yaml
│   └── loki-config.yaml
└── data/                   # 持久化数据卷
    ├── postgres/           # 数据库文件
    ├── models/             # bge-m3 / Qwen 模型
    ├── loki/               # 日志存储
    ├── prometheus/         # 指标存储
    └── grafana/            # Grafana 数据
```

---

## 八、API 接口一览（前缀 `/api`）

| 前缀 | 功能 |
|---|---|
| `/api/auth` | 登录、当前用户 |
| `/api/sop` | SOP 文档：上传/列表/详情/编辑/删除/**下载**/问答/空白录入 |
| `/api/fault` | 故障：录入/检索/分析/列表/流转/复现计数 |
| `/api/report` | 分钟简报、AI 日报生成与查询 |
| `/api/monitor` | 实时指标、趋势、全局巡检、AI 巡检报告 |
| `/api/users` | 团队管理（仅管理员） |
| `/api/approval` | 文档审批、知识空白录用（仅管理员） |
| `/api/scripts` | 脚本模板：增删改查/参数渲染/AI 生成（写操作仅管理员） |
| `/api/rag` | 统一 AI 知识问答 |

**权限模型**：JWT 鉴权 + 两级角色（`admin` 管理员 / `member` 成员），管理员可审批、管团队、管脚本模板。

---

## 九、部署流程

> 部署分四块：**监控栈容器（Compose）→ Ollama 大模型 → 后端（systemd）→ 前端构建 + Nginx**。

### 1. 环境前置要求

- Linux 服务器（本项目为 Ubuntu 22.04）
- Docker + Docker Compose（编排监控栈、数据库、Ollama）
- Python 3.12（后端，用 venv 隔离）
- Node.js 20 + npm（前端构建，用 nvm 管理）
- 磁盘预留：模型约 10GB+（Qwen 7B + bge-m3），另需日志/指标/数据库存储空间

### 2. 获取代码与目录

```bash
cd /opt
git clone <仓库地址> aiops
mkdir -p /opt/aiops/data/{postgres,models,loki,prometheus,grafana,ollama}
```

### 3. 准备 AI 模型（双模型）

| 模型 | 位置 | 说明 |
|---|---|---|
| bge-m3（嵌入） | `/opt/aiops/data/models/bge-m3` | 后端直接本地加载，注意保持符号链接/文件完整 |
| Qwen2.5-7B（大模型） | Ollama 管理（`/opt/aiops/data/ollama`） | 由第 6 步 `ollama pull` 拉取 |

### 4. 配置后端 `.env`

文件位置 `backend/.env`，关键项：

```bash
DATABASE_URL=postgresql+asyncpg://admin:Admin@123456@127.0.0.1:5432/aiops
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1        # Ollama 的 OpenAI 兼容端点
LLM_MODEL=qwen2.5:7b-instruct
EMBEDDING_MODEL=/opt/aiops/data/models/bge-m3
JWT_SECRET=<换成随机长密钥>
PROMETHEUS_URL=http://127.0.0.1:9090
LOKI_URL=http://127.0.0.1:3100
```

### 5. 启动监控栈容器（Docker Compose）

```bash
cd /opt/aiops/deploy
docker compose up -d
```

一次拉起 6 个容器：`postgres`(5432) / `prometheus`(9090) / `node-exporter`(9100) / `grafana`(3000) / `loki`(3100) / `promtail`。

### 6. 启动 Ollama 并拉取大模型

```bash
docker run -d --name ollama -p 11434:11434 \
  -v /opt/aiops/data/ollama:/root/.ollama \
  ollama/ollama

docker exec ollama ollama pull qwen2.5:7b-instruct
```

### 7. 部署后端（systemd 常驻）

```bash
cd /opt/aiops/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

创建 `/etc/systemd/system/aiops-backend.service`：

```ini
[Unit]
Description=AIOps Backend (FastAPI)
After=network.target docker.service

[Service]
WorkingDirectory=/opt/aiops/backend
ExecStart=/opt/aiops/backend/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
Environment=HF_ENDPOINT=https://hf-mirror.com
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aiops-backend
```

> 后端启动时会自动：建表（`CREATE EXTENSION vector` + 建表）→ 初始化默认管理员 `admin` → 启动定时调度器。

### 8. 构建前端

```bash
cd /opt/aiops/frontend
npm install
npm run build        # 产物输出到 dist/，供 Nginx 托管
```

> 开发调试可改用 `npm run dev`（Vite 热更新，自带 `/api` 代理到后端 8000）。

### 9. 启动 Nginx（静态托管 + 反代）

```bash
docker run -d --name aiops-nginx --network host \
  -v /opt/aiops/deploy/nginx.conf:/etc/nginx/conf.d/default.conf \
  -v /opt/aiops/frontend/dist:/opt/aiops/frontend/dist \
  -v /opt/aiops/deploy/.htpasswd:/etc/nginx/.htpasswd \
  nginx:1.27
```

### 10. 验证部署

| 项目 | 地址 | 说明 |
|---|---|---|
| 前端 | `http://<服务器IP>/` | 默认管理员 `admin / Admin@123456`（登录后请改密） |
| 后端健康 | `http://127.0.0.1:8000/health` | 返回 `{"status":"ok"}` |
| 指标 | `http://<服务器IP>:9090` | Prometheus |
| 日志 | `http://<服务器IP>:3100` | Loki |
| 监控大盘 | `http://<服务器IP>/grafana/` | 经 Nginx 反代 |

> **常见排错**：Loki 报 `permission denied` 时执行 `chown -R 10001:10001 /opt/aiops/data/loki`；嵌入模型加载失败时检查 bge-m3 目录符号链接是否指向 `blobs/` 而非 `../../blobs/`。

---

## 十、电梯演讲版（30 秒介绍）

> **「这是一套轻量级 AIOps 平台。**
> 前端用 Vue3，后端用 Python FastAPI；监控数据来自 Prometheus + Loki 这套标准可观测性栈。
> 核心亮点是 **RAG**：把团队的 SOP 文档和历史故障记录用 bge-m3 向量化存进 pgvector，
> 用户提问时语义检索相关内容，再交给本地 Ollama 上的 Qwen 大模型生成带来源的答案。
> 同时它还能自动生成分钟简报、AI 巡检报告、AI 日报，用大模型辅助故障诊断和脚本编写，
> 让运维知识「查得到、问得懂、用得上」。整套用 Docker Compose + systemd + Nginx 部署，单机即可跑起来。」

---

*文档生成日期：2026-10-19*
