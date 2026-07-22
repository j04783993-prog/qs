import os
import secrets
import sqlite3
import time
from collections import defaultdict
from datetime import timedelta

import uuid

from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
# 使用环境变量读取 SECRET_KEY；若未设置则在开发环境生成随机密钥
# 生产环境务必设置环境变量：export SECRET_KEY="your-random-secret-key"
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(minutes=30)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

# 上传文件白名单（仅允许图片格式）
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}

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
    # 迁移：为已有表添加 balance 字段（如不存在）
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 字段已存在
    # 插入默认用户，使用 INSERT OR IGNORE 防止重复插入
    default_users = [
        ("admin", "ChangeMe!Admin2025#", "admin@example.com", "13800138000", 99999),
        ("alice", "ChangeMe!Alice2025#", "alice@example.com", "13900139001", 100),
    ]
    for username, password, email, phone, balance in default_users:
        sql = "INSERT OR IGNORE INTO users (username, password, email, phone, balance) VALUES (?, ?, ?, ?, ?)"
        print(f"[init_db] SQL: {sql} params: ({username}, ***, {email}, {phone}, {balance})")
        cursor.execute(sql, (username, password, email, phone, balance))
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
            # 从数据库获取 user_id 存入 session
            conn = get_db_connection()
            db_user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            conn.close()
            if db_user:
                session["user_id"] = db_user["id"]
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
    """用户注册。"""
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
        sql = "INSERT INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)"
        print(f"[register] SQL: {sql} params: ({username}, ***, {email}, {phone})")
        try:
            cursor.execute(sql, (username, password, email, phone))
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
    """用户搜索。"""
    keyword = request.args.get("keyword", "")
    results = []
    if keyword:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM users WHERE username LIKE ? OR email LIKE ?"
        like_keyword = f"%{keyword}%"
        print(f"[search] SQL: {sql} params: ({like_keyword}, {like_keyword})")
        try:
            cursor.execute(sql, (like_keyword, like_keyword))
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


def _allowed_file(filename):
    """检查文件扩展名是否在白名单内。"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/upload", methods=["GET", "POST"])
def upload():
    """用户头像上传，需要登录才能访问。"""
    if "username" not in session:
        flash("请先登录", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        # CSRF 校验
        if not _validate_csrf_token():
            flash("CSRF 令牌无效，请重新上传", "error")
            return redirect(url_for("upload"))

        file = request.files.get("avatar")
        if not file or file.filename == "":
            flash("请选择要上传的文件", "error")
            return redirect(url_for("upload"))

        # 安全处理：检查文件类型
        if not _allowed_file(file.filename):
            flash("不支持的文件类型，仅允许 png/jpg/jpeg/gif/bmp/webp", "error")
            return redirect(url_for("upload"))

        # 安全处理：使用 secure_filename 清理文件名，再用 UUID 避免重名覆盖
        original_name = secure_filename(file.filename)
        ext = original_name.rsplit(".", 1)[1].lower()
        safe_name = f"{uuid.uuid4().hex}.{ext}"

        upload_dir = os.path.join(BASE_DIR, "static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, safe_name)
        file.save(save_path)
        flash("上传成功", "success")
        file_url = url_for("static", filename=f"uploads/{safe_name}")
        return render_template("upload.html", file_url=file_url, filename=original_name)

    return render_template("upload.html")


@app.route("/profile")
def profile():
    """个人中心，仅查看自己的资料。"""
    # 检查登录状态
    if "user_id" not in session:
        flash("请先登录", "error")
        return redirect(url_for("login"))

    user_id = request.args.get("user_id")
    if not user_id:
        # 未指定时默认查看自己的资料
        user_id = session["user_id"]

    # 权限检查：只能查看自己的资料
    if int(user_id) != session["user_id"]:
        flash("无权查看其他用户的资料", "error")
        return redirect(url_for("profile", user_id=session["user_id"]))

    conn = get_db_connection()
    user = conn.execute("SELECT id, username, email, phone, balance FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if not user:
        flash("用户不存在", "error")
        return redirect(url_for("index"))

    return render_template("profile.html", user=user)


@app.route("/recharge", methods=["POST"])
def recharge():
    """充值，仅允许给自己充值。"""
    # 检查登录状态
    if "user_id" not in session:
        flash("请先登录", "error")
        return redirect(url_for("login"))

    user_id = request.form.get("user_id")
    amount = request.form.get("amount")

    if not user_id or not amount:
        flash("缺少参数", "error")
        return redirect(url_for("index"))

    # 权限检查：只能给自己充值
    if int(user_id) != session["user_id"]:
        flash("无权操作其他用户的账户", "error")
        return redirect(url_for("profile", user_id=session["user_id"]))

    amount = float(amount)

    # 业务逻辑检查：充值金额必须为正数
    if amount <= 0:
        flash("充值金额必须为正数", "error")
        return redirect(url_for("profile", user_id=session["user_id"]))

    conn = get_db_connection()
    conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()

    flash("充值成功", "success")
    return redirect(url_for("profile", user_id=user_id))


if __name__ == "__main__":
    init_db()
    # Debug 模式默认关闭，可通过环境变量 FLASK_DEBUG=true 开启
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
