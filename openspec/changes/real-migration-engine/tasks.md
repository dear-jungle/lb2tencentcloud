# 真实迁移执行引擎 — 任务清单

## 1. 腾讯云 CLB 写入服务

- [x] 1.1 新建 `app/services/tencent/clb_writer.py`，实现 `create_listener(lb_id, params)` 方法 — 调用腾讯云 `CreateListener` API，支持 TCP/UDP/HTTP/HTTPS 四种协议
- [x] 1.2 实现 `create_rule(lb_id, listener_id, params)` 方法 — 调用 `CreateRule` API，创建七层转发规则
- [x] 1.3 实现 `describe_listeners(lb_id)` 方法 — 调用 `DescribeListeners` API，用于写前冲突检测
- [x] 1.4 实现 `detect_conflict(lb_id, protocol, port)` 方法 — 检查目标实例指定协议+端口是否已有监听器

## 2. 迁移执行引擎

- [x] 2.1 新建 `app/services/migration/engine.py`，实现 `MigrationEngine` 类
- [x] 2.2 实现 `prepare(task_id, plan_items)` — 将 plan_items 写入 `migration_plan_item` 表（status=pending）
- [x] 2.3 实现 `execute(task_id)` — 主循环：逐项处理（检测冲突 → 设 waiting_confirm → 等待确认 → 调 API → 保存结果）
- [x] 2.4 实现确认等待机制 — 轮询 `migration_plan_item.status` 从 `waiting_confirm` 变为 `confirmed` 或 `skipped`（超时 5 分钟自动跳过）
- [x] 2.5 实现失败处理 — 根据 `fail_mode`（pause/continue）决定暂停等待用户操作还是记录后继续
- [x] 2.6 实现暂停/继续 — 通过 `migration_task.status` 标志位控制

## 3. 后端 API 路由

- [x] 3.1 `POST /api/migration/tasks` — 创建迁移任务：接收 instanceMappings + planItems，写入 migration_task + migration_plan_item 表
- [x] 3.2 `POST /api/migration/tasks/{id}/execute` — 启动执行：在后台线程启动 MigrationEngine.execute()
- [x] 3.3 `GET /api/migration/tasks/{id}/progress` — 轮询进度：返回当前项序号、状态、待确认项详情、最近日志
- [x] 3.4 `POST /api/migration/tasks/{id}/confirm` — 确认/跳过：更新 plan_item.status 为 confirmed/skipped
- [x] 3.5 `POST /api/migration/tasks/{id}/batch-confirm` — 批量确认：一次确认多个同类 waiting_confirm 项

## 4. 前端执行步骤改造

- [x] 4.1 `execute/index.js` — 点击"开始执行"时调用 `POST /tasks` 创建任务 + `POST /tasks/{id}/execute` 启动执行
- [x] 4.2 实现进度轮询 — 每 2 秒调用 `GET /tasks/{id}/progress`，更新进度条和日志面板
- [x] 4.3 实现二次确认弹窗 — 检测到 `waiting_confirm` 状态时弹出 Modal，展示操作详情（类型、目标、参数表格），提供"确认"/"跳过"按钮
- [x] 4.4 实现批量确认复选框 — 弹窗中勾选"批量确认后续同类操作"后调用 batch-confirm API
- [x] 4.5 实现失败处理弹窗 — 失败暂停模式下弹出"重试/跳过/终止"选项
