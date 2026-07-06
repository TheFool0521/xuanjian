"""
农大玄鉴 · 后端服务
Flask + SQLite · 校车食堂浴室 + 留言板
"""
import os, sqlite3, uuid
from datetime import datetime
from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS

# ===== 配置 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'data.db')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, supports_credentials=True)

# ===== 数据库 =====
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL DEFAULT '匿名',
            content TEXT NOT NULL,
            date TEXT NOT NULL
        );
    """)
    db.commit()
    db.close()

init_db()

# ===== 工具函数 =====
def today():
    return datetime.now().strftime('%Y-%m-%d %H:%M')

def row_to_dict(row):
    return dict(row) if row else None

# ===== 留言板 API =====
@app.route('/api/messages', methods=['GET'])
def list_messages():
    db = get_db()
    rows = db.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 200").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/messages', methods=['POST'])
def create_message():
    data = request.get_json(force=True) or {}
    nickname = (data.get('nickname') or '').strip()[:20] or '匿名'
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': '留言内容不能为空'}), 400
    if len(content) > 2000:
        return jsonify({'error': '留言内容不能超过2000字'}), 400

    db = get_db()
    db.execute(
        "INSERT INTO messages (nickname, content, date) VALUES (?, ?, ?)",
        [nickname, content, today()]
    )
    db.commit()
    return jsonify({'ok': True, 'message': '留言成功'})

# ===== 图片访问 =====
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ===== 静态文件 =====
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
