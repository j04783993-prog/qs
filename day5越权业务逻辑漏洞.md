# 修改报告（2026-07-22）

## 项目信息

- 项目名称：用户管理系统（Flask）
- 仓库地址：https://github.com/j04783993-prog/qs
- 修改日期：2026-07-22
- 修改人员：Jerry

---

## 一、新增功能：个人中心与充值

### 1. 数据库迁移：新增 `balance` 字段

- 在 `init_db()` 中新增迁移逻辑，为 `users` 表添加 `balance` 字段（`REAL` 类型，默认值 0）
- 使用 `ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0`，字段已存在时跳过
- 更新默认用户的初始余额：admin=99999，alice=100

### 2. 登录时存储 user_id

- 登录成功后从数据库查询 `user_id` 并存入 `session["user_id"]`
- 用于后续 `/profile` 和 `/recharge` 路由的权限校验

### 3. 新增路由 `/profile`（GET）

- 显示当前登录用户的个人资料（ID、用户名、邮箱、手机、余额）
- 包含充值表单
- 新增 `templates/profile.html` 模板

### 4. 新增路由 `/recharge`（POST）

- 接收 `user_id` 和 `amount` 参数
- 将 `amount` 加到用户的 `balance` 字段
- 充值成功后重定向到 `/profile`

### 5. 修改模板

- `base.html`：导航栏新增「个人中心」链接
- `index.html`：首页新增「个人中心」快捷按钮

---

## 二、安全审查与漏洞修复

### 审查发现的漏洞

| 漏洞 | 风险等级 | 类型 |
|------|---------|------|
| 任意用户资料查看 | 高 | 越权访问（IDOR） |
| 任意用户余额篡改 | 高 | 越权操作（IDOR） |
| 负数充值扣款 | 高 | 业务逻辑漏洞 |
| 未登录可访问 | 中 | 认证缺失 |
| 用户 ID 可枚举 | 低 | 信息泄露 |

---

### 修复 1：越权访问 — 任意用户资料查看

**问题：** `/profile` 路由的 `user_id` 从 URL 参数获取，不验证当前用户是否有权查看，任何用户可遍历 ID 查看他人资料。

**修复：** 添加登录检查和权限校验，仅允许查看自己的资料：

```python
# 检查登录状态
if "user_id" not in session:
    flash("请先登录", "error")
    return redirect(url_for("login"))

# 权限检查：只能查看自己的资料
if int(user_id) != session["user_id"]:
    flash("无权查看其他用户的资料", "error")
    return redirect(url_for("profile", user_id=session["user_id"]))
```

---

### 修复 2：越权操作 — 任意用户余额篡改

**问题：** `/recharge` 路由的 `user_id` 从表单隐藏字段获取，攻击者可修改 `user_id` 给任意账户充值或扣款。

**修复：** 添加登录检查和权限校验，仅允许给自己充值：

```python
# 检查登录状态
if "user_id" not in session:
    flash("请先登录", "error")
    return redirect(url_for("login"))

# 权限检查：只能给自己充值
if int(user_id) != session["user_id"]:
    flash("无权操作其他用户的账户", "error")
    return redirect(url_for("profile", user_id=session["user_id"]))
```

---

### 修复 3：负数充值 — 任意扣款

**问题：** `amount` 参数不检查正负，攻击者可提交负数金额（如 `-99999`）将余额清零或扣为负数。

**修复：** 添加业务逻辑检查，充值金额必须为正数：

```python
# 业务逻辑检查：充值金额必须为正数
if amount <= 0:
    flash("充值金额必须为正数", "error")
    return redirect(url_for("profile", user_id=session["user_id"]))
```

---

### 修复 4：未登录可访问

**问题：** `/profile` 和 `/recharge` 路由都未检查用户是否登录。

**修复：** 在两个路由开头都添加了登录状态检查：

```python
if "user_id" not in session:
    flash("请先登录", "error")
    return redirect(url_for("login"))
```

---

### 漏洞 5：用户 ID 可枚举（未修复）

**说明：** `user_id` 使用自增整数，理论上可被遍历枚举。但由于已修复漏洞 1 和 2（权限校验），用户只能查看和操作自己的资料，枚举其他用户 ID 不再有意义。此漏洞风险已降至可接受水平。

---

## 三、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app.py` | 修改 | 新增 /profile、/recharge 路由；数据库迁移添加 balance 字段；登录时存储 user_id；修复越权和业务逻辑漏洞 |
| `templates/profile.html` | 新增 | 个人中心页面（用户信息 + 充值表单） |
| `templates/base.html` | 修改 | 导航栏新增「个人中心」链接 |
| `templates/index.html` | 修改 | 首页新增「个人中心」按钮 |
| `CHANGELOG_20260722.md` | 新增 | 本报告 |

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
3. 点击「个人中心」，确认显示自己的资料
4. 输入金额充值，确认余额更新

### 测试越权防护

1. 登录 alice 账号
2. 尝试访问 `/profile?user_id=1`（admin 的资料）
3. 应提示「无权查看其他用户的资料」并重定向到自己的资料页

4. 使用浏览器开发者工具修改充值表单的 `user_id` 为 1
5. 提交充值，应提示「无权操作其他用户的账户」

### 测试负数金额防护

1. 在充值表单中输入 `-100`
2. 应提示「充值金额必须为正数」

---

## 五、后续建议

1. **支付系统集成**：实际项目中应接入第三方支付，而非直接修改数据库余额
2. **操作日志**：记录充值操作的详细日志，便于审计和对账
3. **金额精度**：使用 `Decimal` 类型而非 `float`，避免浮点数精度问题
4. **并发控制**：使用数据库事务或乐观锁，防止并发充值导致余额计算错误
