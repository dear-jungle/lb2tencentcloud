# tencent-clb-writer Specification (Delta)

## MODIFIED Requirements

### Requirement: 实现 CreateListener 写入
系统 SHALL 封装腾讯云 CLB `CreateListener` API，支持创建 TCP/UDP/HTTP/HTTPS 四种协议的监听器。

#### Scenario: 创建 TCP/UDP 四层监听器
- **WHEN** 迁移计划项类型为 `create_listener` 且协议为 TCP 或 UDP
- **THEN** 系统调用 `CreateListener` API，传入协议、端口、调度算法等参数，返回新创建的 ListenerId

#### Scenario: 创建 HTTP/HTTPS 七层监听器
- **WHEN** 迁移计划项类型为 `create_listener` 且协议为 HTTP 或 HTTPS
- **THEN** 系统调用 `CreateListener` API，传入协议、端口、调度算法等参数，返回新创建的 ListenerId

### Requirement: 实现 CreateRule 写入
系统 SHALL 封装腾讯云 CLB `CreateRule` API，支持为七层监听器创建转发规则。

#### Scenario: 创建转发规则
- **WHEN** 迁移计划项类型为 `create_rule`
- **THEN** 系统调用 `CreateRule` API，传入 ListenerId、域名、URL 路径等参数

### Requirement: 写前冲突检测
系统 SHALL 在执行写操作前，拉取目标 CLB 实例已有监听器列表，检测端口是否已占用。

#### Scenario: 端口未占用
- **WHEN** 目标 CLB 实例无同协议同端口的监听器
- **THEN** 正常弹出确认弹窗，用户确认后创建

#### Scenario: 端口已占用
- **WHEN** 目标 CLB 实例已存在同协议同端口的监听器
- **THEN** 在确认弹窗中标红提示冲突详情，用户选择覆盖（跳过创建）或跳过该项
