# cloud-credentials Specification

## Purpose
TBD - created by archiving change aliyun-clb-migration. Update Purpose after archive.
## Requirements
### Requirement: 阿里云凭证输入
系统 SHALL 提供表单让用户输入阿里云 AccessKey ID 和 AccessKey Secret，输入框 SHALL 使用密码掩码显示。

#### Scenario: 用户输入阿里云凭证
- **WHEN** 用户在凭证输入表单中填写阿里云 AccessKey ID 和 AccessKey Secret
- **THEN** 系统以掩码方式显示 Secret，不以明文展示

### Requirement: 腾讯云凭证输入
系统 SHALL 提供表单让用户输入腾讯云 SecretId 和 SecretKey，输入框 SHALL 使用密码掩码显示。

#### Scenario: 用户输入腾讯云凭证
- **WHEN** 用户在凭证输入表单中填写腾讯云 SecretId 和 SecretKey
- **THEN** 系统以掩码方式显示 SecretKey，不以明文展示

### Requirement: 阿里云凭证连接测试
系统 SHALL 在用户提交阿里云凭证后自动调用阿里云 SLB API 进行连接测试，验证凭证有效性和权限。

#### Scenario: 阿里云凭证有效
- **WHEN** 用户提交有效的阿里云凭证
- **THEN** 系统显示连接成功提示，并展示关联的账号信息（如 UID）

#### Scenario: 阿里云凭证无效
- **WHEN** 用户提交无效的阿里云凭证
- **THEN** 系统显示明确的错误信息（如"AccessKey 无效"或"权限不足"），不允许进入下一步

### Requirement: 腾讯云凭证连接测试
系统 SHALL 在用户提交腾讯云凭证后自动调用腾讯云 CLB API 进行连接测试，验证凭证有效性和权限。

#### Scenario: 腾讯云凭证有效
- **WHEN** 用户提交有效的腾讯云凭证
- **THEN** 系统显示连接成功提示，并展示关联的账号信息（如 AppId）

#### Scenario: 腾讯云凭证无效
- **WHEN** 用户提交无效的腾讯云凭证
- **THEN** 系统显示明确的错误信息，不允许进入下一步

### Requirement: 凭证安全传输
系统 SHALL 通过 HTTPS 传输凭证，凭证 SHALL NOT 以明文写入日志或持久化存储到磁盘文件。

#### Scenario: 凭证传输安全
- **WHEN** 用户提交凭证到后端 API
- **THEN** 请求通过 HTTPS 加密通道传输，后端日志中不包含凭证明文

### Requirement: 地域选择
系统 SHALL 在凭证验证通过后，允许用户分别选择阿里云源端地域和腾讯云目标端地域。地域列表 SHALL 仅包含中国大陆地域。

#### Scenario: 选择地域
- **WHEN** 凭证验证通过后
- **THEN** 系统展示阿里云中国大陆可用地域列表和腾讯云中国大陆可用地域列表，用户各选择一个地域

### Requirement: 凭证 .env 预配置复用
系统 SHALL 支持从 .env 文件加载预配置的凭证，并允许用户将当前凭证保存到 .env 文件供下次复用。

#### Scenario: 启动时自动加载 .env 凭证
- **WHEN** 系统启动时检测到 .env 文件中配置了阿里云/腾讯云凭证
- **THEN** 自动填充到凭证输入表单中，用户无需重复输入

#### Scenario: 用户保存凭证到 .env
- **WHEN** 用户点击"保存凭证"按钮
- **THEN** 系统将当前凭证写入 .env 文件（.env 不入版本控制）

