# config-mapping-engine Specification

## Purpose
TBD - created by archiving change aliyun-clb-migration. Update Purpose after archive.
## Requirements
### Requirement: 监听器协议映射
系统 SHALL 将阿里云 CLB 监听器协议类型（TCP/UDP/HTTP/HTTPS）映射为腾讯云 CLB 对应的监听器协议类型。

#### Scenario: 支持的协议类型映射
- **WHEN** 阿里云监听器协议为 TCP、UDP、HTTP 或 HTTPS
- **THEN** 系统映射为腾讯云 CLB 对应的同名协议类型

#### Scenario: 不支持的协议类型
- **WHEN** 阿里云存在腾讯云不支持的协议类型
- **THEN** 系统标记该监听器为"不兼容"，并生成提醒信息说明原因

### Requirement: 调度算法映射
系统 SHALL 将阿里云 CLB 调度算法映射为腾讯云 CLB 对应的调度算法，包括加权轮询（wrr）、加权最小连接数（wlc）等。

#### Scenario: 调度算法可映射
- **WHEN** 阿里云调度算法在腾讯云有对应算法
- **THEN** 系统自动完成映射并展示对应关系

#### Scenario: 调度算法不可映射
- **WHEN** 阿里云调度算法在腾讯云无对应算法
- **THEN** 系统标记为"不兼容"，建议用户选择腾讯云可用的替代算法

### Requirement: 健康检查配置映射
系统 SHALL 将阿里云健康检查配置项（协议、端口、路径、间隔、超时、阈值等）映射为腾讯云对应配置项。

#### Scenario: 健康检查配置映射
- **WHEN** 系统处理健康检查配置
- **THEN** 逐字段映射并标注字段名差异、取值范围差异

### Requirement: 转发规则映射
系统 SHALL 将阿里云 HTTP/HTTPS 监听器的转发规则（域名、URL 路径匹配）映射为腾讯云 CLB 的转发规则。

#### Scenario: 转发规则映射
- **WHEN** 阿里云存在基于域名和 URL 的转发规则
- **THEN** 系统映射为腾讯云 CLB 的七层转发规则

### Requirement: 端口映射
系统 SHALL 映射阿里云监听器前端端口和后端端口到腾讯云对应配置。

#### Scenario: 端口映射
- **WHEN** 阿里云监听器配置了前端和后端端口
- **THEN** 系统将端口配置映射到腾讯云对应字段

### Requirement: 不兼容配置识别
系统 SHALL 识别所有无法映射或腾讯云不支持的阿里云配置项，生成不兼容项清单。

#### Scenario: 存在不兼容配置
- **WHEN** 配置映射过程中发现不兼容项
- **THEN** 系统将所有不兼容项汇总到独立清单，包含配置项名称、阿里云值、不兼容原因

### Requirement: 实例映射关系
系统 SHALL 支持用户配置 CLB 实例的一对一和多对一映射关系。一对多映射暂不支持。

#### Scenario: 一对一映射
- **WHEN** 用户选择将 1 个阿里云 CLB 实例映射到 1 个腾讯云 CLB 实例
- **THEN** 系统记录该映射关系并用于后续迁移

#### Scenario: 多对一映射
- **WHEN** 用户选择将多个阿里云 CLB 实例的配置合并到 1 个腾讯云 CLB 实例
- **THEN** 系统检测端口冲突，冲突时展示冲突列表，用户逐项选择处理方式（覆盖/跳过/重命名端口）

### Requirement: 高级参数映射
系统 SHALL 将阿里云 CLB 的高级参数（连接超时、空闲超时、会话保持配置）映射为腾讯云 CLB 对应配置。

#### Scenario: 高级参数可映射
- **WHEN** 阿里云高级参数在腾讯云有对应配置项
- **THEN** 系统自动完成映射并展示对应关系

#### Scenario: 高级参数不可映射
- **WHEN** 阿里云高级参数在腾讯云无对应配置项
- **THEN** 系统标记为"不兼容"，并说明原因

### Requirement: 策略配置映射
系统 SHALL 将阿里云 CLB 的策略配置（带宽限制、访问控制 ACL）映射为腾讯云 CLB 对应的安全组/访问控制策略。

#### Scenario: 访问控制策略映射
- **WHEN** 阿里云 CLB 配置了访问控制 ACL 策略
- **THEN** 系统映射为腾讯云 CLB 的安全组或访问控制策略，不可映射的部分标记为"不兼容"

#### Scenario: 带宽限制映射
- **WHEN** 阿里云 CLB 配置了带宽限制
- **THEN** 系统映射为腾讯云 CLB 对应的带宽配置

