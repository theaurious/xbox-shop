#!/usr/bin/env python3
"""
╔══════════════════════════════════════════╗
║        JCN XBOX CODES SHOP               ║
║   Professional Digital Code Shop         ║
╚══════════════════════════════════════════╝
Requirements:  pip install flask
Run:           python shop.py
URL:           http://localhost:5000
Owner login:   owner / admin@123
Admin passkey: admin@123
"""
import os, re, json, uuid, sqlite3, hashlib, shutil, threading, time
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
from flask import Flask, request, jsonify, session, render_template_string

# ═══════════════════════════════════════════════════════════════
#  CONFIG & VERCEL COMPATIBILITY
# ═══════════════════════════════════════════════════════════════
ADMIN_PASSKEY = 'admin@123'
SECRET_KEY    = 'jcn-shop-2024-secret-!xyz789'

# Vercel's filesystem is read-only except for /tmp
IS_VERCEL = os.environ.get('VERCEL') == '1'
DB_PATH    = '/tmp/jcn_shop.db' if IS_VERCEL else 'jcn_shop.db'
BACKUP_DIR = '/tmp/backups' if IS_VERCEL else 'backups'

try:
    os.makedirs(BACKUP_DIR, exist_ok=True)
except Exception as e:
    print(f"⚠ Could not create backup dir: {e}")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ═══════════════════════════════════════════════════════════════
#  GAME DETECTION
# ═══════════════════════════════════════════════════════════════
GAMES = {
    'fortnite':    ('Fortnite','🎯','Battle Royale by Epic Games. Fight to be the last player standing.','1. Open Fortnite on your device\n2. Go to the Item Shop\n3. Click "Enter Code" or "Redeem"\n4. Enter your 25-character code\n5. Confirm and enjoy!','V-Bucks or exclusive in-game content (skins, emotes, etc.)'),
    'vbucks':      ('Fortnite V-Bucks','💎','Fortnite in-game currency used to purchase skins, emotes, and Battle Pass.','1. Launch Fortnite\n2. Go to V-Bucks Store\n3. Select "Redeem Code"\n4. Enter your 25-character code','V-Bucks currency for Fortnite in-game purchases'),
    'minecraft':   ('Minecraft','⛏️','The iconic sandbox survival game by Mojang/Microsoft.','1. Visit xbox.com/redeemcode\n2. Sign in to your Microsoft account\n3. Enter your 25-character code\n4. Minecraft added to your library','Full Minecraft game for Xbox / Windows'),
    'roblox':      ('Roblox','🧱','Online game creation platform with millions of user-generated games.','1. Visit roblox.com/redeem\n2. Log into your Roblox account\n3. Enter your code\n4. Click Redeem','Robux currency or Roblox Premium subscription'),
    'robux':       ('Roblox Robux','💰','Roblox in-game currency for avatar items and game passes.','1. Visit roblox.com/redeem\n2. Log in and enter code','Robux for the Roblox platform'),
    'gamepass':    ('Xbox Game Pass Ultimate','🎮','Access to 100+ high-quality games on Xbox and PC.','1. On Xbox: Settings → Account → Redeem Code\n2. OR visit xbox.com/redeemcode\n3. Sign in and enter code','1–3 months of Xbox Game Pass Ultimate'),
    'game pass':   ('Xbox Game Pass Ultimate','🎮','Access to 100+ games subscription for Xbox and PC.','1. Xbox console: Settings → Account → Redeem Code\n2. OR xbox.com/redeemcode\n3. Enter 25-character code','Xbox Game Pass Ultimate subscription'),
    'xboxlive':    ('Xbox Live Gold','⭐','Online multiplayer access and free monthly Games with Gold.','1. Press Xbox button → Profile & System → Settings\n2. Account → Redeem Code\n3. Enter 25-character code','1–12 months of Xbox Live Gold'),
    'xbox live':   ('Xbox Live Gold','⭐','Xbox Live Gold for online multiplayer and monthly free games.','1. Xbox console → Settings → Account → Redeem Code\n2. Enter code','Xbox Live Gold subscription'),
    'cod':         ('Call of Duty','🔫','The iconic first-person shooter franchise by Activision.','1. Launch Call of Duty\n2. Go to Store\n3. Select Redeem Code\n4. Enter code','COD Points or in-game content'),
    'callofduty':  ('Call of Duty','🔫','Award-winning FPS franchise by Activision.','1. COD → Store → Redeem Code\n2. Enter code','COD Points or game content'),
    'warzone':     ('Call of Duty: Warzone','💣','Free-to-play Battle Royale in the COD universe.','1. Launch Warzone → Store → Redeem\n2. Enter code','COD Points or Warzone exclusive content'),
    'fifa':        ('EA Sports FC / FIFA','⚽',"The world's most popular football simulation by EA Sports.",'1. Launch EA FC/FIFA\n2. FUT → Store → Redeem Code\n3. Enter code','FIFA Points for Ultimate Team'),
    'ea sports':   ('EA Sports FC','⚽','EA Sports football simulation game.','1. Launch game → FUT → Redeem Code\n2. Enter code','FIFA/FC Points for Ultimate Team'),
    'ea':          ('EA Play','🎯',"EA's game subscription with access to EA's full library.",'1. Visit xbox.com/redeemcode\n2. Enter 25-character code','EA Play subscription (1–3 months)'),
    'apex':        ('Apex Legends','🦾','Free-to-play Battle Royale by Respawn Entertainment.','1. Launch Apex Legends\n2. Go to Store → Redeem Code\n3. Enter code','Apex Coins or exclusive Apex Legends content'),
    'halo':        ('Halo Infinite','🪖','The legendary sci-fi FPS by 343 Industries on Xbox.','1. Launch Halo Infinite\n2. Go to Shop → Redeem\n3. Enter code','Halo Credits or exclusive Halo content'),
    'gta':         ('GTA / Shark Cards','🚗','Grand Theft Auto Online in-game currency by Rockstar.','1. Launch GTA Online\n2. In-game Store → Redeem\n3. Enter code','GTA Online Shark Card cash'),
    'rockstar':    ('Rockstar Games','🌟','Rockstar Games store credit or content.','1. Launch game → Store → Redeem\n2. Enter code','Rockstar in-game currency or content'),
    'gift':        ('Xbox Gift Card','🎁','Xbox digital gift card for the Microsoft Store.','1. Visit xbox.com/redeemcode\n2. Sign into Microsoft account\n3. Enter 25-character code','Microsoft Store / Xbox balance credit'),
    'microsoft':   ('Microsoft Store Credit','💳','Microsoft Store credit for apps, games, subscriptions.','1. Visit account.microsoft.com\n2. Redeem a code\n3. Enter code','Microsoft Store balance'),
    'pubg':        ('PUBG: Battlegrounds','🏹',"PlayerUnknown's Battlegrounds - original Battle Royale.",'1. Launch PUBG → Shop → Redeem\n2. Enter code','G-Coin or PUBG exclusive content'),
    'rocket':      ('Rocket League','🚀','High-octane soccer with rocket-powered cars by Psyonix.','1. Launch Rocket League → Shop → Redeem\n2. Enter code','Credits or Rocket League exclusive items'),
    'overwatch':   ('Overwatch 2','🦸',"Blizzard's team-based hero shooter.",'1. Launch OW2 → Shop → Redeem\n2. Enter code','Overwatch Coins or exclusive content'),
    'diablo':      ('Diablo','💀','Action RPG dungeon crawler by Blizzard.','1. Launch game → Shop → Redeem\n2. Enter code','In-game currency or content'),
    'destiny':     ('Destiny 2','🌌','Free-to-play online FPS by Bungie.','1. Launch Destiny 2 → Silver Store → Redeem\n2. Enter code','Silver or exclusive Destiny 2 content'),
    'steam':       ('Steam Wallet','💨','Steam wallet credit for game purchases on Steam.','1. Open Steam → Account Details\n2. Add funds → Redeem Steam Wallet Code\n3. Enter code','Steam wallet credit'),
    'epic':        ('Epic Games','🔥','Epic Games Store credit or game codes.','1. store.epicgames.com → Profile → Redeem Code\n2. Enter code','Epic Games store credit or game access'),
    'playstation': ('PlayStation Store','🕹️','PSN wallet credit or game codes.','1. PS4/PS5: PlayStation Store → Redeem Codes\n2. Enter code','PSN wallet credit or PlayStation content'),
    'nintendo':    ('Nintendo eShop','🍄','Nintendo eShop credit for Switch games.','1. Open Nintendo eShop on Switch\n2. Enter Code section → Enter code','Nintendo eShop credit or game access'),
    'xbox':        ('Xbox Gift Card','🎁','Xbox / Microsoft Store value card.','1. xbox.com/redeemcode → Sign in → Enter code','Xbox store balance credit'),
    'free fire':   ('Garena Free Fire','🔥','Battle Royale mobile game by Garena.','1. Open Free Fire → Diamonds → Redeem\n2. Enter code','Diamonds or in-game content'),
    'pubg mobile': ('PUBG Mobile','📱','PUBG: Battlegrounds on mobile.','1. PUBG Mobile → Shop → Redeem\n2. Enter code','UC (Unknown Cash) or content'),
}

CODE_RE = re.compile(r'\b([A-Z0-9]{4,5}[- ][A-Z0-9]{4,5}[- ][A-Z0-9]{4,5}[- ][A-Z0-9]{4,5}[- ][A-Z0-9]{4,5})\b', re.IGNORECASE)

def detect_game(filename='', sample=''):
    txt = (filename.lower() + ' ' + sample[:500].lower())
    for kw, (name, emoji, desc, use, get) in GAMES.items():
        if kw in txt:
            return {'name': name, 'emoji': emoji, 'description': desc, 'how_to_use': use, 'what_you_get': get}
    return {'name': 'Game Code', 'emoji': '🎮', 'description': 'Digital game code for activation.',
            'how_to_use': 'Visit the official game website or console store and enter your code.',
            'what_you_get': 'Game access or in-game content'}

def parse_codes(text):
    found = CODE_RE.findall(text.upper())
    normalized = [re.sub(r'[\s]+', '-', c.strip()) for c in found]
    return list(dict.fromkeys(normalized))

# ═══════════════════════════════════════════════════════════════
#  DATABASE (Fixed Connection Leak)
# ═══════════════════════════════════════════════════════════════
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

_OWNER_HASH = hashlib.sha256('admin@123'.encode()).hexdigest()

def init_db():
    with get_db() as db:
        db.executescript(f"""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'customer',
    token TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    last_login TEXT
);
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    emoji TEXT DEFAULT '🎮',
    description TEXT,
    how_to_use TEXT,
    what_you_get TEXT
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL DEFAULT 0,
    what_you_get TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(game_id) REFERENCES games(id)
);
CREATE TABLE IF NOT EXISTS codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    code_value TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'available',
    order_id INTEGER,
    FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    payment_method TEXT,
    payment_ref TEXT,
    tracking_id TEXT UNIQUE,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    unit_price REAL,
    FOREIGN KEY(order_id) REFERENCES orders(id)
);
CREATE TABLE IF NOT EXISTS order_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    code_id INTEGER,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(code_id) REFERENCES codes(id)
);
CREATE TABLE IF NOT EXISTS support_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conv_id TEXT NOT NULL,
    user_id INTEGER,
    sender_id INTEGER,
    sender_role TEXT DEFAULT 'customer',
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT NOT NULL,
    label TEXT,
    is_default INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS upload_batches (
    id TEXT PRIMARY KEY,
    admin_id INTEGER,
    filename TEXT,
    game_name TEXT,
    game_emoji TEXT DEFAULT '🎮',
    game_desc TEXT,
    game_use TEXT,
    game_get TEXT,
    codes_json TEXT,
    total_codes INTEGER DEFAULT 0,
    dupes_removed INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    deleted INTEGER DEFAULT 0
);
INSERT OR IGNORE INTO users(username, email, password, role)
VALUES('owner', 'owner@jcnshop.com', '{_OWNER_HASH}', 'owner');
""")
    print("✅  Database ready  |  Default owner: owner / admin@123")

# ═══════════════════════════════════════════════════════════════
#  AUTH HELPERS
# ═══════════════════════════════════════════════════════════════
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def current_user():
    t = session.get('token')
    if not t: return None
    with get_db() as db:
        r = db.execute("SELECT * FROM users WHERE token=?", (t,)).fetchone()
        return dict(r) if r else None

def require_login(f):
    @wraps(f)
    def w(*a, **k):
        if not current_user(): return jsonify(error='Login required'), 401
        return f(*a, **k)
    return w

def require_admin(f):
    @wraps(f)
    def w(*a, **k):
        u = current_user()
        if not u or u['role'] not in ('admin', 'owner'):
            return jsonify(error='Admin required'), 403
        return f(*a, **k)
    return w

# ═══════════════════════════════════════════════════════════════
#  BACKUP SYSTEM
# ═══════════════════════════════════════════════════════════════
_last_backup_file = None

def do_backup():
    global _last_backup_file
    if not os.path.exists(DB_PATH): return None
    ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
    fn  = f"backup_{ts}.db"
    dst = os.path.join(BACKUP_DIR, fn)
    prev = _last_backup_file
    shutil.copy2(DB_PATH, dst)
    _last_backup_file = fn
    with get_db() as db:
        db.execute("INSERT INTO backups(filename) VALUES(?)", (fn,))
    if prev:
        def _delete_prev():
            time.sleep(300)
            old = os.path.join(BACKUP_DIR, prev)
            if os.path.exists(old):
                os.remove(old)
            try:
                with get_db() as db:
                    db.execute("UPDATE backups SET deleted=1 WHERE filename=?", (prev,))
            except: pass
        threading.Thread(target=_delete_prev, daemon=True).start()
    print(f"💾  Backup created: {fn}")
    return fn

def _backup_scheduler():
    while True:
        time.sleep(600)
        try: do_backup()
        except Exception as e: print(f"⚠  Backup error: {e}")

# ═══════════════════════════════════════════════════════════════
#  ROUTES — AUTH
# ═══════════════════════════════════════════════════════════════
@app.route('/')
def index(): return render_template_string(HTML)

@app.route('/api/auth/me')
def auth_me():
    u = current_user()
    if u: u = {k: v for k, v in u.items() if k != 'password'}
    return jsonify(user=u)

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    d = request.json or {}
    ident, pw = d.get('username','').strip(), d.get('password','')
    if not ident or not pw: return jsonify(error='Fill all fields'), 400
    with get_db() as db:
        u = db.execute("SELECT * FROM users WHERE (username=? OR email=?) AND password=?", (ident, ident, hash_pw(pw))).fetchone()
    if not u: return jsonify(error='Invalid username or password'), 401
    token = str(uuid.uuid4())
    with get_db() as db:
        db.execute("UPDATE users SET token=?, last_login=datetime('now') WHERE id=?", (token, u['id']))
    session['token'] = token
    safe = {k: v for k, v in dict(u).items() if k not in ('password','token')}
    return jsonify(user=safe)

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    d = request.json or {}
    username, email, pw = d.get('username','').strip(), d.get('email','').strip(), d.get('password','')
    if not all([username, email, pw]): return jsonify(error='All fields required'), 400
    if len(pw) < 6: return jsonify(error='Password must be at least 6 characters'), 400
    if len(username) < 3: return jsonify(error='Username must be at least 3 characters'), 400
    token = str(uuid.uuid4())
    try:
        with get_db() as db:
            db.execute("INSERT INTO users(username,email,password,role,token) VALUES(?,?,?,?,?)", (username, email, hash_pw(pw), 'customer', token))
            u = db.execute("SELECT * FROM users WHERE token=?", (token,)).fetchone()
    except sqlite3.IntegrityError:
        return jsonify(error='Username or email already taken'), 409
    session['token'] = token
    safe = {k: v for k, v in dict(u).items() if k not in ('password','token')}
    return jsonify(user=safe)

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    u = current_user()
    if u:
        with get_db() as db:
            db.execute("UPDATE users SET token=NULL WHERE id=?", (u['id'],))
    session.clear()
    return jsonify(ok=True)

# ═══════════════════════════════════════════════════════════════
#  ROUTES — PRODUCTS
# ═══════════════════════════════════════════════════════════════
@app.route('/api/products')
def get_products():
    with get_db() as db:
        rows = db.execute("""
            SELECT p.*, g.name AS game_name, g.emoji AS game_emoji,
                   g.description AS game_description, g.how_to_use AS game_how_to_use,
                   g.what_you_get AS game_what_you_get, COUNT(c.id) AS stock
            FROM products p
            LEFT JOIN games g ON g.id = p.game_id
            LEFT JOIN codes c ON c.product_id = p.id AND c.status='available'
            WHERE p.status='active'
            GROUP BY p.id ORDER BY g.name, p.name
        """).fetchall()
    return jsonify(products=[dict(r) for r in rows])

@app.route('/api/products/<int:pid>')
def get_product(pid):
    with get_db() as db:
        row = db.execute("""
            SELECT p.*, g.name AS game_name, g.emoji AS game_emoji,
                   g.description AS game_description, g.how_to_use AS game_how_to_use,
                   g.what_you_get AS game_what_you_get, COUNT(c.id) AS stock
            FROM products p
            LEFT JOIN games g ON g.id = p.game_id
            LEFT JOIN codes c ON c.product_id = p.id AND c.status='available'
            WHERE p.id=? GROUP BY p.id
        """, (pid,)).fetchone()
    return jsonify(product=dict(row) if row else None)

# ═══════════════════════════════════════════════════════════════
#  ROUTES — ORDERS & SUPPORT
# ═══════════════════════════════════════════════════════════════
@app.route('/api/orders', methods=['GET','POST'])
@require_login
def orders():
    u = current_user()
    if request.method == 'GET':
        with get_db() as db:
            rows = db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (u['id'],)).fetchall()
        return jsonify(orders=[dict(r) for r in rows])

    d = request.json or {}
    items = d.get('items', [])
    if not items: return jsonify(error='No items in order'), 400
    total = float(d.get('total', 0))
    tracking_id = 'TRK-' + str(uuid.uuid4())[:8].upper()
    with get_db() as db:
        cur = db.execute("INSERT INTO orders(user_id,total,payment_method,payment_ref,tracking_id) VALUES(?,?,?,?,?)",
                         (u['id'], total, d.get('payment_method',''), d.get('payment_ref',''), tracking_id))
        oid = cur.lastrowid
        for item in items:
            db.execute("INSERT INTO order_items(order_id,product_id,quantity,unit_price) VALUES(?,?,?,?)",
                       (oid, item['product_id'], int(item.get('quantity',1)), float(item.get('unit_price',0))))
        order = db.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    return jsonify(order=dict(order))

@app.route('/api/orders/<int:oid>')
@require_login
def get_order(oid):
    u = current_user()
    with get_db() as db:
        order = db.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (oid, u['id'])).fetchone()
        if not order: return jsonify(error='Order not found'), 404
        items = db.execute("SELECT oi.*, p.name FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE oi.order_id=?", (oid,)).fetchall()
        codes = db.execute("SELECT c.code_value FROM order_codes oc JOIN codes c ON c.id=oc.code_id WHERE oc.order_id=?", (oid,)).fetchall()
    return jsonify(order={**dict(order), 'items': [dict(i) for i in items], 'codes': [c['code_value'] for c in codes]})

@app.route('/api/orders/track/<tid>')
def track_order(tid):
    with get_db() as db:
        o = db.execute("SELECT o.*, u.username FROM orders o JOIN users u ON u.id=o.user_id WHERE o.tracking_id=?", (tid,)).fetchone()
    if not o: return jsonify(error='Order not found. Check your tracking ID.'), 404
    return jsonify(order=dict(o))

@app.route('/api/support/messages', methods=['GET','POST'])
@require_login
def support_msgs():
    u = current_user()
    conv_id = f"user-{u['id']}"
    if request.method == 'GET':
        with get_db() as db:
            msgs = db.execute("SELECT * FROM support_messages WHERE conv_id=? ORDER BY created_at ASC", (conv_id,)).fetchall()
            db.execute("UPDATE support_messages SET is_read=1 WHERE conv_id=? AND sender_role!='customer'", (conv_id,))
        return jsonify(messages=[dict(m) for m in msgs])
    d = request.json or {}
    msg = d.get('message','').strip()
    if not msg: return jsonify(error='Empty message'), 400
    with get_db() as db:
        db.execute("INSERT INTO support_messages(conv_id,user_id,sender_id,sender_role,message) VALUES(?,?,?,?,?)",
                   (conv_id, u['id'], u['id'], 'customer', msg))
        row = db.execute("SELECT * FROM support_messages WHERE rowid=last_insert_rowid()").fetchone()
    return jsonify(message=dict(row))

@app.route('/api/payment-methods', methods=['GET','POST'])
@require_login
def payment_methods():
    u = current_user()
    if request.method == 'GET':
        with get_db() as db:
            rows = db.execute("SELECT * FROM payment_methods WHERE user_id=?", (u['id'],)).fetchall()
        return jsonify(methods=[dict(r) for r in rows])
    d = request.json or {}
    ptype, label = d.get('type',''), d.get('label','')
    if ptype not in ('crypto','paypal'): return jsonify(error='Invalid type'), 400
    with get_db() as db:
        has = db.execute("SELECT id FROM payment_methods WHERE user_id=?", (u['id'],)).fetchone()
        db.execute("INSERT INTO payment_methods(user_id,type,label,is_default) VALUES(?,?,?,?)", (u['id'], ptype, label, 0 if has else 1))
    return jsonify(ok=True)

@app.route('/api/payment-methods/<int:mid>', methods=['DELETE'])
@require_login
def del_payment(mid):
    u = current_user()
    with get_db() as db:
        db.execute("DELETE FROM payment_methods WHERE id=? AND user_id=?", (mid, u['id']))
    return jsonify(ok=True)

# ═══════════════════════════════════════════════════════════════
#  ROUTES — ADMIN (With New Editing Features)
# ═══════════════════════════════════════════════════════════════
@app.route('/api/admin/stats')
@require_admin
def admin_stats():
    with get_db() as db:
        return jsonify({
            'total_products':  db.execute("SELECT COUNT(*) FROM products WHERE status='active'").fetchone()[0],
            'total_orders':    db.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
            'total_codes':     db.execute("SELECT COUNT(*) FROM codes WHERE status='available'").fetchone()[0],
            'total_users':     db.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],
            'pending_orders':  db.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0],
            'revenue':         db.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status IN ('completed','delivered')").fetchone()[0],
            'pending_support': db.execute("SELECT COUNT(*) FROM support_messages WHERE is_read=0 AND sender_role='customer'").fetchone()[0],
        })

@app.route('/api/admin/upload/parse', methods=['POST'])
@require_admin
def admin_upload_parse():
    f = request.files.get('file')
    if not f: return jsonify(error='No file uploaded'), 400
    fn = f.filename or 'upload.txt'
    content = f.read().decode('utf-8', errors='ignore')
    all_codes = parse_codes(content)
    raw_count = len(CODE_RE.findall(content.upper()))
    dupes = raw_count - len(all_codes)
    game = detect_game(fn, content)
    batch_id = str(uuid.uuid4())
    u = current_user()
    with get_db() as db:
        db.execute("""INSERT INTO upload_batches (id,admin_id,filename,game_name,game_emoji,game_desc,game_use,game_get,codes_json,total_codes,dupes_removed)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (batch_id, u['id'], fn, game['name'], game['emoji'], game['description'], game['how_to_use'], game['what_you_get'], json.dumps(all_codes), len(all_codes), dupes))
    return jsonify(batch_id=batch_id, game=game, codes=all_codes[:50], total_codes=len(all_codes), dupes_removed=dupes)

@app.route('/api/admin/upload/confirm', methods=['POST'])
@require_admin
def admin_upload_confirm():
    d = request.json or {}
    batch_id = d.get('batch_id')
    if not batch_id: return jsonify(error='Missing batch_id'), 400
    with get_db() as db:
        batch = db.execute("SELECT * FROM upload_batches WHERE id=?", (batch_id,)).fetchone()
        if not batch: return jsonify(error='Batch not found'), 404
        batch = dict(batch)
        codes = json.loads(batch['codes_json'])
        gm = db.execute("SELECT id FROM games WHERE name=?", (batch['game_name'],)).fetchone()
        game_id = gm['id'] if gm else db.execute("INSERT INTO games(name,emoji,description,how_to_use,what_you_get) VALUES(?,?,?,?,?)",
                             (batch['game_name'], batch['game_emoji'], batch['game_desc'], batch['game_use'], batch['game_get'])).lastrowid
        cur = db.execute("INSERT INTO products(game_id,name,description,price,what_you_get,status) VALUES(?,?,?,?,?,?)",
            (game_id, d.get('name','Game Code'), d.get('description',''), float(d.get('price',0)), batch['game_get'], d.get('status','active')))
        product_id = cur.lastrowid
        added = 0
        for code in codes:
            try:
                db.execute("INSERT INTO codes(product_id,code_value) VALUES(?,?)", (product_id, code))
                added += 1
            except sqlite3.IntegrityError: pass
        db.execute("UPDATE upload_batches SET status='done' WHERE id=?", (batch_id,))
    return jsonify(ok=True, count=added, product_id=product_id)

@app.route('/api/admin/orders')
@require_admin
def admin_orders():
    with get_db() as db:
        rows = db.execute("SELECT o.*, u.username FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.created_at DESC").fetchall()
    return jsonify(orders=[dict(r) for r in rows])

@app.route('/api/admin/orders/<int:oid>', methods=['PATCH'])
@require_admin
def admin_update_order(oid):
    d = request.json or {}
    status = d.get('status')
    with get_db() as db:
        db.execute("UPDATE orders SET status=?, updated_at=datetime('now') WHERE id=?", (status, oid))
        if status in ('completed', 'delivered'):
            items = db.execute("SELECT * FROM order_items WHERE order_id=?", (oid,)).fetchall()
            for item in items:
                available = db.execute("SELECT id FROM codes WHERE product_id=? AND status='available' LIMIT ?", (item['product_id'], item['quantity'])).fetchall()
                for c in available:
                    db.execute("UPDATE codes SET status='sold', order_id=? WHERE id=?", (oid, c['id']))
                    db.execute("INSERT OR IGNORE INTO order_codes(order_id,code_id) VALUES(?,?)", (oid, c['id']))
    return jsonify(ok=True)

@app.route('/api/admin/products')
@require_admin
def admin_products():
    with get_db() as db:
        rows = db.execute("""SELECT p.*, g.name AS game_name, g.emoji AS game_emoji, COUNT(c.id) AS stock 
            FROM products p LEFT JOIN games g ON g.id=p.game_id LEFT JOIN codes c ON c.product_id=p.id AND c.status='available'
            GROUP BY p.id ORDER BY g.name, p.name""").fetchall()
    return jsonify(products=[dict(r) for r in rows])

@app.route('/api/admin/products/<int:pid>', methods=['PATCH'])
@require_admin
def admin_update_product(pid):
    d = request.json or {}
    with get_db() as db:
        if 'name' in d and 'price' in d and 'description' in d:
            db.execute("UPDATE products SET name=?, price=?, description=? WHERE id=?", (d['name'], float(d['price']), d['description'], pid))
        if 'status' in d:
            db.execute("UPDATE products SET status=? WHERE id=?", (d['status'], pid))
    return jsonify(ok=True)

@app.route('/api/admin/support')
@require_admin
def admin_support():
    with get_db() as db:
        rows = db.execute("""SELECT sm.conv_id, u.username, MAX(sm.message) AS last_message, MAX(sm.created_at) AS created_at,
            SUM(CASE WHEN sm.is_read=0 AND sm.sender_role='customer' THEN 1 ELSE 0 END) AS unread
            FROM support_messages sm JOIN users u ON u.id=sm.user_id GROUP BY sm.conv_id ORDER BY created_at DESC""").fetchall()
    return jsonify(conversations=[dict(r) for r in rows])

@app.route('/api/admin/support/<conv_id>')
@require_admin
def admin_support_conv(conv_id):
    with get_db() as db:
        msgs = db.execute("SELECT sm.*, u.username FROM support_messages sm LEFT JOIN users u ON u.id=sm.sender_id WHERE sm.conv_id=? ORDER BY sm.created_at ASC", (conv_id,)).fetchall()
        db.execute("UPDATE support_messages SET is_read=1 WHERE conv_id=? AND sender_role='customer'", (conv_id,))
    return jsonify(messages=[dict(m) for m in msgs])

@app.route('/api/admin/support/<conv_id>/reply', methods=['POST'])
@require_admin
def admin_support_reply(conv_id):
    u = current_user()
    d = request.json or {}
    msg = d.get('message','').strip()
    if not msg: return jsonify(error='Empty message'), 400
    with get_db() as db:
        ur = db.execute("SELECT user_id FROM support_messages WHERE conv_id=? LIMIT 1", (conv_id,)).fetchone()
        uid = ur['user_id'] if ur else None
        db.execute("INSERT INTO support_messages(conv_id,user_id,sender_id,sender_role,message) VALUES(?,?,?,?,?)", (conv_id, uid, u['id'], 'staff', msg))
        row = db.execute("SELECT * FROM support_messages WHERE rowid=last_insert_rowid()").fetchone()
    return jsonify(message=dict(row))

@app.route('/api/admin/users')
@require_admin
def admin_users():
    with get_db() as db:
        rows = db.execute("""SELECT u.id, u.username, u.email, u.role, u.created_at, u.last_login, COUNT(o.id) AS order_count 
            FROM users u LEFT JOIN orders o ON o.user_id=u.id GROUP BY u.id ORDER BY u.created_at DESC""").fetchall()
    return jsonify(users=[dict(r) for r in rows])

@app.route('/api/admin/backups')
@require_admin
def admin_backups():
    with get_db() as db:
        rows = db.execute("SELECT * FROM backups ORDER BY created_at DESC LIMIT 30").fetchall()
    return jsonify(backups=[dict(r) for r in rows])

@app.route('/api/admin/backup', methods=['POST'])
@require_admin
def admin_do_backup():
    fn = do_backup()
    return jsonify(ok=True, filename=fn)

# ═══════════════════════════════════════════════════════════════
#  HTML TEMPLATE (With UI Fixes & New Features)
# ═══════════════════════════════════════════════════════════════
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>JCN XBOX CODES SHOP</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#06070b;--s1:#0e0f14;--s2:#14151d;--s3:#1a1b26;
  --border:#1e2030;--border2:#252637;
  --acc:#f97316;--acc2:#ea6c0a;--acc-glow:rgba(249,115,22,.25);
  --green:#22c55e;--red:#ef4444;--blue:#3b82f6;--gold:#f59e0b;--purple:#a855f7;
  --txt:#f1f5f9;--txt2:#94a3b8;--txt3:#475569;--txt4:#2d3748;
  --r:12px;--r2:8px;--r3:20px;
  --sh:0 4px 24px rgba(0,0,0,.5);
  --sh2:0 8px 40px rgba(0,0,0,.6);
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--txt);font-family:'Inter',system-ui,sans-serif;min-height:100vh;overflow-x:hidden}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}

/* ── HEADER ── */
header{position:fixed;top:0;left:0;right:0;z-index:100;height:60px;
  background:rgba(6,7,11,.85);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);display:flex;align-items:center;
  justify-content:space-between;padding:0 16px}
.logo{display:flex;align-items:center;gap:10px;text-decoration:none}
.logo-icon{width:34px;height:34px;border-radius:9px;
  background:linear-gradient(135deg,var(--acc),#c2410c);
  display:flex;align-items:center;justify-content:center;font-size:17px;
  box-shadow:0 2px 12px var(--acc-glow);flex-shrink:0}
.logo-text{font-size:13px;font-weight:800;letter-spacing:.3px;line-height:1.2;color:var(--txt)}
.logo-text span{color:var(--acc)}
.hdr-right{display:flex;align-items:center;gap:8px}
.avatar{width:34px;height:34px;border-radius:50%;
  background:linear-gradient(135deg,var(--acc),#c2410c);
  display:flex;align-items:center;justify-content:center;
  font-size:14px;font-weight:700;cursor:pointer;border:2px solid transparent;
  transition:border-color .2s;color:#fff}
.avatar:hover{border-color:var(--acc)}

/* ── BOTTOM NAV ── */
nav{position:fixed;bottom:0;left:0;right:0;z-index:100;height:60px;
  background:rgba(14,15,20,.9);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  border-top:1px solid var(--border);display:flex}
nav button{flex:1;background:none;border:none;color:var(--txt3);cursor:pointer;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:2px;font-size:9.5px;font-family:inherit;font-weight:500;
  transition:color .2s;position:relative;letter-spacing:.2px}
nav button.active{color:var(--acc)}
nav button.active::after{content:'';position:absolute;top:0;left:25%;right:25%;
  height:3px;background:var(--acc);border-radius:0 0 3px 3px}
nav button .ni{font-size:19px;transition:transform .2s}
nav button.active .ni{transform:scale(1.15)}

/* ── MAIN & TABS ── */
main{margin-top:60px;margin-bottom:60px;min-height:calc(100vh - 120px)}
.tab{display:none;padding:16px;animation:fadeUp .3s ease both}
.tab.on{display:block}

/* ── ANIMATIONS ── */
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes slideUp{from{transform:translateY(100%);opacity:0}to{transform:translateY(0);opacity:1}}
@keyframes slideIn{from{transform:translateY(-10px);opacity:0}to{transform:translateY(0);opacity:1}}
@keyframes shimmer{0%{background-position:-400% 0}100%{background-position:400% 0}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
@keyframes glow{0%,100%{box-shadow:0 0 10px var(--acc-glow)}50%{box-shadow:0 0 24px var(--acc-glow),0 0 40px var(--acc-glow)}}
.fa{animation:fadeUp .35s ease both}
.fa1{animation-delay:.05s}.fa2{animation-delay:.1s}.fa3{animation-delay:.15s}

/* ── HERO ── */
.hero{background:linear-gradient(135deg,#0e0812 0%,#120a1a 40%,#0a1020 100%);
  border:1px solid var(--border);border-radius:var(--r);padding:24px 20px;
  margin-bottom:16px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:-60px;right:-40px;width:220px;height:220px;
  background:radial-gradient(circle,rgba(249,115,22,.15) 0%,transparent 70%);pointer-events:none}
.hero-tag{font-size:10px;color:var(--acc);text-transform:uppercase;letter-spacing:1.5px;font-weight:700;margin-bottom:8px}
.hero h1{font-size:21px;font-weight:900;line-height:1.2;margin-bottom:6px}
.hero h1 span{color:var(--acc)}
.hero p{font-size:12px;color:var(--txt2);margin-bottom:14px;line-height:1.6}
.hero-pills{display:flex;gap:10px;flex-wrap:wrap}
.pill{font-size:10px;font-weight:600;padding:4px 10px;border-radius:20px;display:flex;align-items:center;gap:4px}
.pill-g{background:rgba(34,197,94,.1);color:var(--green);border:1px solid rgba(34,197,94,.2)}
.pill-o{background:rgba(249,115,22,.1);color:var(--acc);border:1px solid rgba(249,115,22,.2)}
.pill-b{background:rgba(59,130,246,.1);color:var(--blue);border:1px solid rgba(59,130,246,.2)}

/* ── SEARCH & CHIPS ── */
.search{display:flex;align-items:center;gap:10px;background:var(--s2);border:1px solid var(--border);border-radius:10px;padding:10px 14px;margin-bottom:12px;transition:border-color .2s}
.search:focus-within{border-color:var(--acc)}
.search input{flex:1;background:none;border:none;color:var(--txt);font-family:inherit;font-size:14px;outline:none}
.search input::placeholder{color:var(--txt3)}
.chips{display:flex;gap:8px;overflow-x:auto;padding-bottom:10px;margin-bottom:12px}
.chips::-webkit-scrollbar{display:none}
.chip{flex-shrink:0;padding:6px 14px;border-radius:20px;font-size:11px;font-weight:600;background:var(--s2);border:1px solid var(--border);cursor:pointer;transition:all .2s;white-space:nowrap;color:var(--txt2)}
.chip.on,.chip:hover{background:var(--acc);border-color:var(--acc);color:#fff}

/* ── PRODUCT GRID ── */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:10px}
.pcard{background:var(--s1);border:1px solid var(--border);border-radius:var(--r);overflow:hidden;cursor:pointer;transition:all .25s;position:relative}
.pcard:hover{border-color:var(--acc);transform:translateY(-3px);box-shadow:0 10px 30px rgba(249,115,22,.12)}
.pcard:active{transform:translateY(0)}
.pcard-banner{background:linear-gradient(135deg,#1a0f2e,#0d1826);height:86px;display:flex;align-items:center;justify-content:center;font-size:40px;border-bottom:1px solid var(--border);position:relative}
.stock-badge{position:absolute;top:6px;right:6px;font-size:9px;font-weight:700;padding:2px 6px;border-radius:10px;background:rgba(0,0,0,.6)}
.pcard-info{padding:10px}
.pcard-game{font-size:9.5px;color:var(--txt3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px;font-weight:600}
.pcard-name{font-size:12.5px;font-weight:700;margin-bottom:6px;line-height:1.3;color:var(--txt)}
.pcard-price{font-size:16px;font-weight:900;color:var(--acc)}
.pcard-qty{font-size:10px;color:var(--txt3);margin-top:3px}

/* ── CARDS ── */
.card{background:var(--s1);border:1px solid var(--border);border-radius:var(--r);padding:14px}
.card2{background:var(--s2);border:1px solid var(--border);border-radius:var(--r2);padding:12px}

/* ── BUTTONS ── */
.btn{padding:10px 18px;border-radius:var(--r2);border:none;cursor:pointer;font-family:inherit;font-size:13px;font-weight:600;transition:all .2s;display:inline-flex;align-items:center;justify-content:center;gap:6px}
.btn-primary{background:var(--acc);color:#fff}
.btn-primary:hover:not(:disabled){background:var(--acc2);transform:translateY(-1px);box-shadow:0 4px 16px var(--acc-glow)}
.btn-sec{background:var(--s3);color:var(--txt);border:1px solid var(--border)}
.btn-sec:hover:not(:disabled){background:var(--border2)}
.btn-danger{background:var(--red);color:#fff}
.btn-success{background:var(--green);color:#fff}
.btn-ghost{background:none;color:var(--txt2);border:1px solid var(--border)}
.btn-ghost:hover:not(:disabled){background:var(--s2)}
.btn-sm{padding:6px 12px;font-size:11.5px}
.btn-block{width:100%}
.btn:disabled{opacity:.5;cursor:not-allowed;transform:none!important}

/* ── MODAL ── */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.82);backdrop-filter:blur(6px);z-index:200;display:flex;align-items:flex-end;justify-content:center}
.overlay.center{align-items:center;padding:16px}
.modal{background:var(--s1);border:1px solid var(--border2);border-radius:var(--r3) var(--r3) 0 0;width:100%;max-width:520px;max-height:92vh;overflow-y:auto;animation:slideUp .28s ease}
.modal.center{border-radius:var(--r3);max-height:85vh;animation:slideIn .28s ease}
.mh{padding:18px 18px 0;display:flex;align-items:center;justify-content:space-between}
.mt{font-size:17px;font-weight:800}
.mx{width:30px;height:30px;border-radius:50%;background:var(--s3);border:none;color:var(--txt2);cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center;transition:all .2s}
.mx:hover{background:var(--border);color:var(--txt)}
.mb{padding:18px}

/* ── FORM ── */
.fg{margin-bottom:14px}
.fl{display:block;font-size:11px;font-weight:700;color:var(--txt2);margin-bottom:5px;text-transform:uppercase;letter-spacing:.5px}
.fi{width:100%;background:var(--s2);border:1px solid var(--border);border-radius:var(--r2);padding:10px 13px;color:var(--txt);font-family:inherit;font-size:13px;transition:border-color .2s;outline:none}
.fi:focus{border-color:var(--acc)}
textarea.fi{resize:vertical;min-height:70px}

/* ── BADGES ── */
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:20px;font-size:10.5px;font-weight:700}
.bg-green{background:rgba(34,197,94,.12);color:var(--green);border:1px solid rgba(34,197,94,.2)}
.bg-orange{background:rgba(249,115,22,.12);color:var(--acc);border:1px solid rgba(249,115,22,.2)}
.bg-red{background:rgba(239,68,68,.12);color:var(--red);border:1px solid rgba(239,68,68,.2)}
.bg-blue{background:rgba(59,130,246,.12);color:var(--blue);border:1px solid rgba(59,130,246,.2)}
.bg-gold{background:rgba(245,158,11,.12);color:var(--gold);border:1px solid rgba(245,158,11,.2)}
.bg-purple{background:rgba(168,85,247,.12);color:var(--purple);border:1px solid rgba(168,85,247,.2)}
.bg-yellow{background:rgba(234,179,8,.12);color:#eab308;border:1px solid rgba(234,179,8,.2)}

/* ── CHAT & TABLES ── */
.chat-wrap{display:flex;flex-direction:column;height:calc(100vh - 150px);overflow:hidden}
.chat-hdr{padding:14px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;flex-shrink:0}
.chat-msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}
.cmsg{max-width:82%;padding:10px 13px;border-radius:14px;font-size:13px;line-height:1.5}
.cmsg.mine{background:var(--acc);color:#fff;border-radius:14px 14px 4px 14px;align-self:flex-end}
.cmsg.theirs{background:var(--s2);border:1px solid var(--border);border-radius:14px 14px 14px 4px;align-self:flex-start}
.cmsg-time{font-size:9.5px;color:var(--txt3);margin:3px 0 0}
.chat-input{padding:12px 14px;border-top:1px solid var(--border);display:flex;gap:8px;flex-shrink:0}
.tbl{width:100%;border-collapse:collapse;font-size:12px}
.tbl th{background:var(--s2);padding:9px 10px;text-align:left;font-weight:700;color:var(--txt2);white-space:nowrap;font-size:11px}
.tbl td{padding:9px 10px;border-bottom:1px solid var(--border)}
.tbl tr:hover td{background:var(--s2)}
.tbl-wrap{overflow-x:auto;border-radius:var(--r);border:1px solid var(--border)}

/* ── STATS & TOAST ── */
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px}
.stat{background:var(--s2);border:1px solid var(--border);border-radius:10px;padding:12px 8px;text-align:center}
.stat-v{font-size:20px;font-weight:900;color:var(--acc)}
.stat-l{font-size:9.5px;color:var(--txt3);text-transform:uppercase;letter-spacing:.5px;margin-top:3px}
.toast-box{position:fixed;top:70px;right:14px;z-index:400;display:flex;flex-direction:column;gap:7px}
.toast{background:var(--s2);border:1px solid var(--border2);border-radius:10px;padding:11px 14px;font-size:12.5px;max-width:270px;animation:slideIn .25s ease;display:flex;align-items:center;gap:8px;box-shadow:var(--sh)}
.toast.ok{border-left:3px solid var(--green)}
.toast.err{border-left:3px solid var(--red)}
.toast.info{border-left:3px solid var(--blue)}

/* ── MISC ── */
.empty{text-align:center;padding:44px 20px;color:var(--txt3)}
.empty-i{font-size:44px;margin-bottom:10px;display:block}
.empty-t{font-size:15px;font-weight:700;color:var(--txt2);margin-bottom:5px}
.fab{position:fixed;bottom:72px;right:14px;width:46px;height:46px;border-radius:50%;background:linear-gradient(135deg,var(--acc),#c2410c);border:none;color:#fff;font-size:20px;cursor:pointer;box-shadow:0 4px 20px var(--acc-glow);z-index:90;display:none;align-items:center;justify-content:center;transition:transform .2s}
.fab:hover{transform:scale(1.1);animation:glow 1.5s ease infinite}
.code-val{font-family:'Courier New',monospace;font-size:13px;font-weight:700;letter-spacing:1.5px;background:var(--s2);border:1px solid var(--border);border-radius:6px;padding:8px 12px;color:var(--green);word-break:break-all;cursor:pointer;user-select:all}
.code-val:hover{border-color:var(--green)}
.pd-banner{background:linear-gradient(135deg,#1a0f2e,#0d1826);height:120px;display:flex;align-items:center;justify-content:center;font-size:60px;border-bottom:1px solid var(--border);border-radius:var(--r) var(--r) 0 0}
.scroll-y{overflow-y:auto;max-height:240px}
hr.div{border:none;border-top:1px solid var(--border);margin:14px 0}
.lbl-sec{font-size:10px;font-weight:700;color:var(--txt2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}

@media(min-width:600px){.grid{grid-template-columns:repeat(auto-fill,minmax(170px,1fr))}nav button{font-size:11px}}
</style>
</head>
<body>

<!-- HEADER -->
<header>
  <a class="logo" href="/">
    <div class="logo-icon">🎮</div>
    <div class="logo-text">JCN <span>XBOX</span><br>CODES SHOP</div>
  </a>
  <div class="hdr-right" id="hdrRight">
    <button class="btn btn-primary btn-sm" onclick="A.auth('login')">Sign In</button>
  </div>
</header>

<!-- MAIN -->
<main>
  <!-- SHOP -->
  <div id="t-shop" class="tab on">
    <div class="hero fa">
      <div class="hero-tag">⚡ JCN XBOX CODES SHOP</div>
      <h1>Premium Game<br><span>Codes & Keys</span> 🎮</h1>
      <p>Instant delivery · 100% legit codes · All major games · Best prices</p>
      <div class="hero-pills">
        <span class="pill pill-g">✓ Verified</span>
        <span class="pill pill-o">⚡ Instant</span>
        <span class="pill pill-b">🔒 Secure</span>
      </div>
    </div>
    <div class="search fa1">
      <span style="color:var(--txt3)">🔍</span>
      <input id="shopQ" placeholder="Search games, codes..." oninput="A.filterP(this.value)">
    </div>
    <div class="chips fa2" id="gameChips">
      <div class="chip on" onclick="A.setFilter('all',this)">All Games</div>
    </div>
    <div class="grid" id="pgrid">
      <div class="skel" style="height:175px"></div>
      <div class="skel" style="height:175px"></div>
      <div class="skel" style="height:175px"></div>
      <div class="skel" style="height:175px"></div>
    </div>
  </div>

  <!-- MY ORDERS -->
  <div id="t-orders" class="tab">
    <div class="sh fa"><h2>📦 My Orders</h2>
      <button class="btn btn-sec btn-sm" onclick="A.loadOrders()">↻</button></div>
    <div id="orderList"><div class="empty"><span class="empty-i">📦</span>
      <div class="empty-t">No orders yet</div>
      <div class="empty-s">Your orders appear here</div></div></div>
  </div>

  <!-- TRACK -->
  <div id="t-track" class="tab">
    <h2 style="font-size:15px;font-weight:800;margin-bottom:14px" class="fa">📍 Track Your Order</h2>
    <div class="card fa1">
      <div class="fg">
        <label class="fl">Tracking ID</label>
        <input id="trackIn" class="fi" placeholder="TRK-XXXXXXXX" onkeypress="if(event.key==='Enter')A.track()">
      </div>
      <button class="btn btn-primary btn-block" onclick="A.track()">🔍 Track Now</button>
    </div>
    <div id="trackOut" style="margin-top:14px"></div>
  </div>

  <!-- SUPPORT CHAT -->
  <div id="t-support" class="tab" style="padding:0">
    <div class="chat-wrap">
      <div class="chat-hdr">
        <div class="chat-avtr">🎧</div>
        <div>
          <div style="font-size:14px;font-weight:700">JCN Support Team</div>
          <div style="font-size:11px;color:var(--green)">● Online · Fast response</div>
        </div>
      </div>
      <div class="chat-msgs" id="chatMsgs">
        <div style="align-self:flex-start">
          <div class="cmsg theirs">👋 Welcome to <strong>JCN XBOX CODES SHOP</strong>! How can we help you today?</div>
          <div class="cmsg-time">Support</div>
        </div>
      </div>
      <div class="chat-input">
        <input id="chatIn" class="fi" placeholder="Type a message..." onkeypress="if(event.key==='Enter')A.sendMsg()">
        <button class="btn btn-primary" onclick="A.sendMsg()" style="flex-shrink:0">➤</button>
      </div>
    </div>
  </div>

  <!-- PAYMENT METHODS -->
  <div id="t-pay" class="tab">
    <div class="sh fa"><h2>💳 Payment Methods</h2>
      <button class="btn btn-primary btn-sm" onclick="A.addPay()">+ Add</button></div>
    <div id="payList">
      <div class="empty"><span class="empty-i">💳</span>
        <div class="empty-t">No saved methods</div>
        <div class="empty-s">Add Crypto or PayPal</div></div>
    </div>
  </div>
</main>

<!-- NAV -->
<nav>
  <button id="nb-shop" class="active" onclick="A.tab('shop',this)"><span class="ni">🏪</span>Shop</button>
  <button id="nb-orders" onclick="A.tab('orders',this)"><span class="ni">📦</span>My Orders</button>
  <button id="nb-track" onclick="A.tab('track',this)"><span class="ni">📍</span>Track</button>
  <button id="nb-support" onclick="A.tab('support',this)"><span class="ni">💬</span>Support</button>
  <button id="nb-pay" onclick="A.tab('pay',this)"><span class="ni">💳</span>Payment</button>
</nav>

<!-- ADMIN FAB & TOASTS & MODALS -->
<button class="fab" id="adminFab" onclick="A.admin()" title="Admin Panel">⚙️</button>
<div class="toast-box" id="toasts"></div>
<div id="mc"></div>

<script>
const A = {
  user: null, prods: [], filter: 'all', _qty: 1, _prod: null,
  _payMethod: null, _newPayType: null, _adminConv: null, _adminUser: '',

  async init() {
    await this.me();
    await this.loadProds();
    setInterval(() => { if(this.user && document.getElementById('t-support').classList.contains('on')) this.loadMsgs(); }, 5000);
  },

  async me() {
    try {
      const d = await (await fetch('/api/auth/me')).json();
      if (d.user) { this.user = d.user; this.updateHdr(); }
    } catch(e) {}
  },

  updateHdr() {
    const el = document.getElementById('hdrRight');
    if (this.user) {
      el.innerHTML = `<div class="avatar" onclick="A.userMenu()" title="${this.esc(this.user.username)}">${this.user.username[0].toUpperCase()}</div>`;
      if (['admin','owner'].includes(this.user.role)) document.getElementById('adminFab').style.display = 'flex';
    } else {
      el.innerHTML = `<button class="btn btn-primary btn-sm" onclick="A.auth('login')">Sign In</button>`;
      document.getElementById('adminFab').style.display = 'none';
    }
  },

  tab(name, btn) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
    document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
    document.getElementById('t-'+name).classList.add('on');
    btn.classList.add('active');
    if (name==='orders') this.loadOrders();
    if (name==='pay') this.loadPay();
    if (name==='support') this.loadMsgs();
  },

  async loadProds() {
    try {
      const d = await (await fetch('/api/products')).json();
      this.prods = d.products || [];
      this.renderProds();
      this.buildChips();
    } catch(e) { document.getElementById('pgrid').innerHTML = '<p style="color:var(--txt3);text-align:center;padding:24px;grid-column:1/-1">Failed to load products</p>'; }
  },

  buildChips() {
    const games = [...new Set(this.prods.map(p=>p.game_name).filter(Boolean))].sort();
    const c = document.getElementById('gameChips');
    c.innerHTML = `<div class="chip on" onclick="A.setFilter('all',this)">All Games</div>`;
    games.forEach(g => {
      const d = document.createElement('div'); d.className = 'chip'; d.textContent = g;
      d.onclick = function(){ A.setFilter(g,this); };
      c.appendChild(d);
    });
  },

  setFilter(g, el) {
    this.filter = g;
    document.querySelectorAll('#gameChips .chip').forEach(c=>c.classList.remove('on'));
    el.classList.add('on');
    this.renderProds();
  },

  filterP(q) {
    const r = q.toLowerCase();
    const list = this.prods.filter(p => p.name.toLowerCase().includes(r)||(p.game_name||'').toLowerCase().includes(r));
    this.renderProds(list);
  },

  renderProds(list) {
    const ps = list || (this.filter==='all' ? this.prods : this.prods.filter(p=>p.game_name===this.filter));
    const g = document.getElementById('pgrid');
    if (!ps.length) {
      g.innerHTML = `<div class="empty" style="grid-column:1/-1"><span class="empty-i">🎮</span><div class="empty-t">No products found</div><div class="empty-s">Check back soon!</div></div>`;
      return;
    }
    g.innerHTML = ps.map((p,i)=>{
      let stockBadge = p.stock > 0 ? (p.stock < 5 ? `<span class="stock-badge bg-yellow">Low Stock: ${p.stock}</span>` : `<span class="stock-badge bg-green">${p.stock} left</span>`) : `<span class="stock-badge bg-red">Sold Out</span>`;
      return `
      <div class="pcard fa" style="animation-delay:${i*.04}s" onclick="A.openProd(${p.id})">
        <div class="pcard-banner">
          ${this.esc(p.game_emoji||'🎮')}
          ${stockBadge}
        </div>
        <div class="pcard-info">
          <div class="pcard-game">${this.esc(p.game_name||'Game')}</div>
          <div class="pcard-name">${this.esc(p.name)}</div>
          <div class="pcard-price">$${parseFloat(p.price).toFixed(2)}</div>
        </div>
      </div>`}).join('');
  },

  async openProd(id) {
    const d = await (await fetch('/api/products/'+id)).json();
    if (!d.product) return;
    const p = d.product; this._prod = p; this._qty = 1;
    const stock = p.stock || 0;
    this.modal(`
      <div class="pd-banner">${this.esc(p.game_emoji||'🎮')}</div>
      <div class="mh" style="border-radius:0"><span class="mt">${this.esc(p.name)}</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb">
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">
          ${stock>0?'<span class="badge bg-green">● In Stock</span>':'<span class="badge bg-red">Sold Out</span>'}
          <span class="badge bg-blue">${this.esc(p.game_name||'Game')}</span>
        </div>
        <p style="font-size:13px;color:var(--txt2);margin-bottom:14px;line-height:1.6">${this.esc(p.game_description||p.description||'')}</p>
        <div class="card2" style="margin-bottom:10px">
          <div class="lbl-sec" style="color:var(--acc)">🎁 What You Get</div>
          <p style="font-size:12.5px;color:var(--txt2);line-height:1.6">${this.esc(p.what_you_get||p.game_what_you_get||'Game access or content')}</p>
        </div>
        <div class="card2" style="margin-bottom:14px">
          <div class="lbl-sec" style="color:var(--blue)">📋 How to Redeem</div>
          <div style="font-size:12px;color:var(--txt2);white-space:pre-line;line-height:1.8">${this.esc(p.game_how_to_use||'Visit official website to redeem')}</div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-size:26px;font-weight:900;color:var(--acc)">$${parseFloat(p.price).toFixed(2)}</div>
          <div class="qty">
            <button class="qb" onclick="A.chQty(-1)">−</button>
            <span class="qv" id="qv">1</span>
            <button class="qb" onclick="A.chQty(1,${stock})">+</button>
          </div>
        </div>
        <div style="font-size:12px;color:var(--txt3);margin-bottom:14px" id="qtot">Total: $${parseFloat(p.price).toFixed(2)}</div>
        ${stock>0?`<button class="btn btn-primary btn-block" id="buyBtn" onclick="A.buy(${p.id},'${p.name.replace(/'/g,"\\'")}',${p.price})">🛒 Buy Now</button>`
          :'<button class="btn btn-ghost btn-block" disabled>Out of Stock</button>'}
      </div>`);
  },

  chQty(d, max=99) {
    this._qty = Math.max(1, Math.min(max, this._qty+d));
    document.getElementById('qv').textContent = this._qty;
    if (this._prod) document.getElementById('qtot').textContent = `Total: $${(this._prod.price*this._qty).toFixed(2)}`;
  },

  buy(pid, name, price) {
    if (!this.user) { this.cls(); this.auth('login'); this.toast('Sign in to purchase','info'); return; }
    const qty = this._qty, total = (price*qty).toFixed(2);
    this.modal(`
      <div class="mh"><span class="mt">🛒 Checkout</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb">
        <div class="card2" style="margin-bottom:14px">
          <div style="font-size:13px;font-weight:700;margin-bottom:8px">${this.esc(name)}</div>
          <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--txt2)">
            <span>Qty: ${qty}</span><span>$${parseFloat(price).toFixed(2)} each</span>
          </div>
          <hr class="div">
          <div style="display:flex;justify-content:space-between;font-size:16px;font-weight:800">
            <span>Total</span><span style="color:var(--acc)">$${total}</span>
          </div>
        </div>
        <div class="lbl-sec">Select Payment Method</div>
        <div class="payopt" id="po-crypto" onclick="A.selPay('crypto')">
          <div class="pay-icon" style="background:rgba(245,158,11,.1);font-size:24px">₿</div>
          <div><div style="font-size:14px;font-weight:700">Cryptocurrency</div><div style="font-size:11px;color:var(--txt2)">BTC · ETH · USDT</div></div>
        </div>
        <div class="payopt" id="po-paypal" onclick="A.selPay('paypal')">
          <div class="pay-icon" style="background:rgba(59,130,246,.1);font-size:22px">🅿️</div>
          <div><div style="font-size:14px;font-weight:700">PayPal</div><div style="font-size:11px;color:var(--txt2)">Secure PayPal payment</div></div>
        </div>
        <div id="payDetails" style="display:none;margin-top:10px"></div>
        <button class="btn btn-primary btn-block" id="placeBtn" onclick="A.place(${pid},${qty},${price})" disabled style="opacity:.4;margin-top:12px">Place Order</button>
      </div>`);
  },

  selPay(method) {
    this._payMethod = method;
    document.querySelectorAll('.payopt').forEach(e=>e.classList.remove('sel'));
    document.getElementById('po-'+method).classList.add('sel');
    const det = document.getElementById('payDetails'); det.style.display = 'block';
    if (method==='crypto') {
      det.innerHTML = `<div class="card2"><div class="lbl-sec" style="color:var(--gold)">💰 Crypto Payment</div>
        <div class="fg"><label class="fl">Cryptocurrency</label><select class="fi" id="ctype"><option>Bitcoin (BTC)</option><option>Ethereum (ETH)</option><option>USDT (TRC20)</option></select></div>
        <div class="fg"><label class="fl">Transaction Hash / TXID</label><input class="fi" id="pref" placeholder="Enter tx hash after sending..."></div>
        <p style="font-size:10.5px;color:var(--txt3)">⚠ Complete payment first, then paste your hash</p></div>`;
    } else {
      det.innerHTML = `<div class="card2"><div class="lbl-sec" style="color:var(--blue)">🅿️ PayPal</div>
        <div class="fg"><label class="fl">PayPal Transaction ID</label><input class="fi" id="pref" placeholder="Enter PayPal transaction ID..."></div>
        <p style="font-size:10.5px;color:var(--txt3)">⚠ Send payment first, then enter your ID</p></div>`;
    }
    const btn = document.getElementById('placeBtn'); btn.disabled = false; btn.style.opacity = '1';
  },

  async place(pid, qty, price) {
    if (!this._payMethod) { this.toast('Select a payment method','err'); return; }
    const btn = document.getElementById('placeBtn'); btn.disabled = true; btn.textContent = 'Processing...';
    const ref = document.getElementById('pref')?.value || '';
    try {
      const d = await (await fetch('/api/orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items:[{product_id:pid,quantity:qty,unit_price:price}],payment_method:this._payMethod,payment_ref:ref,total:price*qty})})).json();
      if (d.error) { this.toast(d.error,'err'); btn.disabled=false; btn.textContent='Place Order'; return; }
      const o = d.order;
      this.modal(`
        <div class="mh"><span class="mt">✅ Order Placed!</span><button class="mx" onclick="A.cls()">✕</button></div>
        <div class="mb" style="text-align:center">
          <div style="font-size:54px;margin-bottom:12px">🎉</div>
          <h3 style="font-size:17px;font-weight:800;margin-bottom:6px">Order Confirmed!</h3>
          <p style="font-size:12.5px;color:var(--txt2);margin-bottom:16px;line-height:1.6">Your order is placed. Codes will be delivered after payment verification.</p>
          <div class="card2" style="margin-bottom:10px;text-align:left">
            <div style="font-size:10px;color:var(--txt3);margin-bottom:3px">TRACKING ID</div>
            <div style="font-size:15px;font-weight:800;color:var(--acc)">${this.esc(o.tracking_id)}</div>
          </div>
          <button class="btn btn-primary btn-block" onclick="A.cls();A.tab('orders',document.getElementById('nb-orders'))">View My Orders</button>
        </div>`);
    } catch(e) { this.toast('Order failed. Try again.','err'); btn.disabled=false; btn.textContent='Place Order'; }
  },

  async loadOrders() {
    if (!this.user) {
      document.getElementById('orderList').innerHTML = `<div class="empty"><span class="empty-i">🔒</span><div class="empty-t">Sign in to view orders</div><button class="btn btn-primary" style="margin-top:12px" onclick="A.auth('login')">Sign In</button></div>`;
      return;
    }
    try {
      const d = await (await fetch('/api/orders')).json();
      const os = d.orders||[];
      if (!os.length) {
        document.getElementById('orderList').innerHTML = `<div class="empty"><span class="empty-i">📦</span><div class="empty-t">No orders yet</div><div class="empty-s">Your orders appear after purchase</div></div>`;
        return;
      }
      document.getElementById('orderList').innerHTML = os.map(o=>`
        <div class="oitem" onclick="A.viewOrder(${o.id})">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
            <div><div style="font-size:11px;color:var(--txt3);margin-bottom:2px">${(o.created_at||'').split('T')[0]}</div>
              <div style="font-size:14px;font-weight:700">#${o.id} · <span style="color:var(--txt3);font-size:12px">${this.esc(o.tracking_id||'')}</span></div></div>
            <span class="badge ${this.obadge(o.status)}">${o.status}</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div style="font-size:11px;color:var(--txt2)">${this.esc(o.payment_method||'')}</div>
            <div style="font-size:16px;font-weight:900;color:var(--acc)">$${parseFloat(o.total).toFixed(2)}</div>
          </div>
        </div>`).join('');
    } catch(e) {}
  },

  obadge(s){return{pending:'bg-orange',processing:'bg-blue',completed:'bg-green',delivered:'bg-green',cancelled:'bg-red'}[s]||'bg-orange';},

  async viewOrder(id) {
    const d = await (await fetch('/api/orders/'+id)).json();
    if (!d.order) return;
    const o = d.order;
    this.modal(`
      <div class="mh"><span class="mt">Order #${o.id}</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb">
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px">
          <span class="badge ${this.obadge(o.status)}">${o.status}</span>
          <span class="badge bg-blue">${this.esc(o.payment_method||'')}</span>
        </div>
        ${o.codes&&o.codes.length?`
        <div class="card2" style="margin-bottom:10px">
          <div class="lbl-sec" style="color:var(--green)">✅ Your Codes (tap to copy)</div>
          ${o.codes.map(c=>`<div class="code-val" onclick="A.copy('${c}',this)" style="margin-bottom:6px">${this.esc(c)}</div>`).join('')}
        </div>`:'<div class="card2" style="margin-bottom:10px;text-align:center;color:var(--txt3)">Codes will appear here once verified</div>'}
      </div>`);
  },

  async loadMsgs() {
    if (!this.user) { document.getElementById('chatMsgs').innerHTML=`<div style="text-align:center;padding:24px"><div style="color:var(--txt3);margin-bottom:12px">Sign in to chat</div><button class="btn btn-primary" onclick="A.auth('login')">Sign In</button></div>`; return; }
    try {
      const d = await (await fetch('/api/support/messages')).json();
      const msgs = d.messages||[];
      const c = document.getElementById('chatMsgs');
      c.innerHTML=msgs.length?msgs.map(m=>{
        const mine = m.sender_role==='customer';
        return `<div style="align-self:${mine?'flex-end':'flex-start'}"><div class="cmsg ${mine?'mine':'theirs'}">${this.esc(m.message)}</div><div class="cmsg-time" style="${mine?'text-align:right':''}">${mine?'You':'Staff'} · ${(m.created_at||'').split('T')[1]?.slice(0,5)||''}</div></div>`;
      }).join(''):`<div style="align-self:flex-start"><div class="cmsg theirs">👋 Welcome! How can we help?</div></div>`;
      c.scrollTop = c.scrollHeight;
    } catch(e) {}
  },

  async sendMsg() {
    const inp = document.getElementById('chatIn'), msg = inp.value.trim();
    if (!msg || !this.user) return;
    inp.value = '';
    document.getElementById('chatMsgs').innerHTML += `<div style="align-self:flex-end"><div class="cmsg mine">${this.esc(msg)}</div></div>`;
    document.getElementById('chatMsgs').scrollTop = document.getElementById('chatMsgs').scrollHeight;
    await fetch('/api/support/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
  },

  async loadPay() {
    if (!this.user) { document.getElementById('payList').innerHTML=`<div class="empty"><span class="empty-i">🔒</span><div class="empty-t">Sign in first</div><button class="btn btn-primary" style="margin-top:12px" onclick="A.auth('login')">Sign In</button></div>`; return; }
    const d = await (await fetch('/api/payment-methods')).json();
    const ms = d.methods||[];
    document.getElementById('payList').innerHTML=ms.length?ms.map(m=>`
      <div class="card" style="margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;gap:12px">
        <div style="display:flex;align-items:center;gap:12px"><span style="font-size:24px">${m.type==='crypto'?'₿':'🅿️'}</span>
          <div><div style="font-size:14px;font-weight:700">${this.esc(m.label||m.type)}</div><div style="font-size:11px;color:var(--txt3)">${m.type}</div></div></div>
        <button class="btn btn-danger btn-sm" onclick="A.delPay(${m.id})">✕</button>
      </div>`).join(''):`<div class="empty"><span class="empty-i">💳</span><div class="empty-t">No saved methods</div><button class="btn btn-primary" style="margin-top:12px" onclick="A.addPay()">+ Add Method</button></div>`;
  },

  addPay() {
    this.modal(`
      <div class="mh"><span class="mt">Add Payment Method</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb">
        <div class="payopt" id="np-crypto" onclick="A.selNewPay('crypto')"><div class="pay-icon" style="background:rgba(245,158,11,.1);font-size:24px">₿</div><div style="font-size:14px;font-weight:700">Cryptocurrency</div></div>
        <div class="payopt" id="np-paypal" onclick="A.selNewPay('paypal')"><div class="pay-icon" style="background:rgba(59,130,246,.1);font-size:22px">🅿️</div><div style="font-size:14px;font-weight:700">PayPal</div></div>
        <div id="npForm" style="display:none;margin-top:10px"></div>
        <button class="btn btn-primary btn-block" style="margin-top:12px" onclick="A.savePay()">Save Method</button>
      </div>`);
  },

  selNewPay(t) {
    this._newPayType = t;
    document.querySelectorAll('[id^="np-"]').forEach(e=>e.classList.remove('sel'));
    document.getElementById('np-'+t).classList.add('sel');
    const f = document.getElementById('npForm'); f.style.display='block';
    f.innerHTML = t==='crypto'?`<div class="fg"><label class="fl">Label</label><input class="fi" id="npLabel" placeholder="My BTC Wallet"></div>`:`<div class="fg"><label class="fl">PayPal Email</label><input class="fi" id="npLabel" type="email" placeholder="you@paypal.com"></div>`;
  },

  async savePay() {
    if (!this._newPayType) return;
    const label = document.getElementById('npLabel')?.value || this._newPayType;
    await fetch('/api/payment-methods',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:this._newPayType,label})});
    this.cls(); this.toast('Saved!','ok'); this.loadPay();
  },

  async delPay(id) {
    if (!confirm('Remove this method?')) return;
    await fetch('/api/payment-methods/'+id,{method:'DELETE'});
    this.loadPay(); this.toast('Removed','ok');
  },

  auth(tab='login') {
    this.modal(`
      <div class="mh"><span class="mt" id="atitle">${tab==='login'?'Sign In':'Create Account'}</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb">
        <div style="display:flex;gap:6px;background:var(--s2);border-radius:8px;padding:4px;margin-bottom:18px">
          <button onclick="A.authTab('login')" style="flex:1;padding:8px;border-radius:6px;border:none;font-family:inherit;font-size:12.5px;font-weight:700;cursor:pointer;background:${tab==='login'?'var(--acc)':'transparent'};color:${tab==='login'?'#fff':'var(--txt2)'}">Sign In</button>
          <button onclick="A.authTab('register')" style="flex:1;padding:8px;border-radius:6px;border:none;font-family:inherit;font-size:12.5px;font-weight:700;cursor:pointer;background:${tab==='register'?'var(--acc)':'transparent'};color:${tab==='register'?'#fff':'var(--txt2)'}">Register</button>
        </div>
        <div id="aform">${this.authForm(tab)}</div>
      </div>`);
  },

  authForm(tab){
    if(tab==='login') return `
      <div class="fg"><label class="fl">Username or Email</label><input class="fi" id="au" placeholder="Enter username or email"></div>
      <div class="fg"><label class="fl">Password</label><input class="fi" type="password" id="ap" placeholder="Password" onkeypress="if(event.key==='Enter')A.doAuth('login')"></div>
      <button class="btn btn-primary btn-block" onclick="A.doAuth('login')">Sign In →</button>`;
    return `
      <div class="fg"><label class="fl">Username</label><input class="fi" id="aun" placeholder="Choose username"></div>
      <div class="fg"><label class="fl">Email</label><input class="fi" id="au" type="email" placeholder="your@email.com"></div>
      <div class="fg"><label class="fl">Password</label><input class="fi" type="password" id="ap" placeholder="Min 6 characters" onkeypress="if(event.key==='Enter')A.doAuth('register')"></div>
      <button class="btn btn-primary btn-block" onclick="A.doAuth('register')">Create Account →</button>`;
  },

  authTab(tab){
    document.getElementById('atitle').textContent = tab==='login'?'Sign In':'Create Account';
    document.getElementById('aform').innerHTML = this.authForm(tab);
  },

  async doAuth(type) {
    const u=document.getElementById('au')?.value, p=document.getElementById('ap')?.value, un=document.getElementById('aun')?.value;
    if(!u||!p){this.toast('Fill all fields','err');return;}
    try {
      const body = type==='login'?{username:u,password:p}:{username:un,email:u,password:p};
      const d = await (await fetch('/api/auth/'+type,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
      if(d.error){this.toast(d.error,'err');return;}
      this.user=d.user; this.cls(); this.updateHdr(); this.toast('Welcome, '+d.user.username+'! 👋','ok');
    } catch(e){this.toast('Auth failed','err');}
  },

  userMenu(){
    if(!this.user)return;
    this.modal(`
      <div class="mh"><span class="mt">My Account</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb" style="text-align:center">
        <div style="width:62px;height:62px;border-radius:50%;background:linear-gradient(135deg,var(--acc),#c2410c);display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:800;margin:0 auto 10px;color:#fff">${this.user.username[0].toUpperCase()}</div>
        <div style="font-size:16px;font-weight:800">${this.esc(this.user.username)}</div>
        <div style="font-size:12px;color:var(--txt2);margin-bottom:6px">${this.esc(this.user.email)}</div>
        <span class="badge bg-gold">${this.user.role}</span><hr class="div" style="margin:14px 0">
        <button class="btn btn-danger btn-block" onclick="A.logout()">Sign Out</button>
      </div>`,true);
  },

  async logout(){ await fetch('/api/auth/logout',{method:'POST'}); this.user=null; this.cls(); this.updateHdr(); this.toast('Signed out','info'); },

  // ── ADMIN ──
  async admin(){
    if (!this.user||!['admin','owner'].includes(this.user.role)){
      this.modal(`<div class="mh"><span class="mt">⚙️ Admin Access</span><button class="mx" onclick="A.cls()">✕</button></div><div class="mb"><p style="font-size:13px;color:var(--txt2);margin-bottom:14px">Sign in as admin/owner to access the panel.</p><button class="btn btn-primary btn-block" onclick="A.cls();A.auth('login')">Sign In</button></div>`); return;
    }
    let stats={}; try{const d=await(await fetch('/api/admin/stats')).json();stats=d;}catch(e){}
    this.modal(`
      <div class="mh"><span class="mt">⚙️ Admin Panel</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb">
        <div class="stats">
          <div class="stat"><div class="stat-v">${stats.total_products||0}</div><div class="stat-l">Products</div></div>
          <div class="stat"><div class="stat-v">${stats.total_orders||0}</div><div class="stat-l">Orders</div></div>
          <div class="stat"><div class="stat-v">${stats.total_codes||0}</div><div class="stat-l">Codes</div></div>
          <div class="stat"><div class="stat-v">${stats.total_users||0}</div><div class="stat-l">Users</div></div>
          <div class="stat"><div class="stat-v" style="color:var(--red)">${stats.pending_orders||0}</div><div class="stat-l">Pending</div></div>
          <div class="stat"><div class="stat-v" style="color:var(--green)">$${parseFloat(stats.revenue||0).toFixed(0)}</div><div class="stat-l">Revenue</div></div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <button class="btn btn-primary" onclick="A.cls();A.adminUpload()">📤 Upload Codes</button>
          <button class="btn btn-sec" onclick="A.cls();A.adminOrders()">📋 Orders</button>
          <button class="btn btn-sec" onclick="A.cls();A.adminProds()">🎮 Products</button>
          <button class="btn btn-sec" onclick="A.cls();A.adminSupport()">💬 Support</button>
          <button class="btn btn-sec" onclick="A.cls();A.adminUsers()">👥 Users</button>
        </div>
      </div>`,true);
  },

  adminUpload(){
    this.modal(`
      <div class="mh"><span class="mt">📤 Upload Codes</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb">
        <div class="fdrop" id="fdrop" onclick="document.getElementById('ffile').click()">
          <div style="font-size:32px;margin-bottom:8px">📁</div>
          <div style="font-size:14px;font-weight:700;margin-bottom:4px">Drop codes.txt here</div>
          <input type="file" id="ffile" accept=".txt" style="display:none" onchange="A.handleFile(this)">
        </div>
        <div id="upPrev" style="margin-top:14px"></div>
      </div>`,true);
  },

  handleFile(inp){if(inp.files[0])this.procFile(inp.files[0]);},

  async procFile(file){
    const prev=document.getElementById('upPrev'); prev.innerHTML='<div style="color:var(--txt2);text-align:center;padding:10px">⏳ Processing…</div>';
    const fd=new FormData(); fd.append('file',file);
    try{
      const d=await(await fetch('/api/admin/upload/parse',{method:'POST',body:fd})).json();
      if(d.error){prev.innerHTML=`<div style="color:var(--red)">${this.esc(d.error)}</div>`;return;}
      prev.innerHTML=`
        <div class="card2" style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div><div style="font-size:13px;font-weight:700">${this.esc(d.game.emoji)} ${this.esc(d.game.name)}</div>
              <div style="font-size:11px;color:var(--txt3)">${d.total_codes} codes · ${d.dupes_removed} duplicates</div></div>
            <span class="badge bg-green">${d.total_codes}</span>
          </div>
        </div>
        <div class="fg"><label class="fl">Product Name</label><input class="fi" id="upName" value="${this.esc(d.game.name+' Code')}"></div>
        <div class="fg"><label class="fl">Price per Code ($)</label><input class="fi" type="number" id="upPrice" placeholder="0.00" step="0.01" min="0"></div>
        <div class="fg"><label class="fl">Description</label><textarea class="fi" id="upDesc" rows="2">${this.esc(d.game.description)}</textarea></div>
        <button class="btn btn-primary btn-block" onclick="A.confirmUp('${d.batch_id}','active')">✅ List for Sale</button>`;
    }catch(e){prev.innerHTML=`<div style="color:var(--red)">Error: ${e.message}</div>`;}
  },

  async confirmUp(bid,status){
    const name=document.getElementById('upName')?.value||'Game Code';
    const price=parseFloat(document.getElementById('upPrice')?.value)||0;
    const desc=document.getElementById('upDesc')?.value||'';
    try{
      const d=await(await fetch('/api/admin/upload/confirm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({batch_id:bid,name,price,description:desc,status})})).json();
      if(d.error){this.toast(d.error,'err');return;}
      this.cls(); this.toast(`${d.count} codes listed! 🎉`,'ok'); this.loadProds();
    }catch(e){this.toast('Upload failed','err');}
  },

  async adminProds(){
    const d=await(await fetch('/api/admin/products')).json();
    const ps=d.products||[];
    this.modal(`
      <div class="mh"><span class="mt">🎮 Products (${ps.length})</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb">
        ${ps.map(p=>`
          <div class="card" style="margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
              <div style="flex:1;min-width:0">
                <div style="font-size:13px;font-weight:700">${this.esc(p.game_emoji||'🎮')} ${this.esc(p.name)}</div>
                <div style="font-size:11px;color:var(--txt3)">${p.stock} codes · $${parseFloat(p.price).toFixed(2)}</div>
              </div>
              <div style="display:flex;gap:6px;align-items:center;flex-shrink:0">
                <button class="btn btn-sec btn-sm" onclick="A.editProd(${p.id},'${this.esc(p.name)}',${p.price},'${this.esc(p.description||'')}',${p.stock},'${p.status}')">✏️ Edit</button>
              </div>
            </div>
          </div>`).join('')||'<div class="empty"><span class="empty-i">🎮</span><div class="empty-t">No products</div></div>'}
      </div>`,true);
  },

  editProd(id, name, price, desc, stock, status) {
    this.modal(`
      <div class="mh"><span class="mt">✏️ Edit Product</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb">
        <div class="fg"><label class="fl">Product Name</label><input class="fi" id="epName" value="${this.esc(name)}"></div>
        <div class="fg"><label class="fl">Price ($)</label><input class="fi" type="number" id="epPrice" value="${price}" step="0.01" min="0"></div>
        <div class="fg"><label class="fl">Description</label><textarea class="fi" id="epDesc" rows="3">${this.esc(desc)}</textarea></div>
        <div class="fg"><label class="fl">Status</label>
          <select class="fi" id="epStatus">
            <option value="active" ${status==='active'?'selected':''}>Active (Visible)</option>
            <option value="inactive" ${status==='inactive'?'selected':''}>Hidden</option>
          </select>
        </div>
        <button class="btn btn-primary btn-block" onclick="A.saveEditProd(${id})">Save Changes</button>
        <p style="font-size:11px;color:var(--txt3);text-align:center;margin-top:10px">Note: This product has ${stock} available codes.</p>
      </div>`,true);
  },

  async saveEditProd(id) {
    const name = document.getElementById('epName').value;
    const price = document.getElementById('epPrice').value;
    const description = document.getElementById('epDesc').value;
    const status = document.getElementById('epStatus').value;
    await fetch('/api/admin/products/'+id, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,price,description,status})});
    this.toast('Product updated','ok'); this.cls(); this.adminProds(); this.loadProds();
  },

  async adminOrders(){
    const d=await(await fetch('/api/admin/orders')).json();
    const os=d.orders||[];
    this.modal(`
      <div class="mh"><span class="mt">📋 Orders (${os.length})</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb" style="padding:12px">
        ${os.length?`<div class="tbl-wrap"><table class="tbl">
          <thead><tr><th>ID</th><th>User</th><th>Total</th><th>Status</th></tr></thead>
          <tbody>${os.map(o=>`<tr>
            <td style="font-weight:700">#${o.id}</td><td>${this.esc(o.username||'')}</td>
            <td style="color:var(--acc);font-weight:700">$${parseFloat(o.total).toFixed(2)}</td>
            <td><select onchange="A.updOrd(${o.id},this.value)" style="background:var(--s2);border:1px solid var(--border);color:var(--txt);border-radius:5px;padding:4px;font-size:11px">
              ${['pending','processing','completed','delivered','cancelled'].map(s=>`<option${o.status===s?' selected':''}>${s}</option>`).join('')}
            </select></td>
          </tr>`).join('')}</tbody></table></div>`:'<div class="empty"><span class="empty-i">📦</span><div class="empty-t">No orders</div></div>'}
      </div>`,true);
  },

  async updOrd(id,status){
    await fetch('/api/admin/orders/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
    this.toast('Order updated','ok');
  },

  async adminSupport(){
    const d=await(await fetch('/api/admin/support')).json();
    const cs=d.conversations||[];
    this.modal(`
      <div class="mh"><span class="mt">💬 Support Chats</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb">
        ${cs.map(c=>`
          <div class="oitem" onclick="A.adminConv('${c.conv_id}','${this.esc(c.username)}')">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
              <div style="font-size:14px;font-weight:700">👤 ${this.esc(c.username)}</div>
              ${c.unread>0?`<span class="badge bg-red">${c.unread} new</span>`:''}
            </div>
            <div style="font-size:12px;color:var(--txt2)">${this.esc(c.last_message||'')}</div>
          </div>`).join('')||'<div class="empty"><span class="empty-i">💬</span><div class="empty-t">No conversations</div></div>'}
      </div>`,true);
  },

  async adminConv(cid,uname){
    this._adminConv=cid; this._adminUser=uname;
    const d=await(await fetch('/api/admin/support/'+cid)).json();
    const msgs=d.messages||[];
    this.modal(`
      <div class="mh"><span class="mt">💬 ${this.esc(uname)}</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div style="height:360px;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px" id="aConvMsgs">
        ${msgs.map(m=>{const mine=m.sender_role!=='customer';return`<div style="align-self:${mine?'flex-end':'flex-start'};max-width:82%"><div class="cmsg ${mine?'mine':'theirs'}">${this.esc(m.message)}</div></div>`}).join('')}
      </div>
      <div style="padding:12px;border-top:1px solid var(--border);display:flex;gap:8px">
        <input class="fi" id="aRepIn" placeholder="Reply…" onkeypress="if(event.key==='Enter')A.adminReply()">
        <button class="btn btn-primary" onclick="A.adminReply()">Send</button>
      </div>`,true);
    const m=document.getElementById('aConvMsgs'); if(m)m.scrollTop=m.scrollHeight;
  },

  async adminReply(){
    const msg=document.getElementById('aRepIn')?.value.trim();
    if(!msg||!this._adminConv)return;
    await fetch('/api/admin/support/'+this._adminConv+'/reply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    this.adminConv(this._adminConv,this._adminUser);
  },

  async adminUsers(){
    const d=await(await fetch('/api/admin/users')).json();
    const us=d.users||[];
    this.modal(`
      <div class="mh"><span class="mt">👥 Users (${us.length})</span><button class="mx" onclick="A.cls()">✕</button></div>
      <div class="mb" style="padding:12px">
        <div class="tbl-wrap"><table class="tbl">
          <thead><tr><th>User</th><th>Role</th><th>Orders</th></tr></thead>
          <tbody>${us.map(u=>`<tr><td style="font-weight:700">${this.esc(u.username)}</td><td><span class="badge bg-gold">${u.role}</span></td><td>${u.order_count||0}</td></tr>`).join('')}</tbody>
        </table></div>
      </div>`,true);
  },

  modal(html, center=false){
    const ov=document.createElement('div'); ov.className='overlay'+(center?' center':''); ov.id='mo'; ov.onclick=e=>{if(e.target===ov)A.cls();};
    const m=document.createElement('div'); m.className='modal'+(center?' center':''); m.innerHTML=html; ov.appendChild(m);
    document.getElementById('mc').appendChild(ov);
  },

  cls(){document.getElementById('mo')?.remove();},

  toast(msg,type='info'){
    const ico={ok:'✅',err:'❌',info:'ℹ️'};
    const el=document.createElement('div'); el.className='toast '+type; el.innerHTML=`<span>${ico[type]}</span><span>${this.esc(msg)}</span>`;
    document.getElementById('toasts').appendChild(el);
    setTimeout(()=>el.style.opacity='0',3500); setTimeout(()=>el.remove(),3800);
  },

  esc(s){const d=document.createElement('div');d.textContent=String(s||'');return d.innerHTML;},
  copy(txt,el){ navigator.clipboard?.writeText(txt).then(()=>{ el.textContent='✅ Copied!'; setTimeout(()=>el.textContent=txt,1500); }); this.toast('Code copied!','ok'); }
};

window.addEventListener('DOMContentLoaded', ()=>A.init());
</script>
</body>
</html>"""

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    threading.Thread(target=_backup_scheduler, daemon=True).start()
    print("\n" + "═"*46)
    print("  🎮  JCN XBOX CODES SHOP  —  RUNNING")
    print("═"*46)
    print("  URL  ▶  http://localhost:5000")
    print("  Admin ▶  owner / admin@123")
    print("═"*46 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False)