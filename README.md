# LabLend - Sistem Peminjaman Peralatan Laboratorium

Aplikasi web (frontend + backend REST API) untuk mata kuliah Komputasi Awan dan Terdistribusi (Tugas 9-15).
Tanpa database: data disimpan sebagai list of dict di memori backend dan kembali ke data awal saat server restart.

## Struktur
```
backend/app.py     REST API Flask (CRUD, auth, validasi)
frontend/          HTML, CSS, JS murni + config.js (alamat API dan profil tim)
deploy/            Skrip dan konfigurasi untuk EC2, Nginx, systemd, ALB, ASG
.env.example       Contoh konfigurasi (salin menjadi .env)
requirements.txt   Dependensi Python
```

## Peta tugas
| Tugas | Kebutuhan | Letak di proyek |
|---|---|---|
| 9 | CRUD 3 entitas, tanpa database, frontend + backend | `backend/app.py`, `frontend/` |
| 10 | Fitur Dashboard, Register, Login | halaman `#dashboard`, `#register`, `#login`; endpoint `/api/auth/*` |
| 11 | Kode di GitHub, komunikasi HTTP, skrip bash di Linux | bagian Git di bawah, `deploy/info-sistem.sh` |
| 12 | Frontend di Vercel + halaman profil anggota | `frontend/` (Root Directory di Vercel), halaman `#profil` (isi `MEMBERS` di `config.js`) |
| 13 | Twelve-factor: codebase, dependencies, config | satu repo Git, `requirements.txt` (versi dipatok), `.env` / `.env.example`, `frontend/config.js` |
| 14 | Apache2, Nginx frontend, backend di EC2, security group | `deploy/setup-frontend.sh`, `deploy/setup-backend.sh`, `deploy/*.conf`, `deploy/*.service` |
| 15 | ALB dan Auto Scaling Group | `deploy/alb-user-data.sh`, `deploy/asg-schedule.sh` |

## Menjalankan di localhost
```
cd lablend
python -m venv venv
venv\Scripts\activate          # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # Linux/Mac: cp .env.example .env
python backend/app.py
```
Buka http://localhost:5000. Akun bawaan: `admin` / `admin123` (atau daftar lewat halaman Register).

## Konfigurasi (.env)
`PORT`, `FLASK_DEBUG`, `SECRET_KEY` (wajib sama di semua instance), `CORS_ORIGINS`, `TOKEN_TTL_HOURS`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`.
Di frontend, `frontend/config.js` berisi `API_BASE` (kosong = backend satu alamat; isi URL backend jika dipisah) dan daftar `MEMBERS`.

## Autentikasi
Semua endpoint `/api/*` kecuali `/api/health`, `/api/auth/login`, `/api/auth/register` memerlukan header `Authorization: Bearer <token>`.
Token bertanda tangan (stateless), jadi valid di semua instance selama `SECRET_KEY` sama. Data akun tetap di memori per instance.

## Endpoint API
| Entitas | Create | Read | Update | Delete |
|---|---|---|---|---|
| Mahasiswa | POST /api/mahasiswa | GET /api/mahasiswa, /api/mahasiswa/{id} | PUT /api/mahasiswa/{id} | DELETE /api/mahasiswa/{id} |
| Peralatan | POST /api/peralatan | GET /api/peralatan?q=&kategori=&tersedia=1, /api/peralatan/{id} | PUT /api/peralatan/{id} | DELETE /api/peralatan/{id} |
| Peminjaman | POST /api/peminjaman | GET /api/peminjaman?status=, /api/peminjaman/{id} | PUT /api/peminjaman/{id} | DELETE /api/peminjaman/{id} |

Lintas entitas: `POST /api/peminjaman/{id}/kembali`, `GET /api/mahasiswa/{id}/riwayat`, `GET /api/peminjaman/terlambat`, `GET /api/dashboard`, `GET /api/peralatan/kategori`, `GET /api/health`.
Auth: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`.

## Git / GitHub (Tugas 11 dan 13)
```
git init && git add . && git commit -m "LabLend"
git branch -M main
git remote add origin https://github.com/USER/lablend.git
git push -u origin main
```

## Deploy
**Vercel (Tugas 12):** import repo, set *Root Directory* = `frontend`, tanpa build command. Isi `API_BASE` di `frontend/config.js` dengan URL backend publik, lalu push.

**EC2 (Tugas 14):** pakai Ubuntu. Security group: backend buka port 5000, frontend buka port 80, keduanya port 22 untuk SSH.
```
# EC2 backend
bash deploy/setup-backend.sh https://github.com/USER/lablend.git
# EC2 frontend
bash deploy/setup-frontend.sh https://github.com/USER/lablend.git http://<public-dns-backend>:5000
```
Cek status: `systemctl status lablend-backend` dan `systemctl status nginx`.

**ALB dan ASG (Tugas 15):** tempel `deploy/alb-user-data.sh` ke User data (Launch Template atau EC2), minimal 2 instance di 2 Availability Zone. Penjadwalan ASG: `bash deploy/asg-schedule.sh <nama-asg> <waktu-UTC>`.

## Catatan penting
Data memori hidup per proses. Di belakang load balancer dengan banyak instance, tiap instance punya data sendiri. Gunicorn dijalankan 1 worker agar data satu proses tetap konsisten. Untuk produksi nyata, data perlu dipindah ke database (tidak diizinkan di tugas ini).
