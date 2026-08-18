"""seed_phase48.py — data demo Fase 48 (idempoten): pengadaan & subkon yang BISA DICOBA.

Pelajaran Fase 46 dipakai lagi: **fitur yang tidak bisa dicapai sama saja dengan tidak ada.**
Layar baru Fase 48 (vendor & harga, permintaan→PO, retur, uang muka/potongan/retensi,
peringatan stok) mustahil dibuktikan pada database yang hanya berisi data Fase 12–47.

Yang ditulis — semuanya BERSANDAR pada data nyata yang sudah ada (proyek, material, SPK,
tagihan), bukan objek karangan:

  * **3 master vendor** (pemasok beton, pemasok baja, penyewaan alat) lengkap dengan NPWP,
    termin bayar, dan rekening — supaya PO tidak lagi menyebut vendor sebagai teks bebas.
  * **Daftar harga** dua vendor untuk material yang sama, dengan harga BERBEDA, sehingga
    pembanding harga benar-benar punya isi dan uji kewajaran harga PO bisa berbunyi.
  * **1 permintaan material yang SUDAH DISETUJUI tetapi stoknya kurang** — bahan untuk
    mencoba tombol "Buat PO dari kekurangan" (jalur yang sebelumnya tidak ada).
  * **Batas stok minimum** pada dua material: satu di bawah batas (peringatan menyala), satu
    aman — supaya papan peringatan tidak kosong dan tidak berbohong.
  * **1 uang muka subkon yang SUDAH DIBAYAR** + **potongan menunggu** (angsuran uang muka &
    denda keterlambatan) — supaya termin berikutnya memperlihatkan potongan nyata.
  * **Backfill daftar retensi** dari tagihan termin lama yang retensinya sudah tertahan di
    pembukuan (`2-1200`) tetapi belum pernah punya daftar. Tanpa backfill, uang retensi yang
    sudah ada di buku besar tidak akan pernah bisa dicairkan lewat layar.

Seed TIDAK PERNAH menekan tombol milik manusia: tidak ada PO yang disetujui, tidak ada barang
yang diretur, tidak ada retensi yang dicairkan. Semua bertanda `demo_batch="fase48"`.
"""
import logging
from datetime import date, timedelta

from core_utils import new_id, now_iso, today_iso_date
from db import ORG_ID, db
from engine import material_book_stock
from reference_p48 import MAINTENANCE_DAYS_DEFAULT

logger = logging.getLogger("sipro.seed")
BATCH = "fase48"

VENDORS = [
    {"code": "VND-01", "name": "CV Sumber Beton Sejahtera", "category": "material",
     "npwp": "01.234.567.8-421.000", "phone": "+628123456701", "pic_name": "Hendra",
     "address": "Jl. Raya Industri No. 12, Bekasi", "payment_terms_days": 30,
     "bank_name": "BCA", "bank_account_no": "5220114455", "bank_account_holder": "CV Sumber Beton Sejahtera",
     "note": "Pemasok beton ready-mix & besi beton. Kirim H+1 setelah PO disetujui."},
    {"code": "VND-02", "name": "PT Baja Nusantara Perkasa", "category": "material",
     "npwp": "02.345.678.9-422.000", "phone": "+628123456702", "pic_name": "Sari",
     "address": "Kawasan Industri Jababeka Blok C-4", "payment_terms_days": 45,
     "bank_name": "Bank Mandiri", "bank_account_no": "1440099887", "bank_account_holder": "PT Baja Nusantara Perkasa",
     "note": "Besi beton & wiremesh. Harga mengikuti kontrak triwulan."},
    {"code": "VND-03", "name": "UD Sewa Alat Jaya", "category": "alat",
     "npwp": "03.456.789.0-423.000", "phone": "+628123456703", "pic_name": "Rudi",
     "address": "Jl. Cikarang Baru No. 8", "payment_terms_days": 14,
     "bank_name": "BRI", "bank_account_no": "300201004455", "bank_account_holder": "UD Sewa Alat Jaya",
     "note": "Sewa molen, vibrator, scaffolding. Tagihan mingguan."},
]


def _day(offset: int) -> str:
    return (date.fromisoformat(today_iso_date()) + timedelta(days=offset)).isoformat()


async def _vendors(org: str) -> list:
    out = []
    for v in VENDORS:
        found = await db.vendors.find_one({"org_id": org, "code": v["code"]}, {"_id": 0})
        if found:
            out.append(found)
            continue
        ts = now_iso()
        doc = {**v, "id": new_id(), "org_id": org, "demo_batch": BATCH, "is_active": True,
               "email": None, "created_by": "seed", "created_at": ts, "updated_at": ts}
        await db.vendors.insert_one(dict(doc))
        doc.pop("_id", None)
        out.append(doc)
    return out


async def _prices(org: str, vendors: list) -> int:
    """Dua vendor menawar material yang sama dengan harga berbeda (ada yang lebih mahal)."""
    mats = await db.materials.find({"org_id": org}, {"_id": 0}).sort("code", 1).to_list(10)
    if not mats or len(vendors) < 2:
        return 0
    written = 0
    for i, mat in enumerate(mats[:3]):
        base = 0
        # Harga dasar diambil dari realisasi PO bila ada, kalau tidak dari tebakan wajar
        # per satuan — tetap ditandai sumbernya supaya jujur.
        po = await db.purchase_orders.find_one(
            {"org_id": org, "items.material_id": mat["id"]}, {"_id": 0, "items": 1})
        if po:
            for it in po.get("items", []):
                if it.get("material_id") == mat["id"]:
                    base = int(it.get("unit_price", 0) or 0)
        if base <= 0:
            base = [95_000, 1_250_000, 78_000][i % 3]
        for j, vendor in enumerate(vendors[:2]):
            unit = int(round(base * (1.0 if j == 0 else 1.12)))
            key = {"org_id": org, "vendor_id": vendor["id"], "material_id": mat["id"],
                   "item_key": f"mat:{mat['id']}", "valid_from": _day(-30)}
            if await db.vendor_prices.find_one(key, {"_id": 0, "id": 1}):
                continue
            ts = now_iso()
            await db.vendor_prices.insert_one({
                **key, "id": new_id(), "demo_batch": BATCH, "vendor_name": vendor["name"],
                "item_name": mat.get("name"), "uom": mat.get("uom"), "unit_price": unit,
                "source": "penawaran", "valid_until": _day(60), "is_active": True,
                "note": "Penawaran tertulis vendor (contoh demo).", "history": [],
                "created_by": "seed", "created_at": ts, "updated_at": ts})
            written += 1
    return written


async def _requisition_with_shortage(org: str) -> dict | None:
    """Permintaan DISETUJUI yang stoknya kurang — bahan uji tombol 'Buat PO'."""
    found = await db.material_requisitions.find_one(
        {"org_id": org, "demo_batch": BATCH}, {"_id": 0})
    if found:
        return found
    proj = await db.projects.find_one({"org_id": org}, {"_id": 0, "id": 1, "name": 1})
    if not proj:
        return None
    mats = await db.materials.find({"org_id": org, "project_id": proj["id"]},
                                   {"_id": 0}).sort("code", 1).to_list(5)
    if not mats:
        return None
    items = []
    for mat in mats[:2]:
        stock = await material_book_stock(proj["id"], mat["id"], org)
        items.append({"material_id": mat["id"], "code": mat["code"], "name": mat["name"],
                      "uom": mat["uom"], "qty_requested": round(max(stock, 0) + 25, 2),
                      "qty_issued": 0.0, "qty_po": 0.0})
    ts = now_iso()
    import sequences as seq
    doc = {
        "id": new_id(), "org_id": org, "demo_batch": BATCH,
        "req_number": await seq.next_number("requisition", org, prefix="PR"),
        "project_id": proj["id"], "project_name": proj.get("name"),
        "phase_id": None, "phase_name": None, "task_id": None,
        "purpose": "Pengecoran kolom lantai 1 minggu depan",
        "items": items, "status": "approved",
        "requested_by": "site@sipro.co.id", "approved_by": "pm@sipro.co.id",
        "approved_at": ts, "issued_by": None, "issued_at": None,
        "rejected_by": None, "rejected_at": None,
        "note": "Stok di gudang tidak cukup — kekurangannya perlu dibelikan PO.",
        "po_ids": [], "po_numbers": [], "created_at": ts, "updated_at": ts,
    }
    await db.material_requisitions.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


async def _min_stock(org: str) -> int:
    """Satu material sengaja DI BAWAH batas minimum supaya peringatan bisa dilihat."""
    proj = await db.projects.find_one({"org_id": org}, {"_id": 0, "id": 1})
    if not proj:
        return 0
    mats = await db.materials.find({"org_id": org, "project_id": proj["id"]},
                                   {"_id": 0}).sort("code", 1).to_list(5)
    touched = 0
    for i, mat in enumerate(mats[:2]):
        if mat.get("min_qty") is not None:
            continue
        stock = await material_book_stock(proj["id"], mat["id"], org)
        min_qty = round(stock + 10, 2) if i == 0 else max(1.0, round(stock / 2, 2))
        await db.materials.update_one({"id": mat["id"], "org_id": org}, {"$set": {
            "min_qty": min_qty, "updated_at": now_iso()}})
        touched += 1
    return touched


async def _advance_and_deductions(org: str) -> dict | None:
    """Uang muka yang SUDAH dibayar + potongan menunggu (angsuran & denda)."""
    found = await db.subcon_advances.find_one({"org_id": org, "demo_batch": BATCH}, {"_id": 0})
    if found:
        return found
    spk = await db.spk.find_one({"org_id": org, "status": {"$in": ["active", "draft"]},
                                 "contract_value": {"$gt": 0}}, {"_id": 0})
    if not spk:
        return None
    import sequences as seq
    amount = int(round(int(spk["contract_value"]) * 0.1))
    ts = now_iso()
    adv = {
        "id": new_id(), "org_id": org, "demo_batch": BATCH,
        "advance_number": await seq.next_number("subcon_advance", org, prefix="UMK"),
        "spk_id": spk["id"], "spk_number": spk.get("spk_number"),
        "project_id": spk["project_id"], "subcontractor_id": spk.get("subcontractor_id"),
        "subcontractor_name": spk.get("subcontractor_name"),
        "amount": amount, "reason": "Mobilisasi alat & upah minggu pertama di lokasi.",
        "due_date": _day(-20), "state": "paid", "amortized": 0, "outstanding": amount,
        "decided_by": "finlead@sipro.co.id", "decided_at": ts,
        "decision_reason": "Sesuai kontrak: uang muka 10% setelah SPK ditandatangani.",
        "paid_at": ts, "paid_by": "finance@sipro.co.id", "journal_no": None,
        "created_by": "pm@sipro.co.id", "created_at": ts, "updated_at": ts,
    }
    await db.subcon_advances.insert_one(dict(adv))
    for kind, value, reason in (
        ("advance", int(round(amount * 0.25)),
         "Angsuran uang muka ke-1 (25%) sesuai jadwal potongan di SPK."),
        ("penalty", 2_500_000,
         "Denda keterlambatan penyelesaian pekerjaan struktur 5 hari kalender."),
    ):
        await db.subcon_deductions.insert_one({
            "id": new_id(), "org_id": org, "demo_batch": BATCH, "spk_id": spk["id"],
            "spk_number": spk.get("spk_number"), "project_id": spk["project_id"],
            "subcontractor_id": spk.get("subcontractor_id"),
            "subcontractor_name": spk.get("subcontractor_name"),
            "kind": kind, "amount": value, "reason": reason,
            "advance_id": adv["id"] if kind == "advance" else None,
            "state": "pending", "claim_id": None, "ap_bill_id": None, "applied_at": None,
            "cancelled_by": None, "cancel_reason": None,
            "created_by": "pm@sipro.co.id", "created_at": ts, "updated_at": ts})
    adv.pop("_id", None)
    return adv


async def _backfill_retentions(org: str) -> int:
    """Retensi yang SUDAH tertahan di pembukuan tetapi belum punya daftar.

    Tanpa ini, uang retensi lama (kredit `2-1200` dari termin yang sudah disetujui) tidak akan
    pernah bisa dicairkan lewat layar — persis lubang yang ditemukan audit Fase 48.
    """
    import sequences as seq
    bills = await db.ap_invoices.find(
        {"org_id": org, "retention_held": {"$gt": 0}, "status": {"$in": ["approved", "partial", "paid"]}},
        {"_id": 0}).to_list(500)
    made = 0
    for bill in bills:
        if bill.get("bill_kind") == "retention_release":
            continue
        if await db.subcon_retentions.find_one({"org_id": org, "ap_bill_id": bill["id"]},
                                               {"_id": 0, "id": 1}):
            continue
        claim = await db.progress_claims.find_one({"org_id": org, "ap_bill_id": bill["id"]},
                                                  {"_id": 0})
        spk = None
        if claim:
            spk = await db.spk.find_one({"id": claim.get("spk_id"), "org_id": org}, {"_id": 0})
        if not spk:
            spk = await db.spk.find_one({"id": bill.get("spk_id"), "org_id": org}, {"_id": 0})
        if not spk:
            continue
        ts = now_iso()
        # Termin lama: masa pemeliharaannya dihitung dari tanggal SPK selesai/kesepakatan,
        # sehingga sebagian sudah lewat (siap dicairkan bila punch list bersih) dan sebagian
        # belum — keduanya keadaan NYATA, bukan direkayasa supaya kelihatan bagus.
        base = str(spk.get("end_date") or bill.get("approved_at") or ts)[:10]
        days = spk.get("maintenance_days")
        days = MAINTENANCE_DAYS_DEFAULT if days is None else int(days)
        until = (date.fromisoformat(base) + timedelta(days=days)).isoformat()
        await db.subcon_retentions.insert_one({
            "id": new_id(), "org_id": org, "demo_batch": BATCH,
            "retention_number": await seq.next_number("subcon_retention", org, prefix="RET"),
            "spk_id": spk["id"], "spk_number": spk.get("spk_number"),
            "project_id": spk["project_id"], "subcontractor_id": spk.get("subcontractor_id"),
            "subcontractor_name": spk.get("subcontractor_name"),
            "claim_id": (claim or {}).get("id"), "claim_number": (claim or {}).get("claim_number"),
            "ap_bill_id": bill["id"], "amount": int(bill.get("retention_held", 0)),
            "retention_pct": float(bill.get("retention_pct", 0) or 0),
            "state": "held", "maintenance_days": days, "maintenance_until": until,
            "requested_by": None, "requested_at": None, "request_reason": None,
            "released_by": None, "released_at": None, "release_reason": None,
            "release_bill_id": None, "journal_no": None,
            "created_by": "seed", "created_at": ts, "updated_at": ts})
        made += 1
    return made


async def seed_phase48(org_id: str = ORG_ID) -> dict:
    vendors = await _vendors(org_id)
    prices = await _prices(org_id, vendors)
    req = await _requisition_with_shortage(org_id)
    mins = await _min_stock(org_id)
    adv = await _advance_and_deductions(org_id)
    rets = await _backfill_retentions(org_id)
    out = {"vendors": len(vendors), "prices": prices,
           "requisition": (req or {}).get("req_number"), "min_stock": mins,
           "advance": (adv or {}).get("advance_number"), "retentions": rets}
    if prices or mins or rets:
        logger.info("Seed Fase 48: %s", out)
    return out
