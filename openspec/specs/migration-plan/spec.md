# migration-plan Specification

## Purpose
TBD - created by archiving change aliyun-clb-migration. Update Purpose after archive.
## Requirements
### Requirement: 生成迁移计划
系统 SHALL 根据配置映射结果自动生成迁移计划，包含所有待迁移项、映射关系、不兼容提醒。

#### Scenario: 成功生成迁移计划
- **WHEN** 配置映射完成
- **THEN** 系统生成迁移计划，列出每个待迁移的监听器、转发规则及其目标配置

### Requirement: 迁移计划预览
系统 SHALL 以可视化方式展示迁移计划，用户可查看每一项迁移操作的源配置和目标配置对比。

#### Scenario: 预览迁移计划
- **WHEN** 迁移计划生成后
- **THEN** 系统以表格/列表方式展示源（阿里云）→ 目标（腾讯云）的配置对比，用颜色区分新增、修改、不兼容项

### Requirement: 不兼容项醒目提醒
系统 SHALL 在迁移计划中以醒目方式（如红色标记、警告图标）展示所有不兼容或无法映射的配置项。

#### Scenario: 不兼容项提醒
- **WHEN** 迁移计划中存在不兼容项
- **THEN** 系统用红色/警告样式标注不兼容项，并展示原因说明

### Requirement: 用户确认迁移计划
系统 SHALL 要求用户在执行迁移前明确确认迁移计划，用户 MUST 点击确认按钮后才可开始执行。

#### Scenario: 用户确认执行
- **WHEN** 用户查看完迁移计划后点击"确认执行"按钮
- **THEN** 系统开始执行迁移

#### Scenario: 用户取消
- **WHEN** 用户在预览迁移计划后选择取消
- **THEN** 系统不执行任何迁移操作，用户可返回修改映射配置

### Requirement: 迁移计划可编辑
系统 SHALL 允许用户在确认前对迁移计划进行微调，包括跳过某些不想迁移的项。

#### Scenario: 跳过某些迁移项
- **WHEN** 用户在迁移计划中取消勾选某些配置项
- **THEN** 这些配置项在迁移执行时被跳过，状态标记为"已跳过"

