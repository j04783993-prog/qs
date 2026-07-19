# 安全修复报告

## 项目信息

- 项目名称：用户管理系统（Flask）
- 仓库地址：https://github.com/j04783993-prog/qs
- 修复时间：2026-07-19
- 修复人员：Jerry

---

## 一、发现的安全漏洞

| 序号 | 漏洞 | 风险等级 | 位置 |
|------|------|----------|------|
| 1 | 硬编码密钥 | 高 | `app.py` 第 4 行 |
| 2 | 明文存储密码 | 高 | `app.py` 用户字典 |
| 3 | 前端页面泄露密码 | 高 | `templates/index.html` |
| 4 | 页面注释泄露默认凭据 | 高 | `templates/login.html` |
| 5 | 使用弱口令/默认口令 | 高 | `app.py` 用户字典 |
| 6 | 缺乏暴力破解防护 | 高 | `app.py` `/login` 路由 |
| 7 | 登录成功后未重定向（可重复提交表单） | 中 | `app.py` `/login` 路由 |
| 8 | 缺乏 CSRF 防护 | 中 | `templates/login.html` |
| 9 | 会话固定风险 | 中 | `app.py` 登录逻辑 |
| 10 | Debug 模式默认开启 | 中 | `app.py` 启动参数 |
| 11 | 缺乏输入校验 | 低 | `app.py` `/login` 路由 |

---

## 二、修复措施

### 1. 硬编码密钥修复

**原问题**：`app.secret_key = "dev-key-2025"` 为固定字符串，攻击者可直接伪造会话 Cookie。

**修复**：改为优先从环境变量 `SECRET_KEY` 读取，未设置时生成随机 32 字节十六进制密钥：

```python
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
```

**建议**：生产环境务必设置强随机密钥，例如：

```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

---

### 2. 明文存储密码修复

**原问题**：用户密码以明文形式存储在内存字典中，一旦源码泄露所有账号都会沦陷。

**修复**：使用 `werkzeug.security.generate_password_hash` 对密码进行哈希存储，登录时使用 `check_password_hash` 校验：

```python
from werkzeug.security import generate_password_hash, check_password_hash

USERS = {
    "admin": {
        "password": generate_password_hash("ChangeMe!Admin2025#"),
        ...
    }
}

if user and check_password_hash(user["password"], password):
    ...
```

---

### 3. 前端页面不再泄露密码

**原问题**：`index.html` 直接展示 `user['password']`。

**修复**：渲染用户信息时过滤掉 `password` 字段：

```python
user_info = {k: v for k, v in USERS[username].items() if k != "password"}
```

---

### 4. 删除泄露凭据的页面注释

**原问题**：`login.html` 顶部注释包含默认管理员账号和密码。

**修复**：已删除该注释。

---

### 5. 使用强口令

**原问题**：默认账号使用 `admin123`、`alice2025` 等弱口令。

**修复**：将默认密码替换为包含大小写字母、数字和特殊符号的强口令：

- `admin` → `ChangeMe!Admin2025#`
- `alice` → `ChangeMe!Alice2025#`

**建议**：首次部署后立即修改默认密码。

---

### 6. 增加登录速率限制

**原问题**：攻击者可以无限制地尝试登录，配合弱口令字典极易成功。

**修复**：基于用户名 + 客户端 IP 实现内存级速率限制，15 分钟内最多允许 5 次失败尝试：

```python
_login_attempts = defaultdict(list)
_RATE_LIMIT_WINDOW = 900
_RATE_LIMIT_MAX_ATTEMPTS = 5
```

**建议**：生产环境使用 Redis 或数据库实现分布式速率限制。

---

### 7. 登录成功后重定向

**原问题**：登录成功后直接 `render_template("index.html")`，刷新页面会重复提交登录表单。

**修复**：登录成功后使用 `redirect(url_for("index"))` 进行 302 重定向。

---

### 8. 增加 CSRF 防护

**原问题**：登录表单没有 CSRF 令牌，可被跨站请求伪造攻击利用。

**修复**：

- 在 `app.py` 中实现 `_generate_csrf_token()` 和 `_validate_csrf_token()`。
- 在 `login.html` 表单中嵌入隐藏字段：

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

---

### 9. 修复会话固定风险

**原问题**：登录后未重新生成会话 Cookie，攻击者可能利用预置的会话 ID 劫持用户。

**修复**：登录成功后调用 `_regenerate_session()` 重新生成会话 Cookie：

```python
def _regenerate_session():
    data = dict(session)
    session.clear()
    session.update(data)
```

---

### 10. Debug 模式默认关闭

**原问题**：`app.run(debug=True)` 默认开启调试模式，会暴露 Werkzeug 交互式调试器，存在远程代码执行风险。

**修复**：默认关闭 Debug，可通过环境变量开启：

```python
debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
app.run(host="0.0.0.0", port=5000, debug=debug_mode)
```

---

### 11. 增加输入校验

**原问题**：登录接口未对用户名和密码做基本校验。

**修复**：登录时检查用户名和密码是否为空，并对用户名进行 `strip()` 处理。

---

## 三、brute.py 的改进

原 `brute.py` 是一个没有任何说明的暴力破解脚本，直接包含在项目中可能引发合规风险。已进行以下改进：

1. 在文件头部添加授权声明和用途说明。
2. 增加请求间隔（`time.sleep(1.0)`），降低对目标服务的压力。
3. 增加异常处理（`requests.RequestException`）。
4. 增加注释说明：当目标启用 CSRF 或速率限制时脚本将难以成功。

---

## 四、新增文件

- `requirements.txt`：列出项目依赖（Flask、Werkzeug、requests）。
- `SECURITY_REPORT.md`：本报告。

---

## 五、后续建议

1. **使用 HTTPS**：生产环境必须启用 TLS，防止凭据在传输过程中被窃取。
2. **使用数据库**：将用户信息持久化到数据库（如 SQLite/PostgreSQL），不要存放在源码中。
3. **更强的认证机制**：考虑集成 Flask-Login、Flask-WTF 或 OAuth2。
4. **日志审计**：记录登录失败和异常行为，便于安全审计。
5. **账户锁定**：对连续失败账号实施临时锁定或 CAPTCHA 验证。
6. **环境隔离**：生产环境使用 `.env` 文件或密钥管理服务（Vault、AWS Secrets Manager）管理密钥。

---

## 六、验证方式

修复后可以通过以下方式验证：

1. 查看 `index.html` 不再显示密码字段。
2. 使用旧密码 `admin123` 登录应失败。
3. 使用新强口令 `ChangeMe!Admin2025#` 登录应成功。
4. 连续 5 次输入错误密码后，第 6 次会触发速率限制。
5. 通过 Burp Suite 或浏览器开发者工具移除 `csrf_token` 后提交，应被拦截。
