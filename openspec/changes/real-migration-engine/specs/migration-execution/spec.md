# migration-execution Specification (Delta)

## MODIFIED Requirements

### Requirement: 后端迁移执行引擎
系统 SHALL 实现后端执行引擎，逐项执行迁移计划，每项操作经用户确认后调用腾讯云 API，结果实时持久化到 MySQL。

#### Scenario: 逐项执行
- **WHEN** 用户点击"开始执行"
- **THEN** 后端逐项处理 planItems，每项流程：检测冲突 → 请求用户确认 → 调用 API → 记录结果

#### Scenario: 状态持久化
- **WHEN** 每项操作完成（成功/失败/跳过）
- **THEN** 通过 MySQL 事务更新 migration_plan_item 表的 status、response_data、error_message

### Requirement: 前端对接后端执行 API
系统 SHALL 将前端执行步骤从纯模拟改为调用后端 API，实时轮询进度。

#### Scenario: 发起执行请求
- **WHEN** 用户点击"开始执行"
- **THEN** 前端调用 `POST /api/migration/tasks/{id}/execute`，后端异步执行

#### Scenario: 轮询进度
- **WHEN** 迁移正在执行
- **THEN** 前端每 2 秒轮询 `GET /api/migration/tasks/{id}/progress`，更新进度条和日志

### Requirement: 二次确认弹窗交互
系统 SHALL 在每个写操作前暂停，等待前端用户确认。支持逐项确认和批量确认两种模式。

#### Scenario: 逐项确认
- **WHEN** 后端执行到某项写操作，返回 `status: waiting_confirm`
- **THEN** 前端弹出 Modal，展示操作详情（操作类型、目标资源、参数摘要），用户点击"确认"或"跳过"

#### Scenario: 批量确认
- **WHEN** 用户开启"批量确认"模式
- **THEN** 后端将所有待确认项一次返回，前端弹出列表让用户勾选确认
