"""
农大玄鉴 · 后端服务
Flask + SQLite · 投稿 / 预约 / 入驻 / 管理员审核
兼容 Railway / Render / 本地运行
"""
import os, sys, hashlib, time, sqlite3, uuid, functools, logging
from datetime import datetime
from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== 配置 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'data.db')

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'xuanjian2026')
ADMIN_PW_HASH = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
JWT_SECRET = os.environ.get('JWT_SECRET', 'xuanjian-cau-platform-secret-key-2026!')
PORT = int(os.environ.get('PORT', 5000))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, supports_credentials=True)

_db_initialized = False

def get_db():
    global _db_initialized
    if 'db' not in g:
        try:
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA journal_mode=WAL")
            if not _db_initialized:
                _init_tables(g.db)
                _db_initialized = True
        except Exception as e:
            logger.error(f"DB connect failed: {e}")
            raise
    return g.db

def _init_tables(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT DEFAULT '',
            author TEXT DEFAULT '匿名',
            photo TEXT,
            date TEXT NOT NULL,
            views INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending'
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_type TEXT NOT NULL,
            name TEXT NOT NULL,
            wechat TEXT NOT NULL,
            note TEXT DEFAULT '',
            date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS join_apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            wechat TEXT NOT NULL,
            school TEXT DEFAULT '中国农业大学',
            service_type TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            date TEXT NOT NULL
        );
    """)
    db.commit()
    logger.info("Database tables initialized")

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db: db.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file):
    ext = file.filename.rsplit('.', 1)[1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, name)
    file.save(path)
    return name

def today():
    return datetime.now().strftime('%Y-%m-%d')

def admin_required(f):
    @functools.wraps(f)
    def wrapper(*a, **kw):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': '未授权'}), 401
        try:
            import jwt
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            if not data.get('admin'): raise Exception()
        except Exception as e:
            return jsonify({'error': '未授权或登录已过期'}), 401
        return f(*a, **kw)
    return wrapper

# ===== 文章 API =====
@app.route('/api/articles', methods=['GET'])
def list_articles():
    cat = request.args.get('category', '')
    try:
        db = get_db()
        if cat:
            rows = db.execute("SELECT * FROM articles WHERE status='published' AND category=? ORDER BY id DESC", [cat]).fetchall()
        else:
            rows = db.execute("SELECT * FROM articles WHERE status='published' ORDER BY id DESC").fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        logger.error(f"list_articles error: {e}")
        return jsonify([])

@app.route('/api/articles/<int:aid>', methods=['GET'])
def get_article(aid):
    try:
        db = get_db()
        db.execute("UPDATE articles SET views = views + 1 WHERE id=?", [aid])
        db.commit()
        row = db.execute("SELECT * FROM articles WHERE id=? AND status='published'", [aid]).fetchone()
        if not row: return jsonify({'error': '文章不存在'}), 404
        return jsonify(dict(row))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/articles', methods=['POST'])
def create_article():
    cat = request.form.get('category', '')
    title = request.form.get('title', '')
    content = request.form.get('content', '')
    author = request.form.get('author', '匿名')
    if not title or not content:
        return jsonify({'error': '标题和正文不能为空'}), 400
    photo_name = None
    photo_file = request.files.get('photo')
    if photo_file and photo_file.filename and allowed_file(photo_file.filename):
        photo_name = save_upload(photo_file)
    summary = content[:80] + ('...' if len(content) > 80 else '')
    try:
        db = get_db()
        db.execute(
            "INSERT INTO articles (category,title,content,summary,author,photo,date,status) VALUES (?,?,?,?,?,?,?,?)",
            [cat, title, content, summary, author, photo_name, today(), 'pending']
        )
        db.commit()
        return jsonify({'ok': True, 'message': '投稿成功，等待管理员审核'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== 管理员 API =====
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(force=True, silent=True) or {}
    pw = data.get('password', '')
    if hashlib.sha256(pw.encode()).hexdigest() == ADMIN_PW_HASH:
        import jwt
        token = jwt.encode({'admin': True, 'exp': int(time.time()) + 86400}, JWT_SECRET, algorithm='HS256')
        return jsonify({'ok': True, 'token': token})
    return jsonify({'error': '密码错误'}), 403

@app.route('/api/admin/pending', methods=['GET'])
@admin_required
def list_pending():
    db = get_db()
    rows = db.execute("SELECT * FROM articles WHERE status='pending' ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/approve/<int:aid>', methods=['POST'])
@admin_required
def approve_article(aid):
    db = get_db()
    db.execute("UPDATE articles SET status='published', date=? WHERE id=?", [today(), aid])
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/reject/<int:aid>', methods=['DELETE'])
@admin_required
def reject_article(aid):
    db = get_db()
    row = db.execute("SELECT photo FROM articles WHERE id=?", [aid]).fetchone()
    if row and row['photo']:
        pp = os.path.join(UPLOAD_DIR, row['photo'])
        if os.path.exists(pp): os.remove(pp)
    db.execute("DELETE FROM articles WHERE id=?", [aid])
    db.commit()
    return jsonify({'ok': True})

# ===== 预约 API =====
@app.route('/api/bookings', methods=['POST'])
def create_booking():
    data = request.get_json(force=True, silent=True) or {}
    stype = data.get('service_type', '')
    name = data.get('name', '')
    wechat = data.get('wechat', '')
    note = data.get('note', '')
    if not name or not wechat:
        return jsonify({'error': '请填写姓名和微信号'}), 400
    try:
        db = get_db()
        db.execute("INSERT INTO bookings (service_type,name,wechat,note,date) VALUES (?,?,?,?,?)", [stype, name, wechat, note, today()])
        db.commit()
        return jsonify({'ok': True, 'message': '预约成功！客服将通过微信联系你确认详情。'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== 入驻 API =====
@app.route('/api/join', methods=['POST'])
def create_join():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get('name', '')
    wechat = data.get('wechat', '')
    school = data.get('school', '中国农业大学')
    stype = data.get('service_type', '')
    bio = data.get('bio', '')
    if not name or not wechat or not bio:
        return jsonify({'error': '请填写必填项'}), 400
    try:
        db = get_db()
        db.execute("INSERT INTO join_apps (name,wechat,school,service_type,bio,date) VALUES (?,?,?,?,?,?)", [name, wechat, school, stype, bio, today()])
        db.commit()
        return jsonify({'ok': True, 'message': '申请成功！3个工作日内审核。'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== 图片访问 =====
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ===== 健康检查 =====
@app.route('/health')
def health():
    try:
        db = get_db()
        db.execute('SELECT 1')
        return jsonify({'status': 'ok', 'db': 'connected'})
    except Exception as e:
        return jsonify({'status': 'ok', 'db': f'error: {e}'}), 200

# ===== 首页 =====
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

# ===== 启动 =====
if __name__ == '__main__':
    logger.info(f"Starting server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
