const API = ((window.APP_CONFIG && APP_CONFIG.API_BASE) || "").replace(/\/$/, "") + "/api";
const store = {
  get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
  del: (k) => { try { localStorage.removeItem(k); } catch {} },
};
const getUser = () => { try { return JSON.parse(store.get("lablend_user") || "null"); } catch { return null; } };
function setSession(token, user) { store.set("lablend_token", token); store.set("lablend_user", JSON.stringify(user)); }
function logout() { store.del("lablend_token"); store.del("lablend_user"); location.hash = "#login"; route(); }
const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

async function api(path, method = "GET", body) {
  const headers = body ? {"Content-Type": "application/json"} : {};
  const token = store.get("lablend_token"); if (token) headers.Authorization = "Bearer " + token;
  let res;
  try { res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined }); }
  catch { throw new Error("Tidak dapat terhubung ke server. Periksa API_BASE di config.js dan pastikan backend menyala."); }
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && !path.startsWith("/auth/")) { logout(); throw new Error("Sesi berakhir, silakan masuk lagi"); }
  if (!res.ok) throw new Error(data.error || "Terjadi kesalahan");
  return data;
}
function toast(msg, isErr) {
  const t = $("#toast"); t.textContent = msg; t.className = "toast" + (isErr ? " error" : "");
  clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.add("hidden"), 3000);
}
const debounce = (fn, ms = 250) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
async function run(fn) { try { await fn(); } catch (e) { toast(e.message, true); } }

/* ---------- modal generic form ---------- */
function openForm(title, fields, values, onSubmit) {
  $("#modal-title").textContent = title;
  const f = $("#modal-form");
  f.innerHTML = fields.map(fd => {
    const v = values?.[fd.name] ?? fd.default ?? "";
    if (fd.type === "select")
      return `<label>${fd.label}<select name="${fd.name}" ${fd.disabled ? "disabled" : ""} required>${fd.options.map(o => `<option value="${esc(o.value)}" ${String(o.value) === String(v) ? "selected" : ""}>${esc(o.label)}</option>`).join("")}</select></label>`;
    return `<label>${fd.label}<input name="${fd.name}" type="${fd.type || "text"}" value="${esc(v)}" ${fd.required === false ? "" : "required"} ${fd.min !== undefined ? `min="${fd.min}"` : ""}></label>`;
  }).join("") + `<div class="modal-actions"><button type="button" id="m-cancel">Batal</button><button class="btn-primary" type="submit">Simpan</button></div>`;
  $("#modal").classList.remove("hidden");
  $("#m-cancel").onclick = closeForm;
  f.onsubmit = (e) => { e.preventDefault(); const btn = f.querySelector("[type=submit]"); btn.disabled = true; run(async () => {
    const data = {}; new FormData(f).forEach((val, k) => data[k] = val);
    fields.forEach(fd => { if (fd.disabled) data[fd.name] = values[fd.name]; });
    await onSubmit(data); closeForm();
  }).finally(() => { btn.disabled = false; }); };
}
function closeForm() { $("#modal").classList.add("hidden"); }
$("#modal").addEventListener("mousedown", (e) => { if (e.target.id === "modal") closeForm(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeForm(); });
const today = () => new Date().toISOString().slice(0, 10);
const plusDays = (n) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);

/* ---------- pages ---------- */
const pages = { dashboard, mahasiswa: pageMahasiswa, peralatan: pagePeralatan, peminjaman: pagePeminjaman, login: pageLogin, register: pageRegister, profil: pageProfil };

async function dashboard() {
  const d = await api("/dashboard");
  $("#content").innerHTML = `<h2>Ringkasan Peminjaman</h2>
  <div class="cards">
    <div class="card"><div class="num">${d.total_peralatan}</div>Total Unit Peralatan<br><small>(${d.jenis_peralatan} jenis)</small></div>
    <div class="card"><div class="num">${d.sedang_dipinjam}</div>Sedang Dipinjam</div>
    <div class="card warn"><div class="num">${d.terlambat}</div>Terlambat</div>
    <div class="card"><div class="num">${d.mahasiswa_aktif}</div>Mahasiswa Aktif<br><small>(dari ${d.total_mahasiswa})</small></div>
  </div>
  ${d.daftar_terlambat.length ? `<h3>Perlu Ditindaklanjuti (terlambat)</h3>${loanTable(d.daftar_terlambat, false)}` : ""}
  <h3>Peminjaman Terbaru</h3>${loanTable(d.terbaru, false)}`;
}

/* ---- Mahasiswa ---- */
async function pageMahasiswa() {
  $("#content").innerHTML = `<h2>Data Mahasiswa</h2>
  <div class="toolbar"><input id="q" placeholder="Cari nama / NIM..." size="28"><button class="btn-primary" id="add">+ Tambah Mahasiswa</button></div><div id="tbl"></div>`;
  const load = async () => {
    const rows = await api("/mahasiswa?q=" + encodeURIComponent($("#q").value));
    $("#tbl").innerHTML = rows.length ? `<table><tr><th>NIM</th><th>Nama</th><th>Prodi</th><th>Email</th><th>No. HP</th><th>Aksi</th></tr>${rows.map(m =>
      `<tr><td>${esc(m.nim)}</td><td>${esc(m.nama)}</td><td>${esc(m.prodi)}</td><td>${esc(m.email)}</td><td>${esc(m.no_hp)}</td>
      <td class="actions"><button class="btn-sm" data-r="${m.id}">Riwayat</button><button class="btn-sm" data-e="${m.id}">Edit</button><button class="btn-sm btn-danger" data-d="${m.id}">Hapus</button></td></tr>`).join("")}</table>` : `<div class="empty">Tidak ada data</div>`;
    $("#tbl").onclick = (ev) => { const b = ev.target.closest("button"); if (!b) return; const row = rows.find(x => x.id == (b.dataset.e || b.dataset.d || b.dataset.r));
      if (b.dataset.e) form(row); if (b.dataset.d) run(async () => { if (confirm(`Hapus ${row.nama}?`)) { await api("/mahasiswa/" + row.id, "DELETE"); toast("Mahasiswa dihapus"); load(); } });
      if (b.dataset.r) run(async () => showRiwayat(row)); };
  };
  const fields = [{name:"nim",label:"NIM"},{name:"nama",label:"Nama"},{name:"prodi",label:"Program Studi"},{name:"email",label:"Email",type:"email",required:false},{name:"no_hp",label:"No. HP",required:false}];
  const form = (m) => openForm(m ? "Edit Mahasiswa" : "Tambah Mahasiswa", fields, m, async (d) => {
    await api(m ? "/mahasiswa/" + m.id : "/mahasiswa", m ? "PUT" : "POST", d); toast("Data disimpan"); load(); });
  $("#add").onclick = () => form(); $("#q").oninput = debounce(() => run(load)); await load();
}
async function showRiwayat(m) {
  const rows = await api(`/mahasiswa/${m.id}/riwayat`);
  $("#modal-title").textContent = `Riwayat Peminjaman - ${m.nama}`;
  $("#modal-form").innerHTML = (rows.length ? `<table><tr><th>Peralatan</th><th>Jml</th><th>Pinjam</th><th>Status</th></tr>${rows.map(p => `<tr><td>${esc(p.peralatan_nama)}</td><td>${p.jumlah}</td><td>${p.tgl_pinjam}</td><td><span class="badge b-${p.status}">${p.status}</span></td></tr>`).join("")}</table>` : `<div class="empty">Belum ada peminjaman</div>`) + `<div class="modal-actions"><button type="button" id="m-cancel">Tutup</button></div>`;
  $("#modal").classList.remove("hidden"); $("#m-cancel").onclick = closeForm;
}

/* ---- Peralatan ---- */
async function pagePeralatan() {
  const all = await api("/peralatan"); const kats = [...new Set(all.map(e => e.kategori))];
  $("#content").innerHTML = `<h2>Daftar Peralatan</h2>
  <div class="toolbar"><input id="q" placeholder="Cari nama / kode..." size="26">
  <select id="kat"><option value="">Kategori: Semua</option>${kats.map(k => `<option>${esc(k)}</option>`).join("")}</select>
  <label><input type="checkbox" id="av"> hanya yang tersedia</label><button class="btn-primary" id="add">+ Tambah Peralatan</button></div><div id="tbl"></div>`;
  const load = async () => {
    const rows = await api(`/peralatan?q=${encodeURIComponent($("#q").value)}&kategori=${encodeURIComponent($("#kat").value)}&tersedia=${$("#av").checked ? 1 : 0}`);
    $("#tbl").innerHTML = rows.length ? `<table><tr><th>Kode</th><th>Nama</th><th>Kategori</th><th>Stok</th><th>Tersedia</th><th>Kondisi</th><th>Aksi</th></tr>${rows.map(e =>
      `<tr><td>${esc(e.kode)}</td><td>${esc(e.nama)}</td><td>${esc(e.kategori)}</td><td>${e.stok_total}</td><td>${e.stok_tersedia}</td><td>${esc(e.kondisi)}</td>
      <td class="actions"><button class="btn-sm" data-e="${e.id}">Edit</button><button class="btn-sm btn-danger" data-d="${e.id}">Hapus</button></td></tr>`).join("")}</table>` : `<div class="empty">Tidak ada data</div>`;
    $("#tbl").onclick = (ev) => { const b = ev.target.closest("button"); if (!b) return; const row = rows.find(x => x.id == (b.dataset.e || b.dataset.d));
      if (b.dataset.e) form(row); if (b.dataset.d) run(async () => { if (confirm(`Hapus ${row.nama}?`)) { await api("/peralatan/" + row.id, "DELETE"); toast("Peralatan dihapus"); pagePeralatan(); } }); };
  };
  const fields = [{name:"kode",label:"Kode"},{name:"nama",label:"Nama"},{name:"kategori",label:"Kategori"},{name:"stok_total",label:"Stok Total",type:"number",min:0},
    {name:"kondisi",label:"Kondisi",type:"select",options:["Baik","Rusak","Perawatan"].map(v => ({value:v,label:v}))}];
  const form = (e) => openForm(e ? "Edit Peralatan" : "Tambah Peralatan", fields, e, async (d) => {
    await api(e ? "/peralatan/" + e.id : "/peralatan", e ? "PUT" : "POST", d); toast("Data disimpan"); pagePeralatan(); });
  $("#add").onclick = () => form(); ["q", "kat", "av"].forEach(i => $("#" + i).oninput = debounce(() => run(load))); await load();
}

/* ---- Peminjaman ---- */
function loanTable(rows, withActions) {
  if (!rows.length) return `<div class="empty">Belum ada peminjaman. Catat peminjaman pertama lewat menu Peminjaman.</div>`;
  return `<table><tr><th>ID</th><th>Mahasiswa</th><th>Peralatan</th><th>Jml</th><th>Pinjam</th><th>Jatuh Tempo</th><th>Kembali</th><th>Status</th>${withActions ? "<th>Aksi</th>" : ""}</tr>${rows.map(p =>
    `<tr><td>LN-${String(p.id).padStart(2, "0")}</td><td>${esc(p.mahasiswa_nama)}<br><small>${esc(p.mahasiswa_nim)}</small></td><td>${esc(p.peralatan_nama)}</td><td>${p.jumlah}</td><td>${p.tgl_pinjam}</td><td>${p.tgl_jatuh_tempo}</td><td>${p.tgl_kembali || "-"}</td>
    <td><span class="badge b-${p.status}">${p.status}</span>${p.hari_terlambat ? `<br><small>${p.hari_terlambat} hari</small>` : ""}</td>${withActions ? `<td class="actions">${p.status !== "Dikembalikan" ? `<button class="btn-sm btn-primary" data-k="${p.id}">Kembalikan</button><button class="btn-sm" data-e="${p.id}">Edit</button>` : ""}<button class="btn-sm btn-danger" data-d="${p.id}">Hapus</button></td>` : ""}</tr>`).join("")}</table>`;
}
async function pagePeminjaman() {
  const [mhs, alat] = await Promise.all([api("/mahasiswa"), api("/peralatan")]);
  $("#content").innerHTML = `<h2>Peminjaman</h2>
  <div class="panel"><h3 style="margin-top:0">Form Peminjaman Baru</h3><form id="f" class="form-row">
    <label>Mahasiswa<select name="mahasiswa_id" required>${mhs.map(m => `<option value="${m.id}">${esc(m.nama)} (${esc(m.nim)})</option>`).join("")}</select></label>
    <label>Peralatan<select name="peralatan_id" required>${alat.map(e => `<option value="${e.id}" ${e.stok_tersedia < 1 || e.kondisi !== "Baik" ? "disabled" : ""}>${esc(e.nama)} - ${e.kondisi === "Baik" ? "tersedia " + e.stok_tersedia : esc(e.kondisi)}</option>`).join("")}</select></label>
    <label>Jumlah<input name="jumlah" type="number" min="1" value="1" style="width:80px" required></label>
    <label>Jatuh Tempo<input name="tgl_jatuh_tempo" type="date" min="${today()}" value="${plusDays(7)}" required></label>
    <button class="btn-primary" type="submit">Simpan Peminjaman</button></form></div>
  <div class="toolbar"><h3 style="margin:0">Riwayat Peminjaman</h3><select id="st"><option value="">Semua status</option><option>Dipinjam</option><option>Terlambat</option><option>Dikembalikan</option></select></div><div id="tbl"></div>`;
  $("#f").onsubmit = (e) => { e.preventDefault(); run(async () => { const d = Object.fromEntries(new FormData(e.target));
    await api("/peminjaman", "POST", d); toast("Peminjaman dicatat, stok diperbarui"); pagePeminjaman(); }); };
  const load = async () => {
    const rows = await api("/peminjaman?status=" + encodeURIComponent($("#st").value));
    $("#tbl").innerHTML = loanTable(rows, true);
    $("#tbl").onclick = (ev) => { const b = ev.target.closest("button"); if (!b) return;
      if (b.dataset.k) run(async () => { await api(`/peminjaman/${b.dataset.k}/kembali`, "POST"); toast("Peralatan dikembalikan"); pagePeminjaman(); });
      if (b.dataset.d) run(async () => { if (confirm("Hapus data peminjaman ini?")) { await api("/peminjaman/" + b.dataset.d, "DELETE"); toast("Peminjaman dihapus"); pagePeminjaman(); } });
      if (b.dataset.e) { const p = rows.find(x => x.id == b.dataset.e);
        openForm("Edit Peminjaman", [{name:"jumlah",label:"Jumlah",type:"number",min:1},{name:"tgl_jatuh_tempo",label:"Jatuh Tempo",type:"date"}], p,
          async (d) => { await api("/peminjaman/" + p.id, "PUT", d); toast("Peminjaman diperbarui"); pagePeminjaman(); }); } };
  };
  $("#st").onchange = () => run(load); await load();
}

/* ---- Auth & Profil ---- */
async function authenticate(path, body) { const r = await api(path, "POST", body); setSession(r.token, r.user); toast("Selamat datang, " + r.user.nama); location.hash = "#dashboard"; }
function pageLogin() {
  $("#content").innerHTML = `<div class="auth-box"><h2>Masuk ke LabLend</h2><form id="af">
    <label>Username<input name="username" required autofocus></label>
    <label>Password<input name="password" type="password" required></label>
    <button class="btn-primary" type="submit">Masuk</button></form>
    <p><small>Belum punya akun? <a href="#register">Daftar</a>. Lihat <a href="#profil">Profil Tim</a>.</small></p></div>`;
  $("#af").onsubmit = (e) => { e.preventDefault(); run(() => authenticate("/auth/login", Object.fromEntries(new FormData(e.target)))); };
}
function pageRegister() {
  $("#content").innerHTML = `<div class="auth-box"><h2>Daftar Akun</h2><form id="af">
    <label>Nama lengkap<input name="nama" required autofocus></label>
    <label>Username<input name="username" required minlength="3" maxlength="30"></label>
    <label>Password (min. 6 karakter)<input name="password" type="password" required minlength="6"></label>
    <button class="btn-primary" type="submit">Daftar</button></form>
    <p><small>Sudah punya akun? <a href="#login">Masuk</a></small></p></div>`;
  $("#af").onsubmit = (e) => { e.preventDefault(); run(() => authenticate("/auth/register", Object.fromEntries(new FormData(e.target)))); };
}
function pageProfil() {
  const c = window.APP_CONFIG || {}, ms = c.MEMBERS || [];
  $("#content").innerHTML = `<h2>Profil Tim</h2><p>Kelompok ${esc(c.KELOMPOK)} - ${esc(c.KELAS)}<br>${esc(c.MATKUL)}</p>
  <div class="cards">${ms.map(m => `<div class="card member"><div class="avatar">${esc(m.nama.split(" ").map(w => w[0]).slice(0, 2).join(""))}</div>
    <b>${esc(m.nama)}</b><br>${esc(m.nim)}<br><small>${esc(m.peran || "")}</small></div>`).join("")}</div>
  <p><small>Aplikasi: LabLend, sistem peminjaman peralatan laboratorium.</small></p>`;
}

/* ---------- router ---------- */
const PUBLIC_PAGES = ["login", "register", "profil"];
async function route() {
  const authed = !!store.get("lablend_token");
  let page = (location.hash || "#dashboard").slice(1); if (!pages[page]) page = "dashboard";
  if (!authed && !PUBLIC_PAGES.includes(page)) { location.hash = "#login"; return; }
  if (authed && (page === "login" || page === "register")) { location.hash = "#dashboard"; return; }
  document.body.classList.toggle("authed", authed);
  $("#user-name").textContent = authed ? (getUser()?.nama || "") : "";
  $("#logout").hidden = !authed;
  document.querySelectorAll(".sidebar a").forEach(a => a.classList.toggle("active", a.dataset.page === page));
  $("#page-title").textContent = "| " + ({profil: "Profil Tim"}[page] || page[0].toUpperCase() + page.slice(1));
  run(pages[page]);
}
window.addEventListener("hashchange", route);
$("#logout").onclick = logout;
route();
