## ADDED Requirements

### Requirement: 目标端监听器冲突检测 API
后端 SHALL 提供 `POST /api/mapping/detect-target-conflicts` 接口，用于检测待迁移监听器与目标实例已有监听器的协议+端口冲突。

#### Scenario: 检测到协议端口冲突
- **WHEN** 前端调用冲突检测接口传入 targetInstanceId 和 listeners 列表，目标实例上存在相同 protocol+port 的已有监听器
- **THEN** 接口返回 `has_conflict: true` 和冲突详情列表（含 protocol、port、existing_listener_id、conflicting_source）

#### Scenario: 无冲突
- **WHEN** 目标实例上不存在与待迁移监听器相同的 protocol+port 组合
- **THEN** 接口返回 `has_conflict: false`，conflicts 为空数组

#### Scenario: 目标实例无监听器
- **WHEN** 目标实例尚未创建任何监听器
- **THEN** 接口返回 `has_conflict: false`

### Requirement: 前端集成目标端冲突检测结果
配置映射阶段 SHALL 在映射结果展示区域中同时呈现目标端冲突警告，阻止存在未解决冲突的用户继续执行。

#### Scenario: 冲突项展示在映射结果页
- **WHEN** 映射执行完成后存在目标端监听器冲突
- **THEN** 页面顶部显示红色警告面板，列出每个冲突项（协议:端口 + 所属源实例 + 目标已有监听器ID），"下一步"按钮禁用或变为"强制继续"

#### Scenario: 解决冲突后恢复操作
- **WHEN** 用户通过修改目标端关联或调整监听配置消除了所有冲突
- **THEN** 警告面板消失，"下一步"按钮恢复正常可用状态

### Requirement: 多对一端口冲突保留
已有的多对一源端端口冲突检测功能 SHALL 保持不变，与目标端冲突检测并行运行。

#### Scenario: 多对一冲突仍正常工作
- **WHEN** 多个源端实例关联到同一目标实例且存在重复 protocol+port
- **THEN** 现有的冲突面板正常展示，不受新增检测影响
