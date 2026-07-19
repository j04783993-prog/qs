import os
import secrets
import time
from collections import defaultdict
from datetime import timedelta

from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# 使用环境变量读取 SECRET_KEY；若未设置则在开发环境生成随机密钥
# 生产环境务必设置环境变量：export SECRET_KEY="your-random-secret-key"
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(minutes=30)

# 简易内存级登录速率限制（生产环境建议使用 Redis 或数据库实现）
_login_attempts = defaultdict(list)
_RATE_LIMIT_WINDOW = 900        # 15 分钟
_RATE_LIMIT_MAX_ATTEMPTS = 5    # 窗口期内最大尝试次数


def _get_client_identifier(username):
    """基于用户名和客户端 IP 生成限流标识。"""
    remote_addr = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    return f"{username}:{remote_addr}"


def _is_rate_limited(identifier):
    """检查指定标识是否已触发速率限制。"""
    now = time.time()
    attempts = _login_attempts.get(identifier, [])
    attempts = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    _login_attempts[identifier] = attempts
    return len(attempts) >= _RATE_LIMIT_MAX_ATTEMPTS


def _record_attempt(identifier):
    """记录一次失败的登录尝试。"""
    _login_attempts.setdefault(identifier, []).append(time.time())


def _regenerate_session():
    """重新生成会话 Cookie，防止会话固定攻击。"""
    data = dict(session)
    session.clear()
    session.update(data)


def _generate_csrf_token():
    """生成并返回 CSRF 令牌。"""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def _validate_csrf_token():
    """校验 POST 请求中的 CSRF 令牌。"""
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if not token or token != session.get("csrf_token"):
            return False
    return True


# 让模板可以直接调用 csrf_token()
app.jinja_env.globals["csrf_token"] = _generate_csrf_token

# 用户数据库：密码使用 Werkzeug 进行哈希存储
USERS = {
    "admin": {
        "password": generate_password_hash("ChangeMe!Admin2025#"),
        "role": "admin",
        "email": "admin@example.com",
        "phone": "13800138000",
        "balance": 99999
    },
    "alice": {
        "password": generate_password_hash("ChangeMe!Alice2025#"),
        "role": "user",
        "email": "alice@example.com",
        "phone": "13900139001",
        "balance": 100
    }
}


@app.route("/")
def index():
    username = session.get("username")
    user_info = None
    if username and username in USERS:
        # 永远不要将密码哈希暴露给前端页面
        user_info = {k: v for k, v in USERS[username].items() if k != "password"}
    return render_template("index.html", username=username, user=user_info)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # 1. CSRF 校验
        if not _validate_csrf_token():
            flash("CSRF 令牌无效，请重新登录", "error")
            return redirect(url_for("login"))

        # 2. 获取并清理输入
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("用户名和密码不能为空", "error")
            return redirect(url_for("login"))

        # 3. 速率限制检查
        identifier = _get_client_identifier(username)
        if _is_rate_limited(identifier):
            flash("登录尝试次数过多，请 15 分钟后再试", "error")
            return redirect(url_for("login"))

        # 4. 验证凭据
        user = USERS.get(username)
        if user and check_password_hash(user["password"], password):
            _regenerate_session()
            session.permanent = True
            session["username"] = username
            flash("登录成功", "success")
            return redirect(url_for("index"))
        else:
            _record_attempt(identifier)
            flash("用户名或密码错误", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Debug 模式默认关闭，可通过环境变量 FLASK_DEBUG=true 开启
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
