# 🏥 Local E-Rekam Medis yaqin

Aplikasi rekam medis elektronik (ERM) lokal berbasis desktop untuk praktik mandiri dokter. Dibuat dengan Python + CustomTkinter, mendukung input suara (voice-to-text), penyimpanan SQLite, lampiran penunjang, dan export PDF.

> **Author:** [@yaqinkdr](https://github.com/yaqinkdr)
> **Year:** 2026

---

## ✨ Fitur

- 📋 **Manajemen Pasien** — Tambah, cari, dan pilih pasien berdasarkan nomor ERM
- 📝 **SOAP Notes** — Subjektif, Objektif, Assessment, Plan dengan placeholder otomatis
- 🩺 **Nilai Normal O** — Template pemeriksaan fisik standar (GCS, KU, Thorax, Cor, dll) siap edit
- 🎤 **Voice Input** — Tahan tombol mic untuk dikte S menggunakan **faster-whisper** (offline, akurat)
- 📎 **Penunjang** — Lampirkan file (foto, lab, PDF) dan kaitkan ke SOAP terkait
- 📄 **Export PDF** — Cetak riwayat pasien lengkap dengan header praktik + kolom tanda tangan + nomor halaman
- 💾 **SQLite Storage** — Data tersimpan lokal, aman, tanpa server
- 🔄 **Auto-migrasi** — Otomatis migrasi dari `patients.json` lama (jika ada)
- 🖱️ **Clickable Penunjang** — Label penunjang di riwayat bisa diklik untuk membuka file

---

## 📸 Tampilan

_(tambahkan screenshot di sini, misalnya:)_
```
![Screenshot Aplikasi](docs/screenshot.png)
```

---

## 🚀 Instalasi

### 1. Clone repository

```bash
git clone https://github.com/yaqinkdr/local-erm.git
cd local-erm
```

### 2. (Opsional) Buat virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install customtkinter reportlab faster-whisper sounddevice numpy
```

**Catatan:**
- `sqlite3` dan `tkinter` sudah bawaan Python — tidak perlu install.
- `sounddevice` memerlukan **PortAudio** (biasanya sudah terbawa saat `pip install` di Windows).
- `faster-whisper` memerlukan **FFmpeg** — [unduh di sini](https://ffmpeg.org/download.html) dan tambahkan ke PATH jika belum ada.

### 4. Jalankan

```bash
python erm_baru.py
```

Saat pertama kali menggunakan fitur voice, model Whisper (`small`) akan diunduh otomatis (~500 MB) dan di-cache di `~/.cache/huggingface/`.

---

## 🎤 Voice Input (Opsional)

Untuk menghindari rate limit saat mengunduh model Whisper, set **Hugging Face Token** (gratis):

1. Buat token di https://huggingface.co/settings/tokens (permission: **Read**)
2. Set sebagai environment variable:

**Windows (permanent):**
```powershell
[System.Environment]::SetEnvironmentVariable('HF_TOKEN', 'hf_xxxxxxxxxx', 'User')
```

**Linux/macOS:**
```bash
export HF_TOKEN=hf_xxxxxxxxxx
```

> ⚠️ **Jangan hardcode token di source code**. Gunakan environment variable.

### Cara pakai
- **Tahan** tombol 🎤 di samping textbox Subjektif → mulai rekam
- **Lepas** tombol → Whisper transkripsi otomatis dan masukkan ke S

---

## 📂 Struktur Data

```
local-erm/
├── erm_baru.py            # File utama aplikasi
├── patients.db            # Database SQLite (dibuat otomatis)
├── penunjang/             # Folder lampiran penunjang
│   ├── 12345_20261005_073512.jpg
│   └── ...
└── README.md
```

### Skema Database

**Tabel `patients`**
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | TEXT | Nomor ERM (primary key) |
| name | TEXT | Nama pasien |

**Tabel `soap`**
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | INTEGER | Auto increment |
| patient_id | TEXT | FK ke patients.id |
| time | TEXT | Timestamp |
| provider | TEXT | Nama pemberi asuhan |
| s, o, a, p | TEXT | Isi SOAP |

**Tabel `penunjang`**
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | INTEGER | Auto increment |
| patient_id | TEXT | FK ke patients.id |
| time | TEXT | Timestamp |
| label | TEXT | Label penunjang |
| file_path | TEXT | Path file lampiran |
| soap_id | INTEGER | FK ke soap.id (nullable) |

---

## 🖨️ Export PDF

Klik tombol **📄 Export PDF** di panel kanan. PDF akan berisi:

- Header Praktek Mandiri dr. Achmad Nurul Yaqin + SIP + alamat
- Identitas pasien
- Riwayat SOAP (terbaru di atas)
- Daftar penunjang per SOAP
- Kolom tanda tangan pasien & dokter
- Nomor halaman otomatis

---

## ⌨️ Keyboard Shortcut

| Aksi | Shortcut |
|---|---|
| Fokus ke search | Klik langsung di kolom search |
| Rekam suara S | Tahan tombol 🎤 |
| Reset O ke normal | Klik tombol ↺ |

---

## 🛠️ Development

### Prasyarat
- Python 3.9+
- pip

### Menjalankan mode develop
```bash
python erm_baru.py
```

---

## 🐛 Known Issues

- Model Whisper default `small` mungkin lambat di CPU lama. Ganti ke `"base"` atau `"tiny"` di `_load_whisper()` untuk lebih cepat.
- Untuk transkripsi Indonesia, akurasi lebih baik pakai model `small` atau `medium`.
- Halusinasi Whisper ("Terima kasih", "Thanks for watching") bisa muncul saat audio kosong — sudah dimitigasi dengan `vad_filter=True`.

---

## 📜 Lisensi

MIT License — bebas digunakan dan dimodifikasi untuk keperluan pribadi maupun komersial.

---

## 🙏 Kredit

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — UI modern untuk Tkinter
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — Speech-to-text offline
- [ReportLab](https://www.reportlab.com/) — Pembuatan PDF
- [SoundDevice](https://python-sounddevice.readthedocs.io/) — Rekaman audio
- [NumPy](https://numpy.org/) — Pemrosesan array audio
- [Hugging Face Hub](https://huggingface.co/) — Distribusi model Whisper

---

## ⚠️ Disclaimer

Aplikasi ini adalah alat bantu administrasi praktik. **Bukan pengganti sistem rekam medis resmi** yang tersertifikasi. Data tersimpan lokal di komputer Anda — pastikan backup rutin dan jaga kerahasiaan data pasien sesuai peraturan yang berlaku (UU PDP, Kode Etik Kedokteran, dll).

---

⭐ Kalau repo ini bermanfaat, jangan lupa kasih star!
