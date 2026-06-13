"""
Generate document images for the 12 assignment test cases, driven entirely by
`data/test_cases.json`. One PNG is rendered per document that carries renderable
content (or a known `actual_type`), named `<case_id>_<file_id>.png`.

The number of images per case varies with the case: a single-document case
produces one image, a three-document case produces three, and a document that
the live eval should keep as injected content (no `actual_type`/`content`)
produces none. The eval runner loads whatever images exist and falls back to the
case's provided content for any document without one.

Run: python scripts/generate_eval_docs.py [--out eval_docs] [--cases data/test_cases.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH = 800
FONT_SIZE = 18
BOLD_SIZE = 22


def _clean(s: str) -> str:
    """The bundled PIL font lacks a few glyphs (em/en dash, rupee sign); swap
    them for ASCII so nothing renders as a tofu box for the vision model."""
    return (str(s).replace("—", "-").replace("–", "-")
            .replace("₹", "Rs. ").replace("’", "'"))


def _fonts():
    return ImageFont.load_default(size=BOLD_SIZE), ImageFont.load_default(size=FONT_SIZE)


def _new(height: int = 1050):
    img = Image.new("RGB", (WIDTH, height), "white")
    return img, ImageDraw.Draw(img)


def _header(d, lines, bold, y=40):
    for ln in lines:
        d.text((50, y), _clean(ln), fill="black", font=bold)
        y += 30
    d.line([(50, y + 5), (WIDTH - 50, y + 5)], fill="black", width=2)
    return y + 22


def _text(d, lines, regular, y):
    for ln in lines:
        d.text((50, y), _clean(ln), fill="black", font=regular)
        y += 30
    return y


def _line_items(d, items, regular, y):
    d.line([(50, y), (WIDTH - 50, y)], fill="#cccccc", width=1)
    y += 10
    for desc, amt in items:
        d.text((50, y), _clean(desc), fill="black", font=regular)
        d.text((620, y), f"Rs. {amt:,}", fill="black", font=regular)
        y += 28
    d.line([(50, y), (WIDTH - 50, y)], fill="black", width=1)
    return y + 8


# ── content helpers ──────────────────────────────────────────────────────────

def _patient(content: dict, doc: dict, member_names: dict, member_id: str) -> str:
    return (content.get("patient_name")
            or doc.get("patient_name_on_doc")
            or member_names.get(member_id, "Patient"))


def _items(content: dict) -> list[tuple[str, int]]:
    rows = []
    for li in content.get("line_items") or []:
        rows.append((li.get("description", "Item"), int(li.get("amount", 0))))
    return rows


# ── renderers (content-driven) ───────────────────────────────────────────────

def render_prescription(content, patient, date) -> Image.Image:
    bold, regular = _fonts()
    img, d = _new()
    doctor = content.get("doctor_name", "Dr. A. Sharma")
    reg = content.get("doctor_registration", "KA/00000/2015")
    y = _header(d, [doctor, f"Reg. No: {reg}",
                    "City Medical Centre, MG Road, Bengaluru — 560001"], bold)
    lines = ["", f"Patient : {patient}                 Date : {date}", ""]
    if content.get("diagnosis"):
        lines += [f"Diagnosis : {content['diagnosis']}", ""]
    if content.get("treatment"):
        lines += [f"Treatment : {content['treatment']}", ""]
    if content.get("medicines"):
        lines.append("Rx:")
        for i, m in enumerate(content["medicines"], 1):
            lines.append(f"  {i}. {m}")
        lines.append("")
    if content.get("tests_ordered"):
        lines.append("Investigations advised:")
        for t in content["tests_ordered"]:
            lines.append(f"  - {t}")
        lines.append("")
    lines += ["Advice : Review as needed.", "", "Signature: ___________________________"]
    _text(d, lines, regular, y)
    return img


def render_hospital_bill(content, patient, date) -> Image.Image:
    bold, regular = _fonts()
    img, d = _new(950)
    hospital = content.get("hospital_name", "City Hospital")
    y = _header(d, [f"{hospital} — Outpatient Bill",
                    "MG Road, Bengaluru 560001  |  GSTIN: 29ABCDE1234F1Z5"], bold)
    y = _text(d, ["", f"Bill No : CH/2024/0001          Date : {date}",
                  f"Patient : {patient}", "Policy  : PLUM_GHI_2024", "",
                  "Services Rendered:"], regular, y)
    items = _items(content)
    if items:
        y = _line_items(d, items, regular, y)
    total = content.get("total")
    if total is not None:
        y = _text(d, ["", f"                               Total Billed : Rs. {int(total):,}"],
                  regular, y)
    _text(d, ["", "Authorised Signatory: ___________________________"], regular, y)
    return img


def render_pharmacy_bill(content, patient, date) -> Image.Image:
    bold, regular = _fonts()
    img, d = _new(750)
    y = _header(d, ["MedPlus Pharmacy",
                    "Residency Road, Bengaluru 560025"], bold)
    y = _text(d, ["", f"Bill No : MP/2024/0001          Date : {date}",
                  f"Patient : {patient}", "", "Items:"], regular, y)
    items = _items(content) or [("Prescribed medicines (as per Rx)",
                                 int(content.get("total", 800)))]
    y = _line_items(d, items, regular, y)
    total = content.get("total", sum(a for _, a in items))
    _text(d, ["", f"                          Total : Rs. {int(total):,}",
              "", "Pharmacist: _______________"], regular, y)
    return img


def render_lab_report(content, patient, date) -> Image.Image:
    bold, regular = _fonts()
    img, d = _new(800)
    y = _header(d, ["Precision Diagnostics Pvt. Ltd.",
                    "NABL Accredited Lab  |  Jayanagar, Bengaluru — 560041"], bold)
    test = content.get("test_name") or content.get("test") or "Diagnostic Test"
    _text(d, ["", f"Patient   : {patient}              Report Date : {date}",
              "Member ID : (per claim)", "",
              f"STUDY : {test}", "",
              "FINDINGS:", "  See attached clinical report.", "",
              "Reported by: Dr. A. Krishnan, MD (Radiology)",
              "Signature: ___________________________   [Centre Stamp]"], regular, y)
    return img


def render_generic(content, patient, date, actual_type) -> Image.Image:
    bold, regular = _fonts()
    img, d = _new(700)
    y = _header(d, [f"{(actual_type or 'DOCUMENT').replace('_', ' ').title()}",
                    "Medical Record"], bold)
    lines = ["", f"Patient : {patient}              Date : {date}", ""]
    for k, v in content.items():
        if k in ("line_items", "patient_name", "date"):
            continue
        lines.append(f"{k.replace('_', ' ').title()} : {v}")
    _text(d, lines, regular, y)
    return img


_RENDERERS = {
    "PRESCRIPTION": render_prescription,
    "HOSPITAL_BILL": render_hospital_bill,
    "PHARMACY_BILL": render_pharmacy_bill,
    "LAB_REPORT": render_lab_report,
    "DIAGNOSTIC_REPORT": render_lab_report,
}


def _load_member_names(policy_path: Path) -> dict[str, str]:
    try:
        policy = json.loads(policy_path.read_text())
    except Exception:
        return {}
    members = policy.get("members") or policy.get("member_roster") or []
    return {m.get("member_id"): m.get("name", "") for m in members if m.get("member_id")}


def generate(cases_path: Path, out: Path, policy_path: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    cases = json.loads(cases_path.read_text())["test_cases"]
    member_names = _load_member_names(policy_path)
    written: list[Path] = []

    for case in cases:
        cid = case["case_id"]
        inp = case["input"]
        member_id = inp.get("member_id", "")
        default_date = str(inp.get("treatment_date", "2024-11-01"))
        for doc in inp.get("documents", []):
            actual_type = doc.get("actual_type")
            content = dict(doc.get("content") or {})
            # Skip documents with neither a known type nor content — nothing to draw.
            if not actual_type and not content:
                continue
            patient = _patient(content, doc, member_names, member_id)
            date = content.get("date", default_date)
            renderer = _RENDERERS.get(actual_type)
            if renderer is render_lab_report:
                img = renderer(content, patient, date)
            elif renderer is None:
                img = render_generic(content, patient, date, actual_type)
            else:
                img = renderer(content, patient, date)
            if (doc.get("quality") or "").upper() == "UNREADABLE":
                # Heavy blur so the vision model reliably reports UNREADABLE
                # rather than occasionally guessing the text on a light blur.
                img = img.filter(ImageFilter.GaussianBlur(radius=9))
            path = out / f"{cid}_{doc['file_id']}.png"
            img.save(path)
            written.append(path)

    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="eval_docs", help="output directory")
    parser.add_argument("--cases", default="data/test_cases.json", help="test cases JSON")
    parser.add_argument("--policy", default="data/policy_terms.json", help="policy JSON (member names)")
    args = parser.parse_args()
    written = generate(Path(args.cases), Path(args.out), Path(args.policy))
    print(f"wrote {len(written)} eval document images to {args.out}/")
    for p in written:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
