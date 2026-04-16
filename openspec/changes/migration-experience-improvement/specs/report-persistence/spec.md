## ADDED Requirements

### Requirement: 迁移报告自动入库
迁移执行引擎完成执行后，系统 SHALL 自动将执行结果写入 `migration_report` 和 `report_detail` 表。

#### Scenario: 执行完成后生成报告记录
- **WHEN** 迁移任务所有 plan_item 执行完毕（成功/失败/跳过）
- **THEN** 引擎创建一条 MigrationReport 记录（含统计摘要）和对应的 ReportDetail 明细行

### Requirement: 报告列表查询
系统 SHALL 提供 `GET /api/reports` 接口支持分页查询历史报告列表。

#### Scenario: 获取报告列表
- **WHEN** 用户访问报告页面或调用列表接口
- **THEN** 返回报告列表（含 id、task_id、摘要统计、生成时间等），支持按 page/page_size 分页

### Requirement: 报告详情查看
系统 SHALL 提供 `GET /api/reports/<id>` 接口返回单个报告的完整明细数据。

#### Scenario: 查看单个报告详情
- **WHEN** 用户点击某条报告的"查看详情"
- **THEN** 返回该报告的摘要信息和所有 ReportDetail 记录（可按 category 筛选）

### Requirement: 单个报告 Excel 下载
系统 SHALL 支持 `GET /api/reports/<id>/download?format=excel` 下载单份 Excel 格式报告。

#### Scenario: 下载 Excel 报告
- **WHEN** 用户点击某条报告的"下载 Excel"
- **THEN** 后端从数据库读取报告数据，生成包含封面摘要、实例概览、监听器明细、不兼容项说明、操作日志的 xlsx 文件并返回下载

### Requirement: 批量报告下载
系统 SHALL 提供 `POST /api/reports/batch-download` 接口支持批量选择报告打包下载。

#### Scenario: 批量下载 ZIP 包
- **WHEN** 用户勾选多条报告并点击"批量下载"
- **THEN** 后端生成每份报告的 Excel 并打包为 ZIP 返回下载

### Requirement: 报告删除
系统 SHALL 提供 `DELETE /api/reports/<id>` 接口支持删除指定报告及其明细。

#### Scenario: 删除单条报告
- **WHEN** 用户点击删除并确认
- **THEN** 对应的 MigrationReport 和级联 ReportDetail 记录被物理删除
