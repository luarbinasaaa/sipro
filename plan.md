# Rencana Development SIPRO — Fase 48 (Pengadaan & Subkon Lanjutan)

> **STATUS 18 Agu 2026 — FASE 1 & 2 SELESAI, FASE 3 BERJALAN.**
> * **Pemulihan lingkungan — SELESAI**: repo GitHub `yataqwerva/sipro` dipulihkan ke container
>   ini; baseline lama diverifikasi ulang (33 gates PASS, `poc_47.py` PASS, `mutasi_47.py`
>   19/19 tertangkap).
> * **Penutupan Fase 47 — SELESAI**: E2E multi-peran (testing agent iterasi 71) tanpa bug;
>   temuan "panel absensi tidak ketemu" terbukti hanya URL uji salah (`/build?hub=lapangan`).
>   Satu cacat UX nyata diperbaiki: tombol "Simpan absensi" tetap aktif walau tidak ada
>   perubahan.
> * **FASE 1 (POC core Fase 48) — SELESAI**: `poc/poc_48.py` **PASS, 61 pemeriksaan hijau**
>   (vendor & harga, permintaan→PO, retur, 3-way MENAHAN, uang muka/potongan/retensi, stok,
>   evaluasi). Satu cacat nyata tertangkap POC: `maintenance_days = 0` diam-diam menjadi 90.
> * **FASE 2 (backend + frontend) — SELESAI**: 5 modul backend + 4 router baru + seed `fase48`
>   + layar di `/procurement` (6 tab), `/subcon` (6 tab), `/materials` (tab Kendali Stok) —
>   tanpa pintu sidebar baru.
> * **FASE 3 (guardrail + penutupan) — BERJALAN**: gate ke-34/35/36 hijau & terdaftar di
>   `run_all_gates.sh` → **OVERALL PASS (36 gates)**; `scripts/mutasi_48.py` (24 mutasi)
>   dijalankan; sisa: E2E testing agent multi-peran.

Problem statement (verbatim):# Rencana Development SIPRO — Fase 48 (Pengadaan & Subkon Lanjutan)

> **STATUS 18 Agu 2026 — FASE 1 & 2 SELESAI, FASE 3 BERJALAN.**
> * **Pemulihan lingkungan — SELESAI**: repo GitHub `yataqwerva/sipro` dipulihkan ke container
>   ini; baseline lama diverifikasi ulang (33 gates PASS, `poc_47.py` PASS, `mutasi_47.py`
>   19/19 tertangkap).
> * **Penutupan Fase 47 — SELESAI**: E2E multi-peran (testing agent iterasi 71) tanpa bug;
>   temuan "panel absensi tidak ketemu" terbukti hanya URL uji salah (`/build?hub=lapangan`).
>   Satu cacat UX nyata diperbaiki: tombol "Simpan absensi" tetap aktif walau tidak ada
>   perubahan.
> * **FASE 1 (POC core Fase 48) — SELESAI**: `poc/poc_48.py` **PASS, 61 pemeriksaan hijau**
>   (vendor & harga, permintaan→PO, retur, 3-way MENAHAN, uang muka/potongan/retensi, stok,
>   evaluasi). Satu cacat nyata tertangkap POC: `maintenance_days = 0` diam-diam menjadi 90.
> * **FASE 2 (backend + frontend) — SELESAI**: 5 modul backend + 4 router baru + seed `fase48`
>   + layar di `/procurement` (6 tab), `/subcon` (6 tab), `/materials` (tab Kendali Stok) —
>   tanpa pintu sidebar baru.
> * **FASE 3 (guardrail + penutupan) — BERJALAN**: gate ke-34/35/36 hijau & terdaftar di
>   `run_all_gates.sh` → **OVERALL PASS (36 gates)**; `scripts/mutasi_48.py` (24 mutasi)
>   dijalankan; sisa: E2E testing agent multi-peran.

> "saya ingin anda lanjutkan development dari repo ini https://github.com/yataqwerva/sipro"

---

## 1) Objectives
Membangun **Fase 48** (tanpa menambah pintu sidebar baru) untuk menutup lubang nyata yang terdeteksi audit API, dengan fokus pada 5 cakupan owner:
1. **Procurement end-to-end yang bisa dipertanggungjawabkan:** PR → PO → GRN (parsial) → retur → **3-way match yang MENAHAN** tagihan melebihi barang diterima/PO → hutang AP.
2. **Subkon lanjutan:** termin/opname sudah ada; tambah **uang muka, denda/potongan, retensi (daftar + pencairan bergerbang)**.
3. **Vendor master & price list:** master vendor (bukan teks bebas) + daftar harga sebagai pembanding PO.
4. **Evaluasi vendor/subkon berbukti:** skor dihitung dari bukti (ketepatan waktu, mutu/temuan, harga vs price list) dan **honest-null** bila belum ada data.
5. **Stok/gudang lebih lengkap:** transfer antar proyek, peringatan stok minimum/reorder, valuasi stok (rata-rata bergerak) + audit trail.

---

## 2) Implementation Steps

### FASE 1 — POC Core (WAJIB, SSOT + idempoten + reversible + tie-out)
**Output:** `poc/poc_48.py` hijau (exit 0). Semua fixture dibuat via API resmi (bertanda `poc48`) dan dibersihkan; tunggu antrean event/journal settle (ikuti pelajaran `scripts/_fixture47.py`) agar tidak meninggalkan jurnal menggantung.

**User stories (POC):**
1. Sebagai pelaksana, saya buat **PR**; jika stok kurang, sistem membuat **PO** dari PR **sekali saja** (idempoten, tidak dobel).
2. Sebagai gudang, saya terima barang bertahap (**GRN parsial**) dan bisa melakukan **retur**; stok & `received_value` turun sesuai retur.
3. Sebagai finance, sistem **MENAHAN** pembuatan/approval tagihan AP jika nilai tagihan kumulatif melebihi nilai diterima/PO (bukan hanya flagged).
4. Sebagai admin proyek, saya buat klaim termin subkon dengan **potongan uang muka + denda + retensi**; `net` = `gross - retention - deductions` dapat direkonstruksi.
5. Sebagai finance_manager, saya hanya bisa mencairkan retensi setelah **masa pemeliharaan lewat** dan **punch list bersih**; sebelum itu ditolak dengan alasan.
6. Sebagai owner, saya melihat evaluasi vendor berbukti; jika belum ada bukti maka tampil **“belum ada data”**, bukan skor 0.

**Langkah POC:**
- P1. Tambah helper fixture POC48 (opsional) untuk membuat proyek/PR/PO/GRN/retur/SPK/claim, dan fungsi `settle()`.
- P2. Alur 1: PR → (stok kurang) → generate PO dari PR → panggil lagi generator → tidak dobel.
- P3. Alur 2: GRN parsial → retur → cek ledger stok material & `received_value` PO.
- P4. Alur 3: coba buat bill > received → harus ditahan (HTTP 400/409) + pesan jelas; bill <= received → boleh.
- P5. Alur 4: SPK + uang muka + denda + retensi; approve claim → AP bill tercipta dengan potongan terikat.
- P6. Alur 5: daftar retensi: create retention release request → ditolak bila syarat belum terpenuhi; setelah syarat terpenuhi → release membuat jurnal + audit.
- P7. Websearch singkat: praktik terbaik **3-way match hold vs flag**, serta **valuasi persediaan average cost** + retur.

> Stop point: **jangan lanjut Fase 2** sebelum POC48 hijau.

---

### FASE 2 — V1 App Development (backend + frontend end-to-end)
**Output:** fitur tampil di UI pada halaman yang sudah ada: `/procurement`, `/subcon`, `/materials`, `/boq` (tanpa pintu sidebar baru).

#### 48A — Vendor Master + Price List + Pembanding
**Backend**
- A1. Koleksi: `vendors`, `vendor_price_lists` (riwayat per vendor+item+uom+periode).
- A2. Router `vendors_router.py`:
  - CRUD vendor, kontak/NPWP, default terms.
  - CRUD price list + endpoint pembanding (vendor vs vendor).
- A3. Wiring: PO wajib refer ke `vendor_id` (tetap simpan `vendor_name` snapshot).

**Frontend**
- AF1. Tambah tab **Vendor & Harga** di `/procurement`.
- AF2. Panel vendor (list/detail), panel price list (import sederhana CSV opsional), dan badge “di atas harga acuan”.

#### 48B — PR → PO + Retur + 3-way MENAHAN
**Backend**
- B1. Tambah jembatan `requisition_id` pada PO + endpoint `POST /materials/requisitions/{id}/to-po`.
- B2. Endpoint retur: `POST /procurement/returns` (membalik material_txns type `out`, menurunkan `received_qty/received_value`, jejak alasan wajib).
- B3. 3-way hold: pada `POST /procurement/bills` jika variance melewati toleransi → **tolak/hold** (bukan hanya flagged), serta opsi override khusus `finance_manager` dengan alasan.

**Frontend**
- BF1. Di `/materials` tab Permintaan: tombol **Buat PO** muncul saat stok kurang / item tidak tersedia.
- BF2. Di `/procurement` tab PO: tambah panel GRN + tombol **Retur** per GRN/item (alasan wajib).
- BF3. Di `/procurement` tab 3-way: tampilkan status hold + alasan + tindakan (override bila berwenang).

#### 48C — Subkon: Uang Muka, Potongan/Denda, Retensi + Pencairan
**Backend**
- C1. Koleksi: `subcon_advances`, `subcon_deductions`, `subcon_retentions`.
- C2. Integrasi ke `subcon_claims_router`: saat approve claim, hitung potongan (advance amortization + deductions) + retention held; tie-out ke AP.
- C3. Router retensi: `GET /subcon/retentions`, `POST /subcon/retentions/{id}/request-release`, `POST /subcon/retentions/{id}/release` (gated).
- C4. Gate syarat release: masa pemeliharaan lewat + punch list bersih + tidak ada sengketa.

**Frontend**
- CF1. `/subcon` tambah tab **Retensi & Potongan**: daftar retensi, advance, deductions per SPK.
- CF2. Flow request-release (lapangan/PM) → approve/release (finlead) dengan dialog alasan.

#### 48D — Evaluasi Vendor/Subkon berbukti
**Backend**
- D1. Engine evaluasi: hitung KPI dari data aktual (PO vs GRN lateness, retur/defect dari punch list, harga vs price list, kepatuhan dok).
- D2. Endpoint `GET /procurement/evaluations`, `GET /subcon/evaluations` dengan `missing_data` + `missing[]`.

**Frontend**
- DF1. Panel evaluasi di `/procurement` (vendor pemasok) dan `/subcon` (subkon).

#### 48E — Stok: Transfer, Stock Alert, Valuasi
**Backend**
- E1. Transfer antar proyek: `POST /materials/transfers` (out dari proyek A, in ke proyek B, atomic-ish dengan audit).
- E2. Stock alerts: threshold min per material per proyek + endpoint list.
- E3. Valuasi average cost per material/proyek + laporan ringkas.

**Frontend**
- EF1. `/materials` tambah tab **Transfer & Peringatan**: transfer dialog + daftar alert + ringkas valuasi.

---

### FASE 3 — SSOT + Seed + RBAC + Gates + Mutasi + Penutupan
**Output:** guardrail + data demo + uji-mutasi memastikan tidak regresi.

**User stories (QA/Governance):**
1. PR→PO tidak bisa dobel dari PR yang sama.
2. Retur selalu mengurangi stok & received_value, tidak bisa “menghilang”.
3. 3-way hold mencegah tagihan melebihi barang diterima, kecuali override beralasan oleh finlead.
4. Retensi tidak bisa dicairkan sebelum syarat (masa + punch list) terpenuhi.
5. Evaluasi vendor tidak boleh mengarang skor; harus “belum ada data” jika bukti kosong.

**Langkah:**
- S1. Tambah `backend/reference_p48.py` + gabungkan ke `/api/reference`.
- S2. Tambah `backend/models_p48.py` (alasan wajib, nominal >0, SoD).
- S3. `backend/seed_phase48.py` idempoten (`demo_batch="fase48"`) sesuai skenario.
- S4. Update RBAC: resource `vendors` + perluasan aksi procurement (return/override_hold) + subcon (retention_release/approve).
- S5. Gate baru:
  - `scripts/verify_procurement_vendor.py`
  - `scripts/verify_subcon_retention.py`
  - `scripts/verify_stock_control.py`
  Daftarkan ke `run_all_gates.sh` (33 → 36).
- S6. `scripts/mutasi_48.py` (16–20 mutasi) mematikan semua lapis aturan; semua harus tertangkap.
- S7. Update dok: `docs/v2/42_PENGADAAN_SUBKON_SPEC.md`, `CODEBASE_MAP.md`, `test_result.md`, `memory/test_credentials.md`, `plan.md`.
- S8. Tutup fase dengan testing agent E2E multi-peran.

---

## 3) Next Actions
1. Implement `poc/poc_48.py` + fixture cleanup/settle sampai hijau.
2. Implement backend minimal untuk gap terbesar: **vendor master**, **PR→PO bridge**, **retur**, **3-way hold**, **retensi release**.
3. Pasang UI minimal di tab existing: `/procurement`, `/materials`, `/subcon`.
4. Tambah SSOT/models/seed fase48.
5. Tambah 3 gates + `mutasi_48.py`, jalankan `run_all_gates.sh`.
6. Minta testing agent E2E multi-peran untuk penutupan Fase 48.

---

## 4) Success Criteria
- `python3 poc/poc_48.py` → **PASS**.
- PR→PO ada jejak (requisition_id), idempoten (tidak dobel).
- Retur mengurangi stok & received_value dan tercatat audit.
- 3-way **MENAHAN** bill melebihi received/PO; override hanya role berwenang + alasan.
- Subkon: advance/deductions/retention tie-out ke AP; retensi bisa dicairkan hanya jika gate terpenuhi.
- Evaluasi vendor/subkon berbukti, honest-null saat data kosong.
- Stok: transfer tidak menciptakan barang; alert & valuasi berjalan.
- `bash scripts/run_all_gates.sh` → **OVERALL PASS (36 gates)**.
- `python3 scripts/mutasi_48.py` → semua mutasi **TERTANGKAP**.
- Tidak ada regresi pada 33 gates lama.