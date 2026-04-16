# config-mapping-engine Specification (Delta)

## MODIFIED Requirements

### Requirement: 映射引擎支持按实例分组
映射引擎 SHALL 支持按实例维度分组映射，保留源端实例→目标端实例的关联信息。

#### Scenario: 按实例分组映射
- **WHEN** 前端传入按实例分组的监听器数据
- **THEN** 映射结果保留实例分组信息，每个映射项标注所属源端实例ID

### Requirement: 不兼容项推荐替代方案
映射引擎 SHALL 为不兼容配置项推荐功能最接近的替代方案。推荐逻辑为功能最接近优先。

#### Scenario: 调度算法有替代
- **WHEN** 源端调度算法（如 sch 源地址哈希）在腾讯云不直接支持
- **THEN** 系统推荐功能最接近的替代方案（如 WRR），填入 `recommendation` 字段，`alternatives` 列出所有可选项

#### Scenario: 配置无替代
- **WHEN** 配置项完全无替代方案
- **THEN** `recommendation` 字段为空，`severity` 为 `error`
