"""
Generate 6 synthetic Indian medical document images for live-demo purposes.
All text is fictional. Run: python scripts/generate_sample_docs.py [--out <dir>]
"""
from __future__ import annotations
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_SIZE = 18
BOLD_SIZE = 22
WIDTH = 800


def _fonts():
    bold = ImageFont.load_default(size=BOLD_SIZE)
    regular = ImageFont.load_default(size=FONT_SIZE)
    return bold, regular


def _new(height: int = 1050) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, height), "white")
    return img, ImageDraw.Draw(img)


def _header(d: ImageDraw.ImageDraw, lines: list[str], bold, y: int = 40) -> int:
    for ln in lines:
        d.text((50, y), ln, fill="black", font=bold)
        y += 30
    d.line([(50, y + 5), (WIDTH - 50, y + 5)], fill="black", width=2)
    return y + 22


def _text(d: ImageDraw.ImageDraw, lines: list[str], regular, y: int) -> int:
    for ln in lines:
        d.text((50, y), ln, fill="black", font=regular)
        y += 30
    return y


def _line_items(d: ImageDraw.ImageDraw, items: list[tuple[str, int]], regular, y: int) -> int:
    d.line([(50, y), (WIDTH - 50, y)], fill="#cccccc", width=1)
    y += 10
    for desc, amt in items:
        d.text((50, y), desc, fill="black", font=regular)
        d.text((650, y), f"Rs. {amt:,}", fill="black", font=regular)
        y += 28
    d.line([(50, y), (WIDTH - 50, y)], fill="black", width=1)
    return y + 8


def prescription_clean(out: Path) -> None:
    bold, regular = _fonts()
    img, d = _new()
    y = _header(d, [
        "Dr. Arun Sharma, MBBS, MD (Internal Medicine)",
        "Reg. No: KA/45678/2015",
        "City Medical Centre, 12 MG Road, Bengaluru — 560001",
        "Ph: 080-22334455",
    ], bold)
    y = _text(d, [
        "",
        "Patient : Rajesh Kumar                  Date : 01-Nov-2024",
        "Age     : 39 yrs    Gender : M",
        "Member ID: EMP001",
        "",
        "Diagnosis : Viral Fever / Acute Febrile Illness",
        "",
        "Rx:",
        "  1. Tab Paracetamol 650 mg  —  1-1-1  x 5 days",
        "  2. Tab Cetirizine 10 mg    —  0-0-1  x 3 days",
        "  3. Tab Vitamin C 500 mg    —  0-0-1  x 7 days",
        "  4. ORS Sachet              —  as required",
        "",
        "Investigations : CBC, Dengue NS1 Ag, Malarial Antigen",
        "",
        "Advice : Complete bed rest. Plenty of fluids.",
        "         Review after 3 days if fever persists.",
        "",
        "Signature: ___________________________",
    ], regular, y)
    img.save(out / "prescription_clean.png")


def bill_clean(out: Path) -> None:
    bold, regular = _fonts()
    img, d = _new(900)
    y = _header(d, [
        "City Clinic — Outpatient Bill",
        "12 MG Road, Bengaluru 560001  |  GSTIN: 29ABCDE1234F1Z5",
    ], bold)
    y = _text(d, [
        "",
        f"Bill No : CC/2024/4821          Date : 01-Nov-2024",
        "Patient : Rajesh Kumar          Member ID : EMP001",
        "Policy  : PLUM_GHI_2024",
        "",
        "Services Rendered:",
    ], regular, y)
    y = _line_items(d, [
        ("Consultation Fee — Dr. Arun Sharma", 500),
        ("CBC (Complete Blood Count)", 600),
        ("Dengue NS1 Antigen Test", 400),
    ], regular, y)
    y = _text(d, [
        "",
        "                               Total Billed : Rs. 1,500",
        "                               Amount Paid  : Rs. 0    (Insurance claim)",
        "",
        "Authorised Signatory: ___________________________",
    ], regular, y)
    img.save(out / "bill_clean.png")


def bill_apollo(out: Path) -> None:
    bold, regular = _fonts()
    img, d = _new(950)
    y = _header(d, [
        "Apollo Hospitals — Outpatient Bill",
        "Bannerghatta Road, Bengaluru 560076  |  GSTIN: 29APOLL0001A1Z5",
    ], bold)
    y = _text(d, [
        "",
        "Bill No : APO/2024/9031         Date : 01-Nov-2024",
        "Patient : Rajesh Kumar          Member ID : EMP001",
        "Policy  : PLUM_GHI_2024",
        "",
        "Network Hospital (15% discount applicable)",
        "",
        "Services Rendered:",
    ], regular, y)
    y = _line_items(d, [
        ("Consultation Fee — Senior Consultant", 4500),
    ], regular, y)
    y = _text(d, [
        "",
        "                               Gross Amount    : Rs. 4,500",
        "                               Network Discount: Rs.   675 (15%)",
        "                               Net Payable     : Rs. 3,825",
        "                               Co-pay (10%)    : Rs.   383",
        "                               Claimable       : Rs. 3,442",
        "",
        "Authorised Signatory: ___________________________",
    ], regular, y)
    img.save(out / "bill_apollo.png")


def pharmacy_bill_blurry(out: Path) -> None:
    bold, regular = _fonts()
    img, d = _new(700)
    y = _header(d, [
        "MedPlus Pharmacy",
        "15 Residency Road, Bengaluru 560025",
    ], bold)
    y = _text(d, [
        "",
        "Bill No : MP/2024/7710          Date : 28-Oct-2024",
        "Patient : Rajesh Kumar",
        "",
        "Items:",
    ], regular, y)
    y = _line_items(d, [
        ("Paracetamol 650mg x 10 tabs", 45),
        ("Cetirizine 10mg x 6 tabs", 30),
        ("Vitamin C 500mg x 10 tabs", 55),
        ("ORS Sachets x 5", 60),
    ], regular, y)
    y = _text(d, [
        "",
        "                          Total : Rs. 190",
        "",
        "Pharmacist: _______________",
    ], regular, y)
    img = img.filter(ImageFilter.GaussianBlur(radius=6))
    img.save(out / "pharmacy_bill_blurry.png")


def prescription_wrong_patient(out: Path) -> None:
    bold, regular = _fonts()
    img, d = _new()
    y = _header(d, [
        "Dr. Priya Nair, MBBS, MS (Orthopaedics)",
        "Reg. No: KA/56789/2018",
        "Manipal Hospital, Old Airport Road, Bengaluru — 560017",
    ], bold)
    y = _text(d, [
        "",
        "Patient : Arjun Mehta                   Date : 01-Nov-2024",
        "Age     : 28 yrs    Gender : M",
        "Member ID: EMP002",
        "",
        "Diagnosis : Right Knee Ligament Sprain",
        "",
        "Rx:",
        "  1. Tab Ibuprofen 400 mg  —  1-0-1 (after food)  x 5 days",
        "  2. Tab Pantoprazole 40 mg — 1-0-0 (before food)  x 5 days",
        "  3. Volini Gel — apply locally twice daily",
        "",
        "Advice : RICE protocol. Avoid weight-bearing for 3 days.",
        "         Physiotherapy referral if no improvement.",
        "",
        "Signature: ___________________________",
    ], regular, y)
    img.save(out / "prescription_wrong_patient.png")


def dental_bill_mixed(out: Path) -> None:
    bold, regular = _fonts()
    img, d = _new(950)
    y = _header(d, [
        "SmileCare Dental Clinic",
        "7 Brigade Road, Bengaluru 560025  |  Reg: KA/DENTAL/2301",
    ], bold)
    y = _text(d, [
        "",
        "Bill No : SC/2024/1102           Date : 01-Nov-2024",
        "Patient : Rajesh Kumar           Member ID : EMP001",
        "Policy  : PLUM_GHI_2024",
        "",
        "Dental Procedures:",
    ], regular, y)
    y = _line_items(d, [
        ("Root Canal Treatment — Tooth #36", 8000),
        ("Teeth Whitening (Cosmetic)", 4000),
    ], regular, y)
    y = _text(d, [
        "",
        "Note: Root Canal is covered under dental benefit (medically necessary).",
        "      Teeth Whitening is cosmetic and NOT covered under policy.",
        "",
        "                               Total Billed : Rs. 12,000",
        "",
        "Dentist: Dr. Kavita Rao  BDS MDS    Signature: ________________",
    ], regular, y)
    img.save(out / "dental_bill_mixed.png")


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    prescription_clean(out)
    bill_clean(out)
    bill_apollo(out)
    pharmacy_bill_blurry(out)
    prescription_wrong_patient(out)
    dental_bill_mixed(out)
    files = list(out.glob("*.png"))
    print(f"wrote {len(files)} docs to {out}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="sample_docs", help="output directory")
    args = parser.parse_args()
    main(Path(args.out))
