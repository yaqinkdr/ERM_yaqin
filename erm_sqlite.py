import os
import sqlite3
import shutil
import datetime
import threading
import tempfile
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable
)
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)

# ============ VOICE INPUT (OPTIONAL) ============
# Install: pip install faster-whisper sounddevice numpy
try:
    import os
    print("Ganti token terlebih dahulu. Dapatkan token dengan login di https://huggingface.co/settings/tokens")
    #os.environ["HF_TOKEN"] = "tulis token Anda di sini"
    from faster_whisper import WhisperModel
    import sounddevice as sd
    import numpy as np
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

DB_FILE = "patients.db"

NORMAL_O = """GCS: E4 V5 M6 TD: 120/80 mmHg N: 70 x/m RR: 18 x/m Suhu: 36.6 °C Spo2: 99 %
K/L: a(-), i(-), c(-), d(-), pupil isokor 3 mm/3 mm, RC (+/+)
Tho: Simetris, retraksi (-)
Cor: S1-S2 normal, murmur (-), gallop (-)
Pul: Ves/Ves, ronkhi (-), wheezing (-)
Abd: BU (+), turgor baik, nyeri tekan (-)
Eks: Akral hangat, CRT < 2 detik, edema (-)"""

class EMedicalRecord(ctk.CTk):
    # ======================== EXPORT PDF ==============================
    def export_pdf(self):
        if not self.current_patient:
            messagebox.showwarning("Warning", "Pilih pasien dulu!")
            return

        cur = self.conn.cursor()
        cur.execute("SELECT name FROM patients WHERE id=?", (self.current_patient,))
        row = cur.fetchone()
        if not row:
            messagebox.showerror("Error", "Pasien tidak ditemukan.")
            return
        patient_name = row[0]
        pid = self.current_patient

        cur.execute(
            "SELECT id, time, provider, s, o, a, p FROM soap "
            "WHERE patient_id=? ORDER BY time DESC",
            (pid,)
        )
        soaps = cur.fetchall()

        if not soaps:
            messagebox.showinfo("Info", "Belum ada data SOAP untuk di-export.")
            return

        default_name = f"ERM_{patient_name.replace(' ', '_')}_{pid}.pdf"
        out_path = filedialog.asksaveasfilename(
            title="Simpan PDF",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF files", "*.pdf")]
        )
        if not out_path:
            return

        try:
            self._build_pdf(out_path, patient_name, pid, soaps)
            messagebox.showinfo("Sukses", f"PDF tersimpan:\n{out_path}")
            try:
                os.startfile(out_path)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Error", f"Gagal buat PDF: {e}")
    BULAN_ID = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]

    def _tgl_id(self):
        now = datetime.datetime.now()
        return f"{now.day} {self.BULAN_ID[now.month - 1]} {now.year}"
    def _build_pdf(self, out_path, patient_name, pid, soaps):
        doc = SimpleDocTemplate(
            out_path, pagesize=A4,
            leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=15 * mm, bottomMargin=20 * mm,
            title=f"E-Rekam Medis {patient_name}",
        )

        styles = getSampleStyleSheet()
        center = ParagraphStyle(
            "center", parent=styles["Normal"],
            alignment=TA_CENTER, fontName="Helvetica-Bold",
            fontSize=13, leading=16,
        )
        section = ParagraphStyle(
            "section", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=10,
            textColor=colors.HexColor("#1f6aa5"),
            spaceBefore=6, spaceAfter=2,
        )
        subtitle = ParagraphStyle(
            "subtitle", parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica",
            fontSize=9,                 
            leading=11,
            textColor=colors.black,
        )
        body = ParagraphStyle(
            "body", parent=styles["Normal"],
            fontName="Helvetica", fontSize=10, leading=13,
        )
        sign_style = ParagraphStyle(
            "sign", parent=styles["Normal"],
            fontName="Helvetica", fontSize=10,
            alignment=TA_CENTER, leading=14,
        )

        story = []

        # ============ KEPALA ============
        story.append(Paragraph("=" * 60, center))
        story.append(Paragraph("Praktek Mandiri dr. Achmad Nurul Yaqin", center))
        story.append(Paragraph("SIP (masih diurus)", center))
        story.append(Paragraph(
            "Jl. Alamat Saya, Kota Kediri <br/>"
            "WA: 0000-0000-0000 | Email: email_saya@email.com",
            subtitle
        ))
        story.append(Paragraph("=" * 60, center))
        story.append(Spacer(1, 6 * mm))

        # ============ IDENTITAS PASIEN ============
        story.append(Paragraph("IDENTITAS PASIEN", section))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#1f6aa5")))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"<b>Nama:</b> {patient_name}", body))
        story.append(Paragraph(f"<b>Nomor NIK:</b> {pid}", body))
        story.append(Paragraph(
            f"<b>Tanggal Cetak:</b> "
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            body
        ))
        story.append(Spacer(1, 5 * mm))

        # ============ RIWAYAT SOAP ============
        story.append(Paragraph("RIWAYAT PEMERIKSAAN (SOAP)", section))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#1f6aa5")))
        story.append(Spacer(1, 3 * mm))

        def esc(t):
            return (str(t or "")
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("\n", "<br/>"))

        for soap_id, time, provider, s, o, a, p in soaps:
            story.append(Paragraph(
                f"<b>{esc(time)}</b> &nbsp;—&nbsp; {esc(provider)}", body
            ))
            story.append(Spacer(1, 1 * mm))
            story.append(Paragraph(f"<b>S:</b> {esc(s)}", body))
            story.append(Paragraph(f"<b>O:</b> {esc(o)}", body))
            story.append(Paragraph(f"<b>A:</b> {esc(a)}", body))
            story.append(Paragraph(f"<b>P:</b> {esc(p)}", body))

            # Penunjang
            cur = self.conn.cursor()
            cur.execute(
                "SELECT label FROM penunjang "
                "WHERE patient_id=? AND soap_id=? ORDER BY time",
                (pid, soap_id)
            )
            pnjs = [r[0] for r in cur.fetchall()]
            if pnjs:
                story.append(Paragraph(
                    f"<b>Penunjang:</b> {esc(', '.join(pnjs))}", body
                ))

            story.append(Spacer(1, 2 * mm))
            story.append(HRFlowable(width="100%", thickness=0.3,
                                    color=colors.lightgrey))
            story.append(Spacer(1, 2 * mm))

        # ============ KOLOM TANDA TANGAN ============
        story.append(Spacer(1, 10 * mm))

        # Bikin tabel 2 kolom: kiri kosong (untuk pasien/keluarga), kanan dokter
        # Pakai Table dari platypus
        from reportlab.platypus import Table, TableStyle
        now_str = self._tgl_id()
        sig_left = Paragraph(
            "Pasien / Keluarga<br/><br/><br/><br/>"
            "(&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)", sign_style
        )
        sig_right = Paragraph(
            f"Kota Kediri, {now_str}<br/>Dokter Pemeriksa<br/><br/><br/><br/>"
            "<b>dr. Achmad Nurul Yaqin</b><br/>"
            "SIP (masih diurus)", sign_style
        )
        sig_table = Table(
            [[sig_left, sig_right]],
            colWidths=[doc.width * 0.5, doc.width * 0.5]
        )
        sig_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(sig_table)

        # ============ BUILD + NOMOR HALAMAN ============
        doc.build(
            story,
            onFirstPage=self._pdf_page_decorator,
            onLaterPages=self._pdf_page_decorator,
        )

    def _pdf_page_decorator(self, canvas, doc):
        """Gambar footer nomor halaman di setiap halaman."""
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        page_num = canvas.getPageNumber()
        text = f"Halaman {page_num}"
        canvas.drawCentredString(A4[0] / 2.0, 12 * mm, text)
        # garis tipis di atas footer
        canvas.setStrokeColor(colors.lightgrey)
        canvas.setLineWidth(0.3)
        canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
        canvas.restoreState()

    def __init__(self):
        super().__init__()

        self.title("E-Rekam Medis by yaqinkdr 2026")
        self.geometry("1200x600")

        # ---------- Storage ----------
        self.penunjang_folder = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "penunjang"
        )
        os.makedirs(self.penunjang_folder, exist_ok=True)
        self.init_db()
        self.migrate_json_if_exists()

        self.current_patient = None
        self.show_penunjang = False
        self.penunjang_frame = None

        # ---------- Voice ----------
        self.whisper_model = None
        self.recording = False
        self.audio_frames = []
        self.stream = None
        self.current_recording_button = None
        self.hold_timer = None  # timer untuk deteksi "tahan"

        # ---------- Layout ----------
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # === Kolom 1: Daftar Pasien ===
        self.column1 = ctk.CTkFrame(self)
        self.column1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.column1.grid_rowconfigure(2, weight=1)
        self.column1.grid_columnconfigure(0, weight=1)

        self.add_patient_button = ctk.CTkButton(
            self.column1, text="Tambah Pasien Baru", command=self.add_new_patient
        )
        self.add_patient_button.grid(row=0, column=0, padx=5, pady=(5, 5), sticky="ew")

        self.search_entry = ctk.CTkEntry(self.column1, placeholder_text="Search pasien...")
        self.search_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.update_patient_list)

        self.patient_listbox = tk.Listbox(
            self.column1, font=("Arial", 12),
            bg="#2b2b2b", fg="white", selectbackground="#1f6aa5"
        )
        self.patient_listbox.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        self.patient_listbox.bind("<<ListboxSelect>>", self.select_patient)

        self.update_patient_list()

        # === Kolom 2: Riwayat Pasien ===
        self.column2 = ctk.CTkFrame(self)
        self.column2.grid(row=0, column=1, padx=5, pady=10, sticky="nsew")
        self.column2.grid_rowconfigure(0, weight=1)
        self.column2.grid_columnconfigure(0, weight=1)

        self.history_text = ctk.CTkTextbox(self.column2, wrap="word")
        self.history_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.penunjang_button = ctk.CTkButton(
            self.column2, text="Tampilkan Penunjang", command=self.toggle_penunjang
        )
        self.penunjang_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        # === Kolom 3: Form Isian ===
        self.column3 = ctk.CTkFrame(self)
        self.column3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        self.column3.grid_rowconfigure((2, 3, 4, 5), weight=1)
        self.column3.grid_columnconfigure(0, weight=1)

        self.patient_info_label = ctk.CTkLabel(
            self.column3, text="Nama: - | NIK: - | Tanggal: -"
        )
        self.patient_info_label.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.provider_entry = ctk.CTkEntry(
            self.column3, placeholder_text="Nama Pemberi Asuhan"
        )
        self.provider_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        # ---- S dengan tombol mic (tahan) ----
        s_frame = ctk.CTkFrame(self.column3)
        s_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        s_frame.grid_columnconfigure(0, weight=1)
        s_frame.grid_rowconfigure(0, weight=1)

        self.s_text = ctk.CTkTextbox(s_frame, height=100, wrap="word")
        self.s_text.grid(row=0, column=0, sticky="nsew")

        self.mic_button = ctk.CTkButton(
            s_frame, text="🎤 Tahan untuk bicara (S)",
            width=90, fg_color="#444", hover_color="#666"
        )
        self.mic_button.grid(row=1, column=0, padx=2, pady=(2, 5), sticky="ew")
        self.mic_button.bind("<ButtonPress-1>", lambda e: self.start_recording(self.s_text))
        self.mic_button.bind("<ButtonRelease-1>", lambda e: self.stop_recording())

        # ---- O dengan tombol reset normal ----
        o_frame = ctk.CTkFrame(self.column3)
        o_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")
        o_frame.grid_columnconfigure(0, weight=1)
        o_frame.grid_rowconfigure(0, weight=1)

        self.o_text = ctk.CTkTextbox(o_frame, height=100, wrap="word")
        self.o_text.grid(row=0, column=0, sticky="nsew")

        self.o_reset_button = ctk.CTkButton(
            o_frame, text="↺ Isi Nilai Normal", width=90,
            fg_color="#444", hover_color="#666",
            command=self.fill_normal_o
        )
        self.o_reset_button.grid(row=1, column=0, padx=2, pady=(2, 5), sticky="ew")

        # ---- A ----
        self.a_text = ctk.CTkTextbox(self.column3, height=100, wrap="word")
        self.a_text.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")

        # ---- P ----
        self.p_text = ctk.CTkTextbox(self.column3, height=100, wrap="word")
        self.p_text.grid(row=5, column=0, padx=5, pady=5, sticky="nsew")

        # ---- Placeholder system ----
        self.placeholders = {
            self.s_text: "Subjektif...",
            self.o_text: NORMAL_O,
            self.a_text: "Assessment...",
            self.p_text: "Plan...",
        }
        self.placeholder_color = "gray"
        self.normal_color = "white" if ctk.get_appearance_mode() == "Dark" else "black"

        for tb, text in self.placeholders.items():
            tb.insert("0.0", text)
            tb.configure(text_color=self.placeholder_color)

            tb.bind("<FocusIn>", lambda e, t=tb: self._on_focus_in(t))
            tb.bind("<FocusOut>", lambda e, t=tb: self._on_focus_out(t))

        self.submit_button = ctk.CTkButton(
            self.column3, text="Submit SOAP", command=self.submit_soap
        )
        self.submit_button.grid(row=6, column=0, padx=5, pady=5, sticky="ew")
        self.export_button = ctk.CTkButton(
            self.column3, text="📄 Export PDF",
            command=self.export_pdf,
            fg_color="#2e7d32", hover_color="#1b5e20"
        )
        self.export_button.grid(row=9, column=0, padx=5, pady=5, sticky="ew")
        self.penunjang_label_entry = ctk.CTkEntry(
            self.column3, placeholder_text="Label Penunjang"
        )
        self.penunjang_label_entry.grid(row=7, column=0, padx=5, pady=5, sticky="ew")

        self.attach_button = ctk.CTkButton(
            self.column3, text="Lampirkan Penunjang", command=self.attach_penunjang
        )
        self.attach_button.grid(row=8, column=0, padx=5, pady=5, sticky="ew")

    # ==================================================================
    # =================== PLACEHOLDER HANDLER ==========================
    # ==================================================================
    def _on_focus_in(self, tb):
        if tb.get("0.0", "end-1c").strip() == self.placeholders[tb]:
            tb.delete("0.0", "end")
            tb.configure(text_color=self.normal_color)

    def _on_focus_out(self, tb):
        if not tb.get("0.0", "end-1c").strip():
            tb.insert("0.0", self.placeholders[tb])
            tb.configure(text_color=self.placeholder_color)

    def _get_text(self, tb):
        """Ambil text; kosongkan kalau masih placeholder."""
        val = tb.get("0.0", "end-1c").strip()
        if val == self.placeholders[tb]:
            return ""
        return val

    def fill_normal_o(self):
        """Isi ulang O dengan nilai normal."""
        self.o_text.delete("0.0", "end")
        self.o_text.insert("0.0", NORMAL_O)
        self.o_text.configure(text_color=self.normal_color)

    # ==================================================================
    # ========================= SQLITE =================================
    # ==================================================================
    def init_db(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS soap (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                time TEXT NOT NULL,
                provider TEXT,
                s TEXT, o TEXT, a TEXT, p TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS penunjang (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                time TEXT NOT NULL,
                label TEXT,
                file_path TEXT,
                soap_id INTEGER,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        """)
        self.conn.commit()

    def migrate_json_if_exists(self):
        """Migrasi otomatis dari patients.json lama kalau ada."""
        json_file = "patients.json"
        if not os.path.exists(json_file):
            return
        try:
            import json as _json
            with open(json_file, "r", encoding="utf-8") as f:
                data = _json.load(f)
            cur = self.conn.cursor()
            for pid, pdata in data.items():
                cur.execute(
                    "INSERT OR IGNORE INTO patients (id, name) VALUES (?, ?)",
                    (pid, pdata.get("name", "-"))
                )
                for e in pdata.get("soap_history", []):
                    cur.execute(
                        "INSERT INTO soap (patient_id, time, provider, s, o, a, p) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (pid, e["time"], e.get("provider", ""),
                         e.get("S", ""), e.get("O", ""), e.get("A", ""), e.get("P", ""))
                    )
                for e in pdata.get("penunjang", []):
                    cur.execute(
                        "INSERT INTO penunjang (patient_id, time, label, file_path) "
                        "VALUES (?, ?, ?, ?)",
                        (pid, e["time"], e.get("label", ""), e.get("file_path", ""))
                    )
            self.conn.commit()
            os.rename(json_file, json_file + ".migrated.bak")
            print("Migrasi dari patients.json selesai.")
        except Exception as e:
            print(f"Migrasi gagal: {e}")

    # ==================================================================
    # ======================= PATIENT LIST =============================
    # ==================================================================
    def update_patient_list(self, event=None):
        search_term = self.search_entry.get().lower()
        self.patient_listbox.delete(0, tk.END)
        cur = self.conn.cursor()
        cur.execute("SELECT id, name FROM patients ORDER BY name")
        for pid, name in cur.fetchall():
            if search_term in name.lower() or search_term in pid.lower():
                self.patient_listbox.insert(tk.END, f"{name} - {pid}")

    def add_new_patient(self):
        erm_id = simpledialog.askstring("Tambah Pasien", "Masukkan Nomor NIK:")
        if not erm_id:
            return
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM patients WHERE id=?", (erm_id,))
        if cur.fetchone():
            messagebox.showerror("Error", "Nomor NIK sudah ada!")
            return
        name = simpledialog.askstring("Tambah Pasien", "Masukkan Nama Pasien:")
        if not name:
            return
        cur.execute("INSERT INTO patients (id, name) VALUES (?, ?)",
                    (erm_id, name.strip()))
        self.conn.commit()
        self.update_patient_list()
        messagebox.showinfo("Sukses", f"Pasien {name} ({erm_id}) berhasil ditambahkan!")

    def select_patient(self, event):
        selection = self.patient_listbox.curselection()
        if not selection:
            return
        selected = self.patient_listbox.get(selection[0])
        pid = selected.split(" - ")[-1]
        self.current_patient = pid

        cur = self.conn.cursor()
        cur.execute("SELECT name FROM patients WHERE id=?", (pid,))
        row = cur.fetchone()
        name = row[0] if row else "-"

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.patient_info_label.configure(
            text=f"Nama: {name} | NIK: {pid} | Tanggal: {now}"
        )
        self.update_history()
        if self.show_penunjang:
            self.update_penunjang_list()

    # ==================================================================
    # ======================== HISTORY / SOAP ==========================
    # ==================================================================
    def update_history(self):
        if not self.current_patient:
            return
        self.history_text.delete("0.0", "end")

        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, time, provider, s, o, a, p FROM soap "
            "WHERE patient_id=? ORDER BY time DESC",
            (self.current_patient,)
        )
        rows = cur.fetchall()

        for soap_id, time, provider, s, o, a, p in rows:
            self.history_text.insert(
                "end",
                f"{time} - {provider}\nS: {s}\nO: {o}\nA: {a}\nP: {p}\n"
            )

            # --- PENUNJANG untuk SOAP ini ---
            cur.execute(
                "SELECT time, label, file_path FROM penunjang "
                "WHERE patient_id=? AND soap_id=? ORDER BY time",
                (self.current_patient, soap_id)
            )
            pnjs = cur.fetchall()
            if pnjs:
                self.history_text.insert("end", "Penunjang: ")

                # penunjang lama yang belum punya soap_id → anggap semua yang < soap tsb
                # (fallback: jika tidak ada soap_id sama sekali, ikut ini)
                for idx, (ptime, plabel, ppath) in enumerate(pnjs):
                    tag = f"pnj_{soap_id}_{idx}"
                    prefix = "" if idx == 0 else ", "
                    self.history_text.insert("end", f"{prefix}{plabel}", tag)
                    self.history_text.tag_config(tag, foreground="#4aa3ff", underline=True)
                    self.history_text.tag_bind(
                        tag, "<Button-1>",
                        lambda e, path=ppath: self.open_file(path)
                    )
                    self.history_text.tag_bind(
                        tag, "<Enter>",
                        lambda e: self.history_text.configure(cursor="hand2")
                    )
                    self.history_text.tag_bind(
                        tag, "<Leave>",
                        lambda e: self.history_text.configure(cursor="xterm")
                    )
                self.history_text.insert("end", "\n")

            self.history_text.insert("end", "\n")

    def submit_soap(self):
        if not self.current_patient:
            messagebox.showwarning("Warning", "Pilih pasien dulu!")
            return
        provider = self.provider_entry.get().strip()
        s = self._get_text(self.s_text)
        o = self._get_text(self.o_text)
        a = self._get_text(self.a_text)
        p = self._get_text(self.p_text)

        if not provider or not s or not o or not a or not p:
            messagebox.showwarning("Warning", "Isi semua field!")
            return

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO soap (patient_id, time, provider, s, o, a, p) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.current_patient, now, provider, s, o, a, p)
        )
        new_soap_id = cur.lastrowid

        # Kaitkan penunjang yang belum punya soap_id (yang dibuat sebelum submit)
        cur.execute(
            "UPDATE penunjang SET soap_id=? "
            "WHERE patient_id=? AND soap_id IS NULL",
            (new_soap_id, self.current_patient)
        )
        self.conn.commit()
        self.update_history()

        # reset field
        self.provider_entry.delete(0, "end")
        for tb in (self.s_text, self.o_text, self.a_text, self.p_text):
            tb.delete("0.0", "end")
            tb.insert("0.0", self.placeholders[tb])
            tb.configure(text_color=self.placeholder_color)

    # ==================================================================
    # ======================== PENUNJANG ===============================
    # ==================================================================
    def toggle_penunjang(self):
        self.show_penunjang = not self.show_penunjang
        if self.show_penunjang:
            self.penunjang_button.configure(text="Sembunyikan Penunjang")
            self.create_penunjang_frame()
            self.update_penunjang_list()
        else:
            self.penunjang_button.configure(text="Tampilkan Penunjang")
            if self.penunjang_frame:
                self.penunjang_frame.destroy()
                self.penunjang_frame = None

    def create_penunjang_frame(self):
        if self.penunjang_frame:
            self.penunjang_frame.destroy()
        self.penunjang_frame = ctk.CTkScrollableFrame(self.column2, height=200)
        self.penunjang_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        self.penunjang_frame.grid_columnconfigure(0, weight=1)

    def update_penunjang_list(self):
        if not self.current_patient or not self.penunjang_frame:
            return
        for widget in self.penunjang_frame.winfo_children():
            widget.destroy()

        cur = self.conn.cursor()
        cur.execute(
            "SELECT time, label, file_path FROM penunjang "
            "WHERE patient_id=? ORDER BY time DESC",
            (self.current_patient,)
        )
        rows = cur.fetchall()
        if not rows:
            ctk.CTkLabel(self.penunjang_frame, text="Belum ada penunjang.").grid(
                row=0, column=0, padx=5, pady=5, sticky="w"
            )
            return

        for i, (time, label, path) in enumerate(rows):
            lb = ctk.CTkLabel(
                self.penunjang_frame,
                text=f"{time} - {label} (Klik untuk buka)",
                text_color="#4aa3ff", cursor="hand2"
            )
            lb.grid(row=i, column=0, padx=5, pady=5, sticky="w")
            lb.bind("<Button-1>", lambda e, pp=path: self.open_file(pp))

    def attach_penunjang(self):
        if not self.current_patient:
            messagebox.showwarning("Warning", "Pilih pasien dulu!")
            return
        label = self.penunjang_label_entry.get().strip()
        if not label:
            messagebox.showwarning("Warning", "Isi label penunjang!")
            return
        file_path = filedialog.askopenfilename(title="Pilih File Penunjang")
        if not file_path:
            return
        now_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(file_path)[1]
        new_filename = f"{self.current_patient}_{now_file}{ext}"
        dest_path = os.path.join(self.penunjang_folder, new_filename)
        shutil.copy(file_path, dest_path)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO penunjang (patient_id, time, label, file_path) "
            "VALUES (?, ?, ?, ?)",
            (self.current_patient, now, label, dest_path)
        )
        self.conn.commit()
        self.penunjang_label_entry.delete(0, "end")
        if self.show_penunjang:
            self.update_penunjang_list()

    def open_file(self, path):
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal buka file: {e}")

    # ==================================================================
    # ======================== VOICE INPUT =============================
    # ==================================================================
    def _load_whisper(self):
        if self.whisper_model is None:
            # Model "small" cukup akurat & cepat di CPU.
            # Ganti ke "base" kalau CPU terlalu lambat.
            self.whisper_model = WhisperModel(
                "small", device="cpu", compute_type="int8"
            )
        return self.whisper_model

    def start_recording(self, textbox):
        if not VOICE_AVAILABLE:
            messagebox.showerror(
                "Fitur tidak tersedia",
                "Install dulu:\n pip install faster-whisper sounddevice numpy"
            )
            return
        self.recording = True
        self.audio_frames = []
        self.current_recording_button = textbox
        self.mic_button.configure(text="● Rekaman...", fg_color="#b00020")

        def callback(indata, frames, time_info, status):
            if self.recording:
                self.audio_frames.append(indata.copy())

        self.stream = sd.InputStream(
            samplerate=16000, channels=1, dtype="float32", callback=callback
        )
        self.stream.start()

    def stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        self.mic_button.configure(text="🎤 Tahan untuk bicara (S)", fg_color="#444")

        if not self.audio_frames:
            return

        audio = np.concatenate(self.audio_frames, axis=0).flatten()
        target = self.current_recording_button
        # proses di background supaya UI tidak freeze
        threading.Thread(
            target=self._transcribe_and_insert,
            args=(audio, target), daemon=True
        ).start()

    def _transcribe_and_insert(self, audio, textbox):
        try:
            model = self._load_whisper()
            segments, _ = model.transcribe(audio, language="id", beam_size=1)
            text = " ".join(seg.text.strip() for seg in segments).strip()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error Whisper", str(e)))
            return

        if not text:
            return

        def insert():
            # Kalau masih placeholder, hapus dulu
            if textbox.get("0.0", "end-1c").strip() == self.placeholders[textbox]:
                textbox.delete("0.0", "end")
                textbox.configure(text_color=self.normal_color)
            textbox.insert("end", text + " ")

        self.after(0, insert)


if __name__ == "__main__":
    app = EMedicalRecord()
    app.mainloop()