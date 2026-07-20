import os
import secrets
import sqlite3
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

# SQLite 数据库路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "users.db")


def init_db():
    """初始化 SQLite 数据库，创建 users 表并插入默认用户。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    """)
    # 插入默认用户，使用 INSERT OR IGNORE 防止重复插入
    default_users = [
        ("admin", "ChangeMe!Admin2025#", "admin@example.com", "13800138000"),
        ("alice", "ChangeMe!Alice2025#", "alice@example.com", "13900139001"),
    ]
    for username, password, email, phone in default_users:
        # 注意：本演示项目为观察 SQL 注入效果，注册和搜索使用字符串拼接
        sql = f"INSERT OR IGNORE INTO users (username, password, email, phone) VALUES ('{username}', '{password}', '{email}', '{phone}')"
        print(f"[init_db] SQL: {sql}")
        cursor.execute(sql)
    conn.commit()
    conn.close()


def get_db_connection():
    """获取 SQLite 数据库连接。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
    return render_template(
        "index.html",
        username=username,
        user=user_info,
        keyword="",
        search_results=[]
    )


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


@app.route("/register", methods=["GET", "POST"])
def register():
    """用户注册，使用字符串拼接 SQL 以演示 SQL 注入效果。"""
    if request.method == "POST":
        # CSRF 校验
        if not _validate_csrf_token():
            flash("CSRF 令牌无效，请重新注册", "error")
            return redirect(url_for("register"))

        username = request.form.get("username", "")
        password = request.form.get("password", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")

        if not username or not password:
            flash("用户名和密码不能为空", "error")
            return redirect(url_for("register"))

        conn = get_db_connection()
        cursor = conn.cursor()
        # 警告：此处故意使用 f-string 字符串拼接，存在 SQL 注入风险，仅用于教学演示
        sql = f"INSERT INTO users (username, password, email, phone) VALUES ('{username}', '{password}', '{email}', '{phone}')"
        print(f"[register] SQL: {sql}")
        try:
            cursor.execute(sql)
            conn.commit()
            flash("注册成功，请登录", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("用户名已存在", "error")
            return redirect(url_for("register"))
        except sqlite3.Error as e:
            flash(f"注册失败：{e}", "error")
            return redirect(url_for("register"))
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/search")
def search():
    """用户搜索，使用字符串拼接 SQL 以演示 SQL 注入效果。"""
    keyword = request.args.get("keyword", "")
    results = []
    if keyword:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 警告：此处故意使用 f-string 字符串拼接，存在 SQL 注入风险，仅用于教学演示
        sql = f"SELECT * FROM users WHERE username LIKE '%{keyword}%' OR email LIKE '%{keyword}%'"
        print(f"[search] SQL: {sql}")
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            results = [
                {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "phone": row["phone"],
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            flash(f"搜索失败：{e}", "error")
        finally:
            conn.close()

    username = session.get("username")
    user_info = None
    if username and username in USERS:
        user_info = {k: v for k, v in USERS[username].items() if k != "password"}

    return render_template(
        "index.html",
        username=username,
        user=user_info,
        keyword=keyword,
        search_results=results
    )


if __name__ == "__main__":
    init_db()
    # Debug 模式默认关闭，可通过环境变量 FLASK_DEBUG=true 开启
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
