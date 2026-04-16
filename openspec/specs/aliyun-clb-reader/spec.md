# aliyun-clb-reader Specification

## Purpose
TBD - created by archiving change aliyun-clb-migration. Update Purpose after archive.
## Requirements
### Requirement: 拉取阿里云 CLB 实例列表
系统 SHALL 根据用户选定的地域，通过阿里云 SLB API 只读拉取该地域下所有 CLB 实例列表，展示实例 ID、名称、状态、网络类型、VIP 地址等关键信息。

#### Scenario: 成功拉取实例列表
- **WHEN** 用户选定阿里云地域且凭证有效
- **THEN** 系统展示该地域下所有 CLB 实例的列表，包含实例 ID、名称、状态、网络类型、VIP

#### Scenario: 该地域无 CLB 实例
- **WHEN** 用户选定的地域下无 CLB 实例
- **THEN** 系统展示"该地域下无 CLB 实例"提示

### Requirement: 用户选择待迁移实例
系统 SHALL 允许用户从实例列表中勾选一个或多个需要迁移的 CLB 实例。

#### Scenario: 用户选择多个实例
- **WHEN** 用户从列表中勾选多个 CLB 实例
- **THEN** 系统记录用户选择，允许进入下一步

### Requirement: 拉取监听器配置
系统 SHALL 对用户选定的每个 CLB 实例，只读拉取其所有监听器配置，包括协议类型（TCP/UDP/HTTP/HTTPS）、端口、转发规则、调度算法等。

#### Scenario: 拉取监听器成功
- **WHEN** 系统为选定实例拉取监听器配置
- **THEN** 返回完整的监听器列表，包含协议、端口、调度算法、转发规则等字段

### Requirement: 拉取健康检查配置
系统 SHALL 对每个监听器只读拉取其健康检查配置，包括检查协议、端口、路径、间隔、阈值等。

#### Scenario: 拉取健康检查成功
- **WHEN** 系统为监听器拉取健康检查配置
- **THEN** 返回健康检查的完整配置项

### Requirement: 拉取转发规则
系统 SHALL 对 HTTP/HTTPS 监听器只读拉取其转发规则（域名、URL 路径、后端服务器组等）。

#### Scenario: 拉取转发规则成功
- **WHEN** 系统为 HTTP/HTTPS 监听器拉取转发规则
- **THEN** 返回所有转发规则，包含域名、URL 路径、后端服务器组引用等

### Requirement: 拉取高级参数
系统 SHALL 对每个监听器只读拉取高级参数，包括连接超时、空闲超时、会话保持配置等。

#### Scenario: 拉取高级参数成功
- **WHEN** 系统为监听器拉取高级参数
- **THEN** 返回连接超时、空闲超时、会话保持类型及参数等完整配置

### Requirement: 拉取策略配置
系统 SHALL 对每个 CLB 实例或监听器只读拉取策略配置，包括带宽限制和访问控制 ACL 策略。

#### Scenario: 拉取策略配置成功
- **WHEN** 系统为 CLB 实例/监听器拉取策略配置
- **THEN** 返回带宽限制参数和访问控制 ACL 规则列表

### Requirement: 阿里云全程只读
系统 SHALL NOT 调用阿里云的任何写入、修改或删除 API。所有阿里云 API 调用 MUST 为只读（Describe/List 类操作）。

#### Scenario: 阿里云只读保证
- **WHEN** 系统与阿里云 API 交互
- **THEN** 仅调用 Describe*/List* 类只读接口，不调用 Create/Modify/Delete/Set 类接口

### Requirement: 配置数据可视化展示
系统 SHALL 以树形或表格形式可视化展示拉取到的 CLB 配置层级结构（实例 → 监听器 → 转发规则 → 后端服务器组）。

#### Scenario: 展示配置层级
- **WHEN** 配置拉取完成
- **THEN** 以可展开的树形结构展示 实例 > 监听器 > 转发规则的层级关系

