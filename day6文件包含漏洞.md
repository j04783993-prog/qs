# 修改报告（2026-07-23）

## 项目信息

- 项目名称：用户管理系统（Flask）
- 仓库地址：https://github.com/j04783993-prog/qs
- 修改日期：2026-07-23
- 修改人员：Jerry

---

## 一、新增功能：动态页面加载

### 1. 在 `app.py` 中新增路由 `/page`（GET）

- 从 URL 参数 `name` 获取页面名称
- 使用拼接字符串的方式构建文件路径
- 如果文件存在则读取内容并显示在首页上
- 如果文件不存在，尝试加上 `.html` 后缀再找一次
- 如果仍然找不到则显示"页面不存在"

### 2. 新建 `pages/` 目录

- 创建 `pages/help.html` 文件（帮助中心页面）

### 3. 修改 `templates/index.html`

- 在首页中添加 `page_content` 显示区域
- 如果 `page_content` 变量存在则显示页面内容
- 添加"帮助中心"入口链接：`/page?name=help`

---

## 二、安全审查与漏洞修复

### 审查发现的漏洞

| 漏洞 | 风险等级 | 类型 |
|------|---------|------|
| 路径遍历攻击 | 高 | 任意文件读取 |
| 未登录可访问 | 中 | 认证缺失 |

---

### 修复 1：路径遍历攻击

**问题：** `name` 参数直接拼接到文件路径中，攻击者可通过 `../` 读取服务器上的任意文件：

```
# 攻击示例
/page?name=../../../etc/passwd
/page?name=../../app.py
```

这会导致服务器敏感信息泄露，包括配置文件、源代码、系统密码等。

**修复：** 多层防护，彻底阻止路径遍历：

```python
# 1. 移除路径分隔符
name = name.replace("/", "").replace("\\", "")
# 2. 移除 .. 防止目录遍历
name = name.replace("..", "")

# 3. 使用 realpath 规范化路径，确保在 pages 目录内
real_pages_dir = os.path.realpath(pages_dir)
real_file_path = os.path.realpath(file_path)
if not real_file_path.startswith(real_pages_dir + os.sep):
    flash("无效的页面路径", "error")
    return redirect(url_for("index"))
```

修复后，即使攻击者尝试使用 `../` 或编码绕过，也会被拦截。

---

### 修复 2：未登录可访问

**问题：** `/page` 路由未检查用户是否登录，匿名用户也能访问动态页面。

**修复：** 在路由开头添加登录状态检查：

```python
if "username" not in session:
    flash("请先登录", "error")
    return redirect(url_for("login"))
```

---

## 三、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app.py` | 修改 | 新增 `/page` 路由，添加路径遍历防护和登录检查 |
| `pages/help.html` | 新增 | 帮助中心页面 |
| `templates/index.html` | 修改 | 添加 page_content 显示区域和帮助中心入口 |
| `day6动态页面加载漏洞.md` | 新增 | 本报告 |

---

## 四、验证方式

### 启动应用

```bash
cd /opt/Class01
python3 app.py
```

### 测试正常流程

1. 访问 `http://127.0.0.1:5000`
2. 登录（admin / `ChangeMe!Admin2025#`）
3. 点击「帮助中心」按钮
4. 确认显示帮助页面内容

### 测试路径遍历防护

登录后尝试以下 URL，应提示"无效的页面路径"或"页面不存在"：

```
/page?name=../../../etc/passwd
/page?name=../../app.py
/page?name=..%2F..%2Fetc%2Fpasswd
```

### 测试未登录访问

未登录状态下直接访问 `/page?name=help`，应跳转到登录页面。

---

## 五、后续建议

1. **文件白名单**：仅允许加载预定义的页面文件，而非任意文件
2. **内容类型限制**：只允许加载 `.html` 文件
3. **日志记录**：记录所有页面加载请求，便于安全审计
4. **缓存控制**：动态加载的内容应设置适当的缓存策略
