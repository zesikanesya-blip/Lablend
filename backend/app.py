"""LabLend - Sistem Peminjaman Peralatan Laboratorium (Backend REST API).

Tanpa database: seluruh data disimpan sebagai list of dict (JSON) di memori.
Data kembali ke kondisi awal setiap kali server di-restart.
"""
import os
from datetime import date, timedelta
import re
try:  # Twelve-factor: konfigurasi dari environment / file .env
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
except ImportError:
    pass
from flask import Flask, jsonify, request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"),
            static_url_path="")

# ----------------------------------------------------------------- CONFIG (dari environment)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-ganti-di-produksi")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
TOKEN_TTL = int(os.environ.get("TOKEN_TTL_HOURS", "12")) * 3600
signer = URLSafeTimedSerializer(SECRET_KEY)

# ----------------------------------------------------------------- DATA (hardcoded JSON/dict)
def _d(offset):
    return (date.today() + timedelta(days=offset)).isoformat()

mahasiswa = [
    {"id": 1, "nim": "1301223001", "nama": "Andi Pratama", "prodi": "Informatika", "email": "andi@student.telkomuniversity.ac.id", "no_hp": "081200000001"},
    {"id": 2, "nim": "1301223002", "nama": "Sari Wulandari", "prodi": "Informatika", "email": "sari@student.telkomuniversity.ac.id", "no_hp": "081200000002"},
    {"id": 3, "nim": "1301223003", "nama": "Budi Santoso", "prodi": "Sistem Informasi", "email": "budi@student.telkomuniversity.ac.id", "no_hp": "081200000003"},
    {"id": 4, "nim": "1301223004", "nama": "Dewi Lestari", "prodi": "Teknik Telekomunikasi", "email": "dewi@student.telkomuniversity.ac.id", "no_hp": "081200000004"},
]
peralatan = [
    {"id": 1, "kode": "EQ-001", "nama": "Arduino Uno", "kategori": "Mikrokontroler", "stok_total": 10, "stok_tersedia": 8, "kondisi": "Baik"},
    {"id": 2, "kode": "EQ-002", "nama": "Multimeter", "kategori": "Alat Ukur", "stok_total": 6, "stok_tersedia": 5, "kondisi": "Baik"},
    {"id": 3, "kode": "EQ-003", "nama": "Router Cisco", "kategori": "Jaringan", "stok_total": 4, "stok_tersedia": 3, "kondisi": "Baik"},
    {"id": 4, "kode": "EQ-004", "nama": "Raspberry Pi 4", "kategori": "Mikrokomputer", "stok_total": 5, "stok_tersedia": 5, "kondisi": "Baik"},
]
peminjaman = [
    {"id": 1, "mahasiswa_id": 1, "peralatan_id": 1, "jumlah": 2, "tgl_pinjam": _d(-3), "tgl_jatuh_tempo": _d(4), "tgl_kembali": None},
    {"id": 2, "mahasiswa_id": 2, "peralatan_id": 2, "jumlah": 1, "tgl_pinjam": _d(-10), "tgl_jatuh_tempo": _d(-3), "tgl_kembali": None},
    {"id": 3, "mahasiswa_id": 3, "peralatan_id": 3, "jumlah": 1, "tgl_pinjam": _d(-2), "tgl_jatuh_tempo": _d(5), "tgl_kembali": None},
    {"id": 4, "mahasiswa_id": 4, "peralatan_id": 4, "jumlah": 1, "tgl_pinjam": _d(-9), "tgl_jatuh_tempo": _d(-2), "tgl_kembali": _d(-3)},
]
_next = {"mahasiswa": 5, "peralatan": 5, "peminjaman": 5}
KONDISI = ("Baik", "Rusak", "Perawatan")
users = [{"id": 1, "nama": "Admin Lab", "username": os.environ.get("ADMIN_USERNAME", "admin"),
          "password_hash": generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123"))}]
_next["users"] = 2
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ----------------------------------------------------------------- HELPERS
def err(msg, code=400):
    return jsonify({"error": msg}), code

def find(coll, id_):
    return next((x for x in coll if x["id"] == id_), None)

def new_id(name):
    i = _next[name]; _next[name] += 1; return i

def status_of(p):
    if p["tgl_kembali"]:
        return "Dikembalikan"
    return "Terlambat" if p["tgl_jatuh_tempo"] < date.today().isoformat() else "Dipinjam"

def hari_terlambat(p):
    if p["tgl_kembali"] or p["tgl_jatuh_tempo"] >= date.today().isoformat(): return 0
    return (date.today() - date.fromisoformat(p["tgl_jatuh_tempo"])).days

def clean(d):
    """Trim spasi di semua nilai string."""
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in d.items()}

def bad_contact(d):
    if d.get("email") and not EMAIL_RE.match(d["email"]): return "Format email tidak valid"
    if d.get("no_hp") and not re.fullmatch(r"\+?\d{8,15}", d["no_hp"]): return "No. HP harus 8-15 digit angka"

def enrich(p):
    m, e = find(mahasiswa, p["mahasiswa_id"]), find(peralatan, p["peralatan_id"])
    return {**p, "status": status_of(p), "hari_terlambat": hari_terlambat(p),
            "mahasiswa_nama": m["nama"] if m else "(dihapus)",
            "mahasiswa_nim": m["nim"] if m else "-",
            "peralatan_nama": e["nama"] if e else "(dihapus)"}

def active_loans(key, id_):
    return [p for p in peminjaman if p[key] == id_ and not p["tgl_kembali"]]

def need(data, fields):
    miss = [f for f in fields if data.get(f) in (None, "")]
    return ("Field wajib diisi: " + ", ".join(miss)) if miss else None

def to_int(v):
    try: return int(v)
    except (TypeError, ValueError): return None

def valid_date(s):
    try: date.fromisoformat(s); return True
    except (TypeError, ValueError): return False

# ----------------------------------------------------------------- AUTH (token bertanda tangan, stateless)
OPEN_PATHS = {"/api/health", "/api/auth/login", "/api/auth/register"}

def public(u): return {"id": u["id"], "nama": u["nama"], "username": u["username"]}

def current_user():
    h = request.headers.get("Authorization", "")
    if not h.startswith("Bearer "): return None
    try: data = signer.loads(h[7:], max_age=TOKEN_TTL)
    except BadSignature: return None  # termasuk SignatureExpired
    return find(users, data.get("uid"))

@app.before_request
def guard():
    if request.method == "OPTIONS" or not request.path.startswith("/api/") or request.path in OPEN_PATHS: return
    if not current_user(): return err("Login diperlukan", 401)

@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"] = CORS_ORIGINS
    r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    r.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return r

def auth_body():
    raw = request.get_json(silent=True) or {}
    d = clean(raw); d["password"] = raw.get("password") or ""  # password tidak di-trim
    return d

@app.post("/api/auth/register")
def register():
    d = auth_body()
    e = need(d, ["nama", "username", "password"])
    if e: return err(e)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", d["username"]): return err("Username 3-30 karakter (huruf, angka, _ . -)")
    if len(d["password"]) < 6: return err("Password minimal 6 karakter")
    if any(u["username"].lower() == d["username"].lower() for u in users): return err("Username sudah dipakai", 409)
    u = {"id": new_id("users"), "nama": d["nama"], "username": d["username"], "password_hash": generate_password_hash(d["password"])}
    users.append(u)
    return jsonify({"token": signer.dumps({"uid": u["id"]}), "user": public(u)}), 201

@app.post("/api/auth/login")
def login():
    d = auth_body()
    u = next((x for x in users if x["username"].lower() == d.get("username", "").lower()), None)
    if not u or not check_password_hash(u["password_hash"], d["password"]): return err("Username atau password salah", 401)
    return jsonify({"token": signer.dumps({"uid": u["id"]}), "user": public(u)})

@app.get("/api/auth/me")
def me():
    return jsonify(public(current_user()))

@app.errorhandler(HTTPException)
def http_err(e):
    return err(e.description if e.code != 404 else "Endpoint tidak ditemukan", e.code)

@app.errorhandler(Exception)
def unexpected(e):
    app.logger.exception(e)
    return err("Terjadi kesalahan pada server", 500)

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "tanggal": date.today().isoformat()})

# ----------------------------------------------------------------- FRONTEND
@app.route("/")
def index():
    return app.send_static_file("index.html")

# ----------------------------------------------------------------- MAHASISWA (CRUD)
@app.get("/api/mahasiswa")
def mhs_list():
    q = request.args.get("q", "").lower()
    return jsonify([m for m in mahasiswa if q in m["nama"].lower() or q in m["nim"]])

@app.get("/api/mahasiswa/<int:id_>")
def mhs_get(id_):
    m = find(mahasiswa, id_)
    return jsonify(m) if m else err("Mahasiswa tidak ditemukan", 404)

@app.post("/api/mahasiswa")
def mhs_create():
    d = clean(request.get_json(silent=True) or {})
    e = need(d, ["nim", "nama", "prodi"]) or bad_contact(d)
    if e: return err(e)
    if any(m["nim"] == d["nim"] for m in mahasiswa): return err("NIM sudah terdaftar", 409)
    m = {"id": new_id("mahasiswa"), "nim": d["nim"], "nama": d["nama"], "prodi": d["prodi"],
         "email": d.get("email", ""), "no_hp": d.get("no_hp", "")}
    mahasiswa.append(m)
    return jsonify(m), 201

@app.put("/api/mahasiswa/<int:id_>")
def mhs_update(id_):
    m = find(mahasiswa, id_)
    if not m: return err("Mahasiswa tidak ditemukan", 404)
    d = clean(request.get_json(silent=True) or {})
    e = need({**m, **d}, ["nim", "nama", "prodi"]) or bad_contact(d)
    if e: return err(e)
    if any(x["nim"] == d.get("nim") and x["id"] != id_ for x in mahasiswa): return err("NIM sudah terdaftar", 409)
    for k in ("nim", "nama", "prodi", "email", "no_hp"):
        if k in d: m[k] = d[k]
    return jsonify(m)

@app.delete("/api/mahasiswa/<int:id_>")
def mhs_delete(id_):
    m = find(mahasiswa, id_)
    if not m: return err("Mahasiswa tidak ditemukan", 404)
    if active_loans("mahasiswa_id", id_): return err("Mahasiswa masih memiliki peminjaman aktif", 409)
    mahasiswa.remove(m)
    return jsonify({"message": "Mahasiswa dihapus"})

@app.get("/api/mahasiswa/<int:id_>/riwayat")
def mhs_riwayat(id_):
    if not find(mahasiswa, id_): return err("Mahasiswa tidak ditemukan", 404)
    return jsonify([enrich(p) for p in peminjaman if p["mahasiswa_id"] == id_])

# ----------------------------------------------------------------- PERALATAN (CRUD)
@app.get("/api/peralatan")
def alat_list():
    q = request.args.get("q", "").lower()
    kat = request.args.get("kategori", "")
    only = request.args.get("tersedia") in ("1", "true")
    res = [e for e in peralatan
           if (q in e["nama"].lower() or q in e["kode"].lower())
           and (not kat or e["kategori"] == kat)
           and (not only or e["stok_tersedia"] > 0)]
    return jsonify(res)

@app.get("/api/peralatan/kategori")
def alat_kategori():
    return jsonify(sorted({e["kategori"] for e in peralatan}))

@app.get("/api/peralatan/<int:id_>")
def alat_get(id_):
    e = find(peralatan, id_)
    return jsonify(e) if e else err("Peralatan tidak ditemukan", 404)

@app.post("/api/peralatan")
def alat_create():
    d = clean(request.get_json(silent=True) or {})
    e = need(d, ["kode", "nama", "kategori", "stok_total"])
    if e: return err(e)
    if d.get("kondisi", "Baik") not in KONDISI: return err("kondisi harus salah satu dari: " + ", ".join(KONDISI))
    st = to_int(d["stok_total"])
    if st is None or st < 0: return err("stok_total harus bilangan bulat >= 0")
    if any(x["kode"] == d["kode"] for x in peralatan): return err("Kode peralatan sudah ada", 409)
    item = {"id": new_id("peralatan"), "kode": d["kode"], "nama": d["nama"], "kategori": d["kategori"],
            "stok_total": st, "stok_tersedia": st, "kondisi": d.get("kondisi", "Baik")}
    peralatan.append(item)
    return jsonify(item), 201

@app.put("/api/peralatan/<int:id_>")
def alat_update(id_):
    item = find(peralatan, id_)
    if not item: return err("Peralatan tidak ditemukan", 404)
    d = clean(request.get_json(silent=True) or {})
    e = need({**item, **d}, ["kode", "nama", "kategori"])
    if e: return err(e)
    if d.get("kondisi", item["kondisi"]) not in KONDISI: return err("kondisi harus salah satu dari: " + ", ".join(KONDISI))
    if any(x["kode"] == d.get("kode") and x["id"] != id_ for x in peralatan): return err("Kode peralatan sudah ada", 409)
    if "stok_total" in d:
        st = to_int(d["stok_total"])
        if st is None or st < 0: return err("stok_total harus bilangan bulat >= 0")
        dipinjam = item["stok_total"] - item["stok_tersedia"]
        if st < dipinjam: return err(f"stok_total tidak boleh kurang dari jumlah yang sedang dipinjam ({dipinjam})", 409)
        item["stok_total"], item["stok_tersedia"] = st, st - dipinjam
    for k in ("kode", "nama", "kategori", "kondisi"):
        if k in d: item[k] = d[k]
    return jsonify(item)

@app.delete("/api/peralatan/<int:id_>")
def alat_delete(id_):
    item = find(peralatan, id_)
    if not item: return err("Peralatan tidak ditemukan", 404)
    if active_loans("peralatan_id", id_): return err("Peralatan masih dipinjam", 409)
    peralatan.remove(item)
    return jsonify({"message": "Peralatan dihapus"})

# ----------------------------------------------------------------- PEMINJAMAN (CRUD + fitur lintas entitas)
@app.get("/api/peminjaman")
def pin_list():
    st = request.args.get("status", "")
    res = [enrich(p) for p in peminjaman]
    if st: res = [p for p in res if p["status"] == st]
    return jsonify(sorted(res, key=lambda p: -p["id"]))

@app.get("/api/peminjaman/terlambat")
def pin_late():
    return jsonify([enrich(p) for p in peminjaman if status_of(p) == "Terlambat"])

@app.get("/api/peminjaman/<int:id_>")
def pin_get(id_):
    p = find(peminjaman, id_)
    return jsonify(enrich(p)) if p else err("Peminjaman tidak ditemukan", 404)

@app.post("/api/peminjaman")
def pin_create():
    d = request.get_json(silent=True) or {}
    e = need(d, ["mahasiswa_id", "peralatan_id", "jumlah", "tgl_jatuh_tempo"])
    if e: return err(e)
    mid, pid, jml = to_int(d["mahasiswa_id"]), to_int(d["peralatan_id"]), to_int(d["jumlah"])
    if not find(mahasiswa, mid): return err("Mahasiswa tidak ditemukan", 404)
    alat = find(peralatan, pid)
    if not alat: return err("Peralatan tidak ditemukan", 404)
    if jml is None or jml < 1: return err("jumlah minimal 1")
    tgl_pinjam = d.get("tgl_pinjam") or date.today().isoformat()
    if not valid_date(tgl_pinjam) or not valid_date(d["tgl_jatuh_tempo"]): return err("Format tanggal harus YYYY-MM-DD")
    if d["tgl_jatuh_tempo"] < tgl_pinjam: return err("Jatuh tempo tidak boleh sebelum tanggal pinjam")
    if alat["kondisi"] != "Baik": return err("Peralatan sedang tidak dalam kondisi Baik", 409)
    if jml > alat["stok_tersedia"]: return err(f"Stok tidak cukup (tersedia {alat['stok_tersedia']})", 409)
    alat["stok_tersedia"] -= jml
    p = {"id": new_id("peminjaman"), "mahasiswa_id": mid, "peralatan_id": pid, "jumlah": jml,
         "tgl_pinjam": tgl_pinjam, "tgl_jatuh_tempo": d["tgl_jatuh_tempo"], "tgl_kembali": None}
    peminjaman.append(p)
    return jsonify(enrich(p)), 201

@app.put("/api/peminjaman/<int:id_>")
def pin_update(id_):
    p = find(peminjaman, id_)
    if not p: return err("Peminjaman tidak ditemukan", 404)
    if p["tgl_kembali"]: return err("Peminjaman yang sudah dikembalikan tidak dapat diubah", 409)
    d = request.get_json(silent=True) or {}
    alat = find(peralatan, p["peralatan_id"])
    if "jumlah" in d:
        jml = to_int(d["jumlah"])
        if jml is None or jml < 1: return err("jumlah minimal 1")
        selisih = jml - p["jumlah"]
        if alat:
            if selisih > alat["stok_tersedia"]: return err(f"Stok tidak cukup (tersedia {alat['stok_tersedia']})", 409)
            alat["stok_tersedia"] -= selisih
        p["jumlah"] = jml
    if "tgl_jatuh_tempo" in d:
        if not valid_date(d["tgl_jatuh_tempo"]): return err("Format tanggal harus YYYY-MM-DD")
        if d["tgl_jatuh_tempo"] < p["tgl_pinjam"]: return err("Jatuh tempo tidak boleh sebelum tanggal pinjam")
        p["tgl_jatuh_tempo"] = d["tgl_jatuh_tempo"]
    return jsonify(enrich(p))

@app.post("/api/peminjaman/<int:id_>/kembali")
def pin_return(id_):
    p = find(peminjaman, id_)
    if not p: return err("Peminjaman tidak ditemukan", 404)
    if p["tgl_kembali"]: return err("Peralatan sudah dikembalikan", 409)
    p["tgl_kembali"] = date.today().isoformat()
    alat = find(peralatan, p["peralatan_id"])
    if alat: alat["stok_tersedia"] = min(alat["stok_total"], alat["stok_tersedia"] + p["jumlah"])
    return jsonify(enrich(p))

@app.delete("/api/peminjaman/<int:id_>")
def pin_delete(id_):
    p = find(peminjaman, id_)
    if not p: return err("Peminjaman tidak ditemukan", 404)
    if not p["tgl_kembali"]:  # batalkan peminjaman aktif -> stok dikembalikan
        alat = find(peralatan, p["peralatan_id"])
        if alat: alat["stok_tersedia"] = min(alat["stok_total"], alat["stok_tersedia"] + p["jumlah"])
    peminjaman.remove(p)
    return jsonify({"message": "Peminjaman dihapus"})

# ----------------------------------------------------------------- DASHBOARD
@app.get("/api/dashboard")
def dashboard():
    st = [status_of(p) for p in peminjaman]
    aktif_ids = {p["mahasiswa_id"] for p in peminjaman if not p["tgl_kembali"]}
    return jsonify({
        "total_peralatan": sum(e["stok_total"] for e in peralatan),
        "jenis_peralatan": len(peralatan),
        "sedang_dipinjam": st.count("Dipinjam") + st.count("Terlambat"),
        "terlambat": st.count("Terlambat"),
        "mahasiswa_aktif": len(aktif_ids),
        "total_mahasiswa": len(mahasiswa),
        "daftar_terlambat": sorted((enrich(p) for p in peminjaman if status_of(p) == "Terlambat"), key=lambda p: -p["hari_terlambat"]),
        "terbaru": [enrich(p) for p in sorted(peminjaman, key=lambda p: -p["id"])[:5]],
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG", "1") == "1")
