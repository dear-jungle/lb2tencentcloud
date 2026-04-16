# 导出 Excel 报告 — 任务清单

## 1. 引入 SheetJS 库

- [x] 1.1 下载 `xlsx.full.min.js` 到 `public/js/` 目录（本地化，不引用公网 CDN）
- [x] 1.2 在 `report/index.js` 中通过动态 `<script>` 标签懒加载（render 时才加载，不阻塞其他步骤）

## 2. 实现 Excel 导出核心逻辑（report/index.js）

- [x] 2.1 实现 `buildCoverSheet(state)` — 封面·迁移摘要：迁移时间、源端/目标端账号地域、实例数、整体结论文字、成功率
- [x] 2.2 实现 `buildInstanceSheet(state)` — 实例迁移概览：每对实例一行，中文列名
- [x] 2.3 实现 `buildListenerSheet(state)` — 监听器配置明细：每个监听器一行，中文列名
- [x] 2.4 实现 `buildIncompatibleSheet(state)` — 不兼容项说明：中文列名
- [x] 2.5 实现 `buildLogSheet(state)` — 操作日志：序号、操作描述、结果、错误信息
- [x] 2.6 实现 `applyStyles(wb)` — 列宽自适应（社区版不支持颜色样式，作为预留）
- [x] 2.7 实现 `exportExcel(state)` — 组装 5 个 Sheet，`xlsx.writeFile()` 触发下载，文件名 `迁移报告_YYYY-MM-DD.xlsx`

## 3. 更新报告页面 UI（report/index.js）

- [x] 3.1 "导出 Excel 报告" 为绿色主按钮，"导出 JSON" 改为 btn-flat 次要样式
- [x] 3.2 Excel 导出点击时：检查 SheetJS 是否加载完成，未完成显示 loading，完成后执行导出
