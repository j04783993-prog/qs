# 修改报告（2026-07-21）

## 项目信息

- 项目名称：用户管理系统（Flask）
- 仓库地址：https://github.com/j04783993-prog/qs
- 修改日期：2026-07-21
- 修改人员：Jerry

---

## 一、新增功能：用户头像上传

### 1. 在 `app.py` 中新增上传配置

```python
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
```

- 限制上传文件最大 16MB
- 定义允许的文件扩展名白名单

### 2. 新增路由 `/upload`（GET / POST）

- 需要登录才能访问，未登录跳转到登录页
- GET 请求显示上传页面
- POST 请求接收文件，经过以下安全处理后保存：
  1. **CSRF 校验**：验证表单中的 CSRF 令牌
  2. **文件类型检查**：使用白名单机制，仅允许 `png/jpg/jpeg/gif/bmp/webp` 格式
  3. **文件名安全处理**：
     - 使用 `werkzeug.utils.secure_filename` 清理文件名，移除路径分隔符和特殊字符
     - 使用 `uuid.uuid4().hex` 生成随机文件名，防止文件名冲突和覆盖
  4. 保存到 `static/uploads/` 目录
- 上传成功后返回文件访问 URL 并显示图片预览

### 3. 新增模板 `templates/upload.html`

- 继承 `base.html`
- 包含文件选择输入框（`accept` 限制图片格式）和上传按钮
- 表单带 CSRF 隐藏字段和 `enctype="multipart/form-data"`
- 上传成功后显示文件名、图片预览和文件链接

### 4. 修改模板 `templates/base.html`

- 登录后导航栏新增「上传头像」链接

### 5. 修改模板 `templates/index.html`

- 已登录欢迎页面新增「上传头像」快捷按钮

### 6. 新增目录 `static/uploads/`

- 创建 `static/uploads/` 目录存放上传文件
- 添加 `.gitkeep` 保留目录结构

### 7. 修改样式 `static/css/style.css`

- 新增上传成功区域、图片预览等样式

---

## 二、安全修复：文件上传漏洞

原始实现存在以下安全问题，本次已全部修复：

### 问题 1：无文件类型检查

**风险**：攻击者可上传任意文件（如 `.py`、`.sh`、`.html`），可能导致远程代码执行。

**修复**：新增 `_allowed_file()` 函数，使用白名单机制仅允许图片格式：

```python
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}

def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
```

### 问题 2：使用原始文件名保存

**风险**：文件名可能包含路径分隔符（如 `../../etc/passwd`），导致目录遍历攻击；同名文件会被覆盖。

**修复**：使用 `secure_filename` 清理文件名 + UUID 重命名：

```python
original_name = secure_filename(file.filename)
ext = original_name.rsplit(".", 1)[1].lower()
safe_name = f"{uuid.uuid4().hex}.{ext}"
```

### 问题 3：前端未限制文件类型

**修复**：在 `upload.html` 的 `<input>` 中添加 `accept` 属性：

```html
<input type="file" accept=".png,.jpg,.jpeg,.gif,.bmp,.webp" required>
```

---

## 三、安全修复：SQL 注入漏洞（2026-07-20 遗留）

在 2026-07-20 的代码中，注册和搜索功能的 SQL 语句使用了 f-string 字符串拼接，存在 SQL 注入风险。本次一并修复。

### 修复位置

| 路由 | 修复前 | 修复后 |
|------|--------|--------|
| `init_db()` | `f"INSERT OR IGNORE INTO... VALUES ('{username}', ...)"` | `"... VALUES (?, ?, ?, ?)"` + 参数化 |
| `/register` | `f"INSERT INTO... VALUES ('{username}', ...)"` | `"... VALUES (?, ?, ?, ?)"` + 参数化 |
| `/search` | `f"SELECT * FROM... LIKE '%{keyword}%'"` | `"... LIKE ?"` + `f"%{keyword}%"` + 参数化 |

### 修复示例

```python
# 修复前（SQL注入漏洞）
sql = f"INSERT INTO users (username, password, email, phone) VALUES ('{username}', '{password}', '{email}', '{phone}')"
cursor.execute(sql)

# 修复后（参数化查询）
sql = "INSERT INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)"
cursor.execute(sql, (username, password, email, phone))
```

---

## 四、配置更新：`.gitignore`

| 规则 | 说明 |
|------|------|
| `static/uploads/*` | 忽略所有上传的文件 |
| `!static/uploads/.gitkeep` | 保留目录结构文件 |
| `brute.py` | 忽略暴力破解测试脚本，保留在本地不上传 |

---

## 五、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app.py` | 修改 | 新增上传路由、文件类型检查、UUID重命名；修复 SQL 注入 |
| `templates/upload.html` | 新增 | 上传页面 |
| `templates/base.html` | 修改 | 导航栏新增「上传头像」链接 |
| `templates/index.html` | 修改 | 首页新增「上传头像」按钮 |
| `static/css/style.css` | 修改 | 新增上传相关样式 |
| `static/uploads/.gitkeep` | 新增 | 保留目录结构 |
| `.gitignore` | 修改 | 忽略上传文件和 brute.py |
| `CHANGELOG_20260721.md` | 新增 | 本报告 |

---

## 六、验证方式

### 启动应用

```bash
cd /opt/Class01
python3 app.py
```

### 测试上传功能

1. 访问 `http://127.0.0.1:5000`
2. 登录（admin / `ChangeMe!Admin2025#`）
3. 点击「上传头像」
4. 上传一张图片，确认显示预览

### 测试文件类型限制

- 尝试上传 `.py` 或 `.txt` 文件，应提示「不支持的文件类型」

### 测试 SQL 注入修复

在搜索框中输入以下 Payload：

```text
%' OR '1'='1
```

应返回「无搜索结果」或精确匹配，而非返回全部用户。

---

## 七、后续建议

1. **MIME 类型校验**：除了检查扩展名，还应读取文件头验证真实类型
2. **缩略图生成**：上传后自动生成不同尺寸的头像
3. **头像与用户关联**：在数据库中记录用户的头像路径
4. **存储空间管理**：定期清理未使用的上传文件
5. **云存储集成**：生产环境使用对象存储服务替代本地存储
