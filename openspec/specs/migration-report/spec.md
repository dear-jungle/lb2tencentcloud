# migration-report Specification

## Purpose
TBD - created by archiving change aliyun-clb-migration. Update Purpose after archive.
## Requirements
### Requirement: 迁移报告生成
系统 SHALL 在迁移完成后自动生成迁移报告，汇总所有迁移操作的结果。

#### Scenario: 迁移完成生成报告
- **WHEN** 所有迁移操作执行完毕（包括成功、失败、跳过的项）
- **THEN** 系统自动生成迁移报告页面

### Requirement: 报告内容分类展示
系统 SHALL 在报告中将迁移项按结果分类展示：成功项、失败项、跳过项、不兼容项。

#### Scenario: 分类汇总展示
- **WHEN** 用户查看迁移报告
- **THEN** 报告以分类标签页或分区展示四类结果，每类显示数量和明细列表

### Requirement: 报告详情
系统 SHALL 在报告中为每个迁移项展示详细信息：源配置、目标配置、执行时间、结果、错误信息（如有）。

#### Scenario: 查看迁移项详情
- **WHEN** 用户在报告中点击某个迁移项
- **THEN** 展开显示该项的完整详情，包括源/目标配置对比和执行日志

### Requirement: 报告导出
系统 SHALL 将 Excel（`.xlsx`）作为主要导出格式，生成面向业务人员可读的多 Sheet 报告。JSON 导出保留作为辅助格式。

#### Scenario: 导出 Excel 报告
- **WHEN** 用户点击"导出 Excel 报告"按钮
- **THEN** 系统在浏览器端生成并下载 `.xlsx` 文件，包含 5 个 Sheet：封面·迁移摘要、实例迁移概览、监听器配置明细、不兼容项说明、操作日志

#### Scenario: Excel 中文字段名
- **WHEN** 用户查看 Excel 明细 Sheet
- **THEN** 所有列标题使用中文业务术语，状态值用中文（成功/失败/跳过/不兼容）

#### Scenario: 导出 JSON 报告（辅助）
- **WHEN** 用户点击"导出 JSON"按钮
- **THEN** 系统生成并下载 JSON 格式的报告文件

### Requirement: 报告统计摘要
系统 SHALL 在报告顶部展示统计摘要：总迁移项数、成功数、失败数、跳过数、不兼容数、耗时。

#### Scenario: 展示统计摘要
- **WHEN** 用户打开迁移报告
- **THEN** 报告顶部展示统计卡片，一目了然

