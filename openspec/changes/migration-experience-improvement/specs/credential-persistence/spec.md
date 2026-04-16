## ADDED Requirements

### Requirement: 凭证 Cookie 持久化存储
系统 SHALL 在用户填写并验证凭证后，将阿里云和腾讯云的凭证信息加密保存到浏览器 Cookie 中，有效期 7 天。

#### Scenario: 验证成功后自动保存凭证到 Cookie
- **WHEN** 用户在凭证步骤验证阿里云/腾讯云连接成功
- **THEN** 系统将凭证（AccessKey ID/Secret、SecretId/SecretKey、地域）经混淆编码后写入 Cookie，设置 Max-Age=604800（7天）

#### Scenario: 页面加载时自动填充已保存的凭证
- **WHEN** 用户打开凭证配置页面且浏览器中存在有效的凭证 Cookie
- **THEN** 系统从 Cookie 读取并解码凭证信息，自动填充到对应输入框中

#### Scenario: 凭证过期或不存在时不自动填充
- **WHEN** 用户打开凭证配置页面且 Cookie 已过期或不存在
- **THEN** 输入框保持空白，不触发任何错误提示

### Requirement: 手动清除凭证缓存
系统 SHALL 提供手动清除已保存凭证的操作入口。

#### Scenario: 用户主动清除凭证
- **WHEN** 用户点击"清除已保存凭证"按钮
- **THEN** 系统删除对应 Cookie，清空输入框，显示确认提示

### Requirement: Cookie 安全属性
凭证 Cookie SHALL 设置安全相关的属性以降低泄露风险。

#### Scenario: Cookie 属性正确设置
- **WHEN** 系统写入凭证 Cookie
- **THEN** Cookie 设置 SameSite=Strict; Path=/; 不设置 HttpOnly（前端需 JS 读取）
