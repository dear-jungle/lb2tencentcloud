# 开发技术文档

## 技术概述

本项目为阿里云 CLB 配置迁移到腾讯云 CLB 的 Web 工具，采用 Python + Flask 后端 + 原生 JavaScript 前端的技术栈，与已有 lb 项目保持一致的开发框架和模块化设计思想。

---

## 技术栈

### 后端技术

| 技术组件 | 版本 | 用途 |
|---------|------|------|
| **Python** | 3.10+ | 开发语言 |
| **Flask** | >=2.3.0 | Web 框架（轻量级，Blueprint 模块化路由） |
| **Flask-CORS** | >=4.0.0 | 跨域处理 |
| **Gunicorn** | >=21.0.0 | WSGI 服务器（开发模式，含 `--reload` 热重载） |
| **Hypercorn** | >=0.16.0 | ASGI 服务器（生产模式，支持 HTTP/2） |
| **gevent** | >=23.0.0 | 异步处理 |
| **python-dotenv** | >=1.0.0 | 环境变量管理 |
| **aliyun-python-sdk-core** | >=2.13.36 | 阿里云核心 SDK |
| **aliyun-python-sdk-slb** | >=3.3.20 | 阿里云 SLB SDK |
| **tencentcloud-sdk-python** | >=3.0.1000 | 腾讯云 SDK |
| **flask-sock** | >=0.7.0 | WebSocket 支持 |

### 前端技术

| 技术组件 | 版本 | 用途 |
|---------|------|------|
| **原生 JavaScript** | ES6+ | 核心逻辑（无框架依赖） |
| **Materialize CSS** | 1.0.0 | UI 框架（Material Design 风格） |
| **Material Icons** | Latest | 图标资源（本地化部署） |

### 构建工具

| 技术组件 | 版本 | 用途 |
|---------|------|------|
| **Node.js** | 16+ | 构建环境 |
| **Vite** | ^5.0.0 | 构建打包工具 |
| **Terser** | ^5.26.0 | JS 压缩 |
| **vite-plugin-compression** | ^0.5.1 | Gzip/Brotli 压缩 |

### 测试框架

| 技术组件 | 版本 | 用途 |
|---------|------|------|
| **pytest** | >=7.4.0 | 核心测试框架 |
| **pytest-flask** | >=1.2.0 | Flask 应用测试支持 |
| **pytest-mock** | >=3.11.0 | Mock/Patch 支持 |
| **pytest-cov** | >=4.1.0 | 代码覆盖率 |
| **responses** | >=0.23.0 | HTTP 响应 Mock |

---

## 项目结构

```
lb2tencentcloud/
├── app/                    # Flask 应用核心
│   ├── __init__.py        # Flask 应用工厂
│   ├── routes/            # 路由定义（Blueprint 模块化）
│   │   ├── main_routes.py       # 主页路由
│   │   ├── credential_routes.py # 凭证管理
│   │   ├── aliyun_routes.py     # 阿里云 CLB 读取
│   │   ├── tencent_routes.py    # 腾讯云 CLB 读写
│   │   ├── mapping_routes.py    # 配置映射
│   │   ├── migration_routes.py  # 迁移执行
│   │   └── report_routes.py     # 迁移报告
│   ├── services/          # 业务逻辑层
│   │   ├── aliyun/        # 阿里云服务（只读）
│   │   ├── tencent/       # 腾讯云服务（受控读写）
│   │   ├── mapper/        # 配置映射引擎
│   │   ├── migration/     # 迁移执行引擎
│   │   └── report/        # 报告生成服务
│   └── utils/             # 工具函数
├── public/                # 前端静态资源
│   ├── index.html         # 主页面（SPA）
│   ├── css/               # 样式文件
│   ├── js/                # JavaScript 模块
│   │   ├── app.js         # 应用入口
│   │   └── modules/       # 功能模块（ES6 模块化）
│   └── fonts/             # 字体资源（本地化）
├── frontend/              # 前端构建环境
│   ├── package.json       # Node.js 配置
│   └── vite.config.js     # Vite 构建配置
├── dist/                  # 构建产物（生产环境）
├── data/                  # 运行时数据（JSON 文件、SQLite）
├── tests/                 # 测试文件
├── docs/                  # 项目文档
├── logs/                  # 日志文件
├── certs/                 # SSL 证书
├── server.py              # 应用入口
├── start.sh               # 启动脚本
├── run_tests.sh           # 测试运行脚本
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量示例
└── openspec/              # 规格文档
```

---

## 开发环境搭建

### 1. 环境要求

- Python 3.10+
- Node.js 16+（用于前端构建）
- pip 包管理器

### 2. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Node.js 依赖（在 frontend 目录下）
cd frontend && npm install && cd ..
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填写必要配置
```

`.env` 文件示例：
```env
# 服务配置
PORT=10041
DEV_MODE=1

# 日志配置
LOG_LEVEL=DEBUG
```

### 4. 启动开发服务器

```bash
./start.sh
```

---

## 前后端热加载

### 后端热加载（Python）

**机制**：使用 Gunicorn 的 `--reload` 选项

- 监控目录：`app/`、`server.py`
- `.env` 文件变化通过 `--reload-extra-file` 监控
- 修改 `.py` 文件后自动重启，耗时 2-3 秒

**开发模式启动参数**：
```bash
gunicorn server:app \
    --bind "0.0.0.0:10041" \
    --workers 2 \
    --worker-class sync \
    --timeout 120 \
    --reload \
    --reload-extra-file app/ \
    --reload-extra-file public/ \
    --log-level debug
```

**Flask 热加载配置**：
```python
# app/__init__.py
if dev_mode:
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用静态文件缓存
```

### 前端热加载（HTML/CSS/JS）

**方式一：开发模式（推荐日常开发）**
- 完全禁用浏览器缓存
- HTTP 响应头：`Cache-Control: no-cache, no-store, must-revalidate`
- 修改后按 F5 刷新浏览器即可看到效果

**方式二：Vite 开发服务器（支持 HMR）**
```bash
cd frontend && npm run dev
```
- 支持热模块替换（HMR），修改 JS/CSS 后页面自动更新
- 代理 `/api` 请求到后端

### 缓存控制策略

| 模式 | HTML | CSS/JS | API 响应 |
|------|------|--------|---------|
| 开发模式 | 完全禁用缓存 | 完全禁用缓存 | 完全禁用缓存 |
| 生产模式 | 5 分钟 | 1 小时（带 hash） | 按需 |

---

## 模块化设计

### 后端模块化

**Flask Blueprint 按功能拆分路由**：
- `credential_routes.py` — 凭证管理（验证、地域列表）
- `aliyun_routes.py` — 阿里云 CLB 只读操作
- `tencent_routes.py` — 腾讯云 CLB 读写操作
- `mapping_routes.py` — 配置映射
- `migration_routes.py` — 迁移执行
- `report_routes.py` — 报告查看

**三层架构**：
```
路由层(Routes) → 服务层(Services) → 数据层(SDK/Storage)
```

**设计模式应用**：
- **工厂模式**：`AliyunClientFactory`、`TencentClientFactory` — 创建云平台客户端
- **策略模式**：`SchedulerConverter`、`HealthCheckConverter` — 配置转换策略
- **门面模式**：`AliyunService`、`TencentService` — 统一服务入口
- **仓储模式**：迁移任务状态持久化

**文件行数规范**：
- 路由层：< 200 行/文件
- 服务层：< 300 行/文件
- 转换器/策略层：< 150 行/文件

### 前端模块化

**ES6 模块系统**（`import/export`）：

```
public/js/
├── app.js              # 应用统一入口（门面模式）
└── modules/
    ├── core/           # 核心模块
    │   ├── state-manager.js   # 全局状态管理（单例模式）
    │   ├── api-service.js     # API 调用封装（单例模式）
    │   └── http-client.js     # HTTP 客户端
    ├── wizard/         # 分步向导
    │   ├── step-navigator.js  # 步骤导航管理
    │   └── step-renderer.js   # 步骤页面渲染
    ├── credential/     # 凭证管理 UI
    ├── aliyun/         # 阿里云配置展示
    ├── mapping/        # 配置映射展示
    ├── migration/      # 迁移执行（进度、日志、WebSocket）
    └── report/         # 报告展示
```

**前端代码规范**：
- 每个 JS 文件 < 200 行，职责单一
- 类名大驼峰（如 `StateManager`）、函数名小驼峰（如 `loadRegions`）、常量全大写
- JSDoc 注释（功能描述、参数、返回值）
- 使用状态管理而非全局变量
- 使用 ApiService 封装而非直接 fetch
- 统一错误处理

---

## API 设计规范

### RESTful API 设计原则

1. **资源导向**：URL 表示资源，HTTP 方法表示操作
2. **统一响应格式**：

```json
// 成功响应
{"success": true, "data": {...}, "message": "操作成功"}

// 错误响应
{"success": false, "error": "ERROR_CODE", "message": "错误描述"}
```

3. **HTTP 状态码规范**：200 成功、400 参数错误、404 不存在、500 内部错误

### 主要 API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /api/credentials/aliyun/verify | 验证阿里云凭证 |
| POST | /api/credentials/tencent/verify | 验证腾讯云凭证 |
| GET | /api/aliyun/regions | 获取阿里云地域列表 |
| GET | /api/aliyun/clb/instances | 获取阿里云 CLB 实例列表 |
| GET | /api/aliyun/clb/instances/{id}/config | 获取 CLB 完整配置 |
| POST | /api/mapping/generate | 生成配置映射结果 |
| POST | /api/migration/plan | 生成迁移计划 |
| POST | /api/migration/execute | 执行迁移 |
| GET | /api/migration/status/{task_id} | 查询迁移状态 |
| POST | /api/migration/pause/{task_id} | 暂停迁移 |
| POST | /api/migration/resume/{task_id} | 继续迁移 |
| GET | /api/report/{task_id} | 获取迁移报告 |
| GET | /api/report/{task_id}/export | 导出报告（JSON/CSV） |
| GET | /api/health | 健康检查 |

---

## 构建与部署

### 开发模式

```bash
./start.sh              # 启动（不打包，使用源文件，热重载）
```

### 生产模式

```bash
./start.sh --prod --build   # 构建打包 + 生产启动（Hypercorn HTTP/2）
```

### Vite 构建配置要点

- **代码分割**：按功能模块分割（core、wizard、aliyun、tencent、mapping、migration、report）
- **Terser 压缩**：生产环境移除 console.log、debugger
- **Gzip/Brotli 压缩**：>10KB 的资源自动压缩
- **资源 Hash**：文件名带 hash 指纹，便于缓存控制
- **CSS 代码分割**：独立 CSS 文件

---

## 安全规范

- **凭证安全**：AK/SK 仅存于服务端内存会话，不持久化，不写入日志
- **源端只读**：阿里云仅调用 Describe*/List* 类只读接口
- **目标端二次确认**：腾讯云所有写操作必须前端弹窗确认
- **HTTPS 传输**：前后端通信全程加密
- **CORS 控制**：开发模式 `*`，生产模式白名单
- **日志脱敏**：不记录 AccessKey/SecretKey
- **输入验证**：所有 API 参数经验证后才使用

---

## 日志规范

**日志级别**：
- **DEBUG**：详细的 API 调用参数（仅开发环境）
- **INFO**：业务操作日志（"开始拉取配置"、"映射完成"）
- **WARNING**：非致命问题（"不兼容配置项已跳过"）
- **ERROR**：错误信息（API 调用失败、参数验证失败）

**日志文件**：
- `logs/app.log` — 应用日志
- `logs/api.log` — API 调用日志
- `logs/migration.log` — 迁移操作日志

**日志格式**：
```
2026-04-10 16:30:52,123 [INFO] app.services.migration: 开始迁移任务 task-001，共 15 项
```
