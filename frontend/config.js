// Konfigurasi frontend (Twelve-factor: config terpisah dari kode).
// API_BASE kosong = backend satu alamat dengan frontend (localhost).
// Saat frontend dan backend terpisah (Vercel / Nginx / EC2), isi dengan URL backend, contoh: http://ec2-1-2-3-4.compute.amazonaws.com:5000
window.APP_CONFIG = {
  API_BASE: "",
  KELOMPOK: "13",
  KELAS: "IF-48-02",
  MATKUL: "CAK3EAB3 Komputasi Awan dan Terdistribusi - Universitas Telkom",
  // Tugas 12: halaman Profil Tim membaca daftar ini. Lengkapi nama dan NIM seluruh anggota.
  MEMBERS: [
    { nama: "Zesika Neysa Alfara", nim: "103012400211", peran: "Anggota Kelompok 13" },
    { nama: "Nailah Dhiya Marzuqoh", nim: "103012400421", peran: "Anggota Kelompok 13" }
  ]
};
