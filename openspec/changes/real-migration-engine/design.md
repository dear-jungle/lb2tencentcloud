# 真实迁移执行引擎 — 设计文档

## Goals

- 实现真实的腾讯云 CLB 写入（CreateListener + CreateRule）
- 写操作前必须经用户确认（二次确认弹窗）
- 写操作前检测冲突（目标端已有同端口监听器）
- 执行状态持久化到 MySQL（支持断点续传）
- 前端对接后端 API，替换纯前端模拟

**Non-Goals:**
- 不做 ModifyListener（修改已有监听器）— 风险高，后续迭代
- 不做健康检查/会话保持/ACL/带宽等高级参数写入 — 后续迭代
- 不做 WebSocket — 先用轮询
- 不做创建 CLB 实例

## 架构决策

### 决策 1：前后端交互模式 — 轮询 + 确认回调

**选择**：后端逐项执行，遇到写操作暂停等待确认，前端轮询进度并提交确认/跳过。

**流程**：
```
前端                                后端
  │                                   │
  ├─ POST /execute ──────────────────►│ 开始执行
  │                                   │ 处理第1项...
  │◄─ GET /progress ──────────────────│ status: running, current: 1
  │                                   │ 遇到写操作 → 暂停
  │◄─ GET /progress ──────────────────│ status: waiting_confirm, pending_item: {...}
  │                                   │
  ├─ POST /confirm {action: "confirm"}►│ 用户确认
  │                                   │ 调用 CreateListener API
  │                                   │ 成功 → 继续下一项
  │◄─ GET /progress ──────────────────│ status: running, current: 2
  │                                   │ ...
  │◄─ GET /progress ──────────────────│ status: completed
```

### 决策 2：执行引擎架构

**选择**：同步执行 + 线程隔离

```python
class MigrationEngine:
    def execute(self, task_id, plan_items):
        for item in plan_items:
            # 1. 冲突检测
            conflict = self._detect_conflict(item)
            # 2. 等待用户确认（设置 status=waiting_confirm）
            self._wait_for_confirmation(item)
            # 3. 调用腾讯云 API
            result = self._execute_item(item)
            # 4. 持久化结果
            self._save_result(item, result)
```

用 `threading.Thread` 在后台线程执行，主线程处理 HTTP 请求。确认通过数据库中间表通信（`plan_item.status` 从 `waiting_confirm` 变为 `confirmed`）。

### 决策 3：腾讯云写入 API 封装

**新建 `app/services/tencent/clb_writer.py`**（写入服务，与只读的 `clb_service.py` 分离）：

| 方法 | 腾讯云 API | 参数 |
|------|-----------|------|
| `create_listener()` | `CreateListener` | LoadBalancerId, Protocol, Port, Scheduler 等 |
| `create_rule()` | `CreateRule` | LoadBalancerId, ListenerId, Domain, Url 等 |
| `describe_listeners()` | `DescribeListeners` | LoadBalancerId（冲突检测用） |

**安全约束**：
- 只封装 Create 类 API（不封装 Modify/Delete）
- 每个方法调用前必须校验 `item.user_confirmed == True`
- 所有 API 调用记录到 `execution_log` 表

### 决策 4：二次确认弹窗交互

**前端 Modal 弹窗**：
```
┌─────────────────────────────────────────┐
│  操作确认                         [✕]    │
├─────────────────────────────────────────┤
│                                         │
│  操作类型：创建监听器                     │
│  目标实例：lb-xxx (实例X)                │
│                                         │
│  ┌─────────────┬───────────────────┐    │
│  │ 参数         │ 值                │    │
│  ├─────────────┼───────────────────┤    │
│  │ 协议         │ TCP              │    │
│  │ 端口         │ 80               │    │
│  │ 调度算法     │ WRR              │    │
│  │ 健康检查     │ 关闭             │    │
│  └─────────────┴───────────────────┘    │
│                                         │
│  □ 批量确认后续同类操作                   │
│                                         │
│     [跳过]                    [确认执行]  │
└─────────────────────────────────────────┘
```

### 决策 5：错误处理

| 场景 | 行为 |
|------|------|
| API 调用成功 | 记录 success，继续下一项 |
| API 调用失败（失败暂停模式） | 暂停，弹窗：重试/跳过/终止 |
| API 调用失败（失败继续模式） | 记录 failed，自动继续 |
| 用户跳过确认 | 记录 skipped，继续 |
| 网络超时 | 重试 1 次，仍失败则按失败处理 |

### 决策 6：数据持久化

复用已有 `MigrationPlanItem` 模型：
- 执行前：创建 task + plan_items 记录（`status=pending`）
- 等待确认：`status=waiting_confirm`，`request_params` 存 API 参数
- 用户确认：`status=confirmed`，`user_confirmed=True`，`confirmed_at`
- 执行中：`status=running`，`executed_at`
- 完成：`status=success/failed/skipped`，`response_data/error_message`

## API 设计

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/migration/tasks` | POST | 创建迁移任务 + plan_items |
| `/api/migration/tasks/{id}/execute` | POST | 启动执行（后台线程） |
| `/api/migration/tasks/{id}/progress` | GET | 轮询进度（当前项、状态、日志） |
| `/api/migration/tasks/{id}/confirm` | POST | 确认/跳过当前待确认项 |
| `/api/migration/tasks/{id}/batch-confirm` | POST | 批量确认多项 |
| `/api/migration/tasks/{id}/pause` | POST | 暂停 |
| `/api/migration/tasks/{id}/resume` | POST | 继续 |
