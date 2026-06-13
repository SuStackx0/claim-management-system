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


def lab_report_cbc(out: Path) -> None:
    """NABL-accredited CBC + Dengue lab report for Rajesh Kumar.
    Exercises: DIAGNOSTIC claim path, structured result extraction."""
    bold, regular = _fonts()
    img, d = _new(1100)
    y = _header(d, [
        "Precision Diagnostics Pvt. Ltd.",
        "NABL Accredited Lab  |  Lab ID: KA-NABL-5521",
        "45 Jayanagar, 4th Block, Bengaluru — 560041  |  Ph: 080-41234567",
    ], bold)
    y = _text(d, [
        "",
        "Patient   : Rajesh Kumar                    Sample Date  : 01-Nov-2024",
        "Age / Sex : 39 yrs / M                      Report Date  : 01-Nov-2024",
        "Member ID : EMP001                          Sample ID    : PD-2024-18723",
        "Ref. Doctor: Dr. Arun Sharma, City Medical Centre",
        "",
        "Test   : COMPLETE BLOOD COUNT (CBC) + Dengue Panel",
        "",
    ], regular, y)
    # table header
    d.line([(50, y), (WIDTH - 50, y)], fill="black", width=2)
    y += 8
    d.text((50, y),  "TEST NAME",       fill="black", font=bold)
    d.text((300, y), "RESULT",          fill="black", font=bold)
    d.text((420, y), "UNIT",            fill="black", font=bold)
    d.text((540, y), "NORMAL RANGE",    fill="black", font=bold)
    d.text((700, y), "FLAG",            fill="black", font=bold)
    y += 26
    d.line([(50, y), (WIDTH - 50, y)], fill="black", width=1)
    y += 8

    rows = [
        ("Haemoglobin",        "13.2",   "g/dL",  "13.0 – 17.0",  ""),
        ("RBC Count",          "4.65",   "mill/uL","4.50 – 5.90",  ""),
        ("WBC Count",          "9,800",  "/uL",   "4,500 – 11,000",""),
        ("Neutrophils",        "72",     "%",     "40 – 70",       "H"),
        ("Lymphocytes",        "20",     "%",     "20 – 40",       ""),
        ("Platelet Count",     "1,85,000","/uL",  "1,50,000 – 4,50,000",""),
        ("PCV / Haematocrit",  "40.2",   "%",     "40.0 – 50.0",  ""),
        ("MCV",                "86.4",   "fL",    "83.0 – 101.0", ""),
        ("MCH",                "28.4",   "pg",    "27.0 – 32.0",  ""),
        ("MCHC",               "32.8",   "g/dL",  "31.5 – 34.5",  ""),
        ("",                   "",       "",      "",              ""),
        ("Dengue NS1 Antigen", "NEGATIVE","",     "—",             ""),
        ("Dengue IgM",         "NEGATIVE","",     "—",             ""),
        ("Dengue IgG",         "NEGATIVE","",     "—",             ""),
    ]
    for name, result, unit, ref, flag in rows:
        d.text((50,  y), name,   fill="black", font=regular)
        d.text((300, y), result, fill="black", font=regular)
        d.text((420, y), unit,   fill="black", font=regular)
        d.text((540, y), ref,    fill="black", font=regular)
        d.text((700, y), flag,   fill="red" if flag == "H" else "black", font=regular)
        y += 26

    d.line([(50, y), (WIDTH - 50, y)], fill="black", width=1)
    y += 12
    y = _text(d, [
        "Remarks : Neutrophil count slightly elevated — consistent with early viral/",
        "          bacterial infection. Dengue panel negative. Clinical correlation advised.",
        "",
        "Verified by: Dr. Meena Pillai, MD (Pathology)  |  Reg. No: KA/89012/2018",
        "Signature: ___________________________   [Lab Stamp]",
        "",
        "Report generated electronically. Valid without physical signature if digitally",
        "verified at: https://precisiondiag.in/verify/PD-2024-18723",
    ], regular, y)
    img.save(out / "lab_report_cbc.png")


def hospital_bill_highvalue(out: Path) -> None:
    """Large inpatient hospital bill (~Rs. 87,500) for Rajesh Kumar.
    Exercises: high-value fraud/manual-review threshold in adjudication."""
    bold, regular = _fonts()
    img, d = _new(1200)
    y = _header(d, [
        "Manipal Hospitals — Inpatient Final Bill",
        "Old Airport Road, Bengaluru 560017  |  GSTIN: 29MANIP0001B1Z3",
        "Ph: 080-25024444  |  Hosp. Reg: KA/HOS/2001/0042",
    ], bold)
    y = _text(d, [
        "",
        "Bill No   : MH/IP/2024/00872         Date of Bill  : 10-Nov-2024",
        "Patient   : Rajesh Kumar             Member ID     : EMP001",
        "Policy    : PLUM_GHI_2024            IP No         : IP2024-08441",
        "Ward      : General Ward (Bed G-14)  Admission     : 05-Nov-2024",
        "Discharge : 09-Nov-2024              Treating Physician: Dr. Suresh Reddy",
        "Diagnosis : Typhoid Fever (confirmed Widal + blood culture)",
        "",
        "Itemised Charges:",
    ], regular, y)
    y = _line_items(d, [
        ("Room Charges — General Ward (4 nights x Rs. 3,500)", 14000),
        ("Nursing Charges (4 nights x Rs. 1,000)",              4000),
        ("Consultant Visit — Dr. Suresh Reddy (5 visits)",      7500),
        ("IV Antibiotics — Ceftriaxone 1g x 20 vials",          6000),
        ("IV Fluids & Consumables",                              3200),
        ("Widal Test + Blood Culture & Sensitivity",             2800),
        ("CBC (x4 serial counts)",                               2400),
        ("ECG",                                                   800),
        ("Chest X-Ray (PA View)",                               1200),
        ("USG Abdomen",                                          2500),
        ("Physiotherapy Sessions (x2)",                         1800),
        ("Pharmacy (detailed bill attached as Annexure A)",     18500),
        ("Miscellaneous / Sundries",                            2800),
        ("Dietitian Consultation (x2)",                         1000),
        ("Discharge Summary & Records",                          200),
    ], regular, y)
    y = _text(d, [
        "",
        "                               Gross Total       : Rs. 68,700",
        "                               Network Discount  : Rs.  6,870 (10%)",
        "                               Net Payable       : Rs. 61,830",
        "                               Co-pay (10%)      : Rs.  6,183",
        "                               Insurance Claimable: Rs. 55,647",
        "",
        "Sub-limit note: Pharmacy sub-limit may apply per policy schedule.",
        "",
        "Authorised Signatory: ___________________________   [Hospital Seal]",
        "Cashier: Ms. Divya Rao",
    ], regular, y)
    img.save(out / "hospital_bill_highvalue.png")


def discharge_summary(out: Path) -> None:
    """Inpatient discharge summary for Rajesh Kumar (Typhoid, 4-night stay).
    Exercises: CONSULTATION/inpatient claim, date-range extraction, diagnosis parsing."""
    bold, regular = _fonts()
    img, d = _new(1250)
    y = _header(d, [
        "Manipal Hospitals — Discharge Summary",
        "Old Airport Road, Bengaluru 560017  |  Ph: 080-25024444",
    ], bold)
    y = _text(d, [
        "",
        "Patient Name   : Rajesh Kumar           Member ID   : EMP001",
        "Age / Gender   : 39 yrs / Male          IP Number   : IP2024-08441",
        "Policy         : PLUM_GHI_2024          Ward / Bed  : General Ward / G-14",
        "Date of Admission  : 05-Nov-2024 (15:30 hrs)",
        "Date of Discharge  : 09-Nov-2024 (11:00 hrs)",
        "Total Days         : 4",
        "Treating Physician : Dr. Suresh Reddy, MD (Internal Medicine)",
        "                     Reg. No: KA/67321/2012",
        "",
        "PRESENTING COMPLAINTS:",
        "  - Fever (38.9°C) with chills for 6 days",
        "  - Abdominal pain (periumbilical), nausea",
        "  - Generalised weakness, anorexia",
        "",
        "DIAGNOSIS ON ADMISSION: Pyrexia of Unknown Origin (PUO)",
        "FINAL DIAGNOSIS       : Enteric Fever (Typhoid) — Salmonella Typhi",
        "",
        "INVESTIGATIONS:",
        "  CBC (admission): WBC 12,400/uL (neutrophilia), Hb 12.8 g/dL, Plt 1,10,000/uL",
        "  Widal Test (Day 2): TO titre 1:320 (significant), TH titre 1:160",
        "  Blood Culture (Day 1): Salmonella Typhi — sensitive to Ceftriaxone",
        "  USG Abdomen: Mild hepatosplenomegaly. No abscess.",
        "  Chest X-Ray: NAD",
        "",
        "TREATMENT GIVEN:",
        "  IV Ceftriaxone 1g BD x 5 days (switched to oral Azithromycin on day 4)",
        "  IV Fluids (NS + RL) for hydration",
        "  Tab Paracetamol 650mg SOS for fever",
        "  Soft liquid diet throughout admission",
        "",
        "CONDITION AT DISCHARGE: Stable. Afebrile for 48 hours. Tolerating oral feeds.",
        "",
        "DISCHARGE MEDICATIONS:",
        "  1. Tab Azithromycin 500mg — 1-0-0 x 5 days (to complete 10-day course)",
        "  2. Tab Paracetamol 650mg — SOS (if temp > 38°C)",
        "  3. ORS sachets as required",
        "  4. Probiotics — 1 capsule BD x 7 days",
        "",
        "FOLLOW-UP: Review with Dr. Reddy after 1 week (appointment enclosed).",
        "           Repeat CBC + LFT at follow-up.",
        "",
        "Dr. Suresh Reddy, MD (Internal Medicine)   Reg. No: KA/67321/2012",
        "Date: 09-Nov-2024                           Signature: _______________",
        "                                            [Hospital Stamp]",
    ], regular, y)
    img.save(out / "discharge_summary.png")


def vision_prescription(out: Path) -> None:
    """Optical / vision prescription for Rajesh Kumar.
    Exercises: VISION claim category, spectacle/lens power extraction."""
    bold, regular = _fonts()
    img, d = _new(900)
    y = _header(d, [
        "Dr. Kavitha Menon, MBBS, MS (Ophthalmology)",
        "Reg. No: KA/72345/2014",
        "ClearVision Eye Clinic, 8 Residency Road, Bengaluru — 560025",
        "Ph: 080-22567890",
    ], bold)
    y = _text(d, [
        "",
        "Patient  : Rajesh Kumar                   Date : 15-Oct-2024",
        "Age      : 39 yrs     Gender : M           Member ID : EMP001",
        "",
        "SPECTACLE PRESCRIPTION",
        "",
    ], regular, y)

    # prescription table
    d.line([(50, y), (WIDTH - 50, y)], fill="black", width=2)
    y += 8
    d.text((50,  y), "EYE",    fill="black", font=bold)
    d.text((160, y), "SPHERE", fill="black", font=bold)
    d.text((290, y), "CYLINDER", fill="black", font=bold)
    d.text((430, y), "AXIS", fill="black", font=bold)
    d.text((520, y), "ADD", fill="black", font=bold)
    d.text((610, y), "VA (corrected)", fill="black", font=bold)
    y += 26
    d.line([(50, y), (WIDTH - 50, y)], fill="black", width=1)
    y += 8

    for eye, sph, cyl, axis, add_, va in [
        ("Right (RE)", "-1.50", "-0.75", "170", "+2.00", "6/6"),
        ("Left  (LE)", "-2.00", "-0.50", "165", "+2.00", "6/6"),
    ]:
        d.text((50,  y), eye,  fill="black", font=regular)
        d.text((160, y), sph,  fill="black", font=regular)
        d.text((290, y), cyl,  fill="black", font=regular)
        d.text((430, y), axis, fill="black", font=regular)
        d.text((520, y), add_, fill="black", font=regular)
        d.text((610, y), va,   fill="black", font=regular)
        y += 26

    d.line([(50, y), (WIDTH - 50, y)], fill="black", width=1)
    y += 14

    y = _text(d, [
        "",
        "Lens Type    : Progressive (Anti-Reflective coating recommended)",
        "Frame Type   : Any",
        "PD (Pupillary Distance) : 64 mm",
        "",
        "Diagnosis    : Myopia with Astigmatism (both eyes); Presbyopia",
        "",
        "Estimated Spectacle Cost: Rs. 4,500 – Rs. 7,000 (frame + lens)",
        "",
        "Note: Annual vision benefit applicable under policy PLUM_GHI_2024.",
        "      Retain original prescription for insurance claim.",
        "",
        "Signature: ___________________________   [Clinic Stamp]",
    ], regular, y)
    img.save(out / "vision_prescription.png")


def unrelated_receipt(out: Path) -> None:
    """Supermarket / retail receipt — NOT a medical document.
    Exercises: document-type rejection by the Document Verification agent."""
    bold, regular = _fonts()
    img, d = _new(750)
    y = _header(d, [
        "FreshMart Supermarket",
        "Indiranagar Branch, 100 Feet Road, Bengaluru 560038",
        "GSTIN: 29FRESH1234F1Z0  |  PH: 080-41007788",
    ], bold)
    y = _text(d, [
        "",
        "CASH MEMO / TAX INVOICE",
        "Bill No : FM/2024/KN-039821          Date : 01-Nov-2024  17:42",
        "Cashier : Pooja S.                   Counter: 03",
        "",
        "Item                              Qty   Price   Amount",
    ], regular, y)
    d.line([(50, y), (WIDTH - 50, y)], fill="#cccccc", width=1)
    y += 8
    items = [
        ("Aashirvaad Atta 5kg",           1, 265,  265),
        ("Amul Full Cream Milk 1L x 2",   2,  68,  136),
        ("Sunflower Oil 1L",              1, 155,  155),
        ("Tata Salt 1kg",                 1,  28,   28),
        ("Haldiram's Bhujia 400g",        1,  99,   99),
        ("Colgate Toothpaste 200g",       1,  89,   89),
        ("Surf Excel 1kg",                1, 210,  210),
        ("Red Label Tea 500g",            1, 265,  265),
        ("Bingo! Chips Assorted x 3",     3,  20,   60),
        ("Parle-G Biscuits 800g",         1,  70,   70),
    ]
    for name, qty, price, amt in items:
        d.text((50,  y), name,         fill="black", font=regular)
        d.text((490, y), str(qty),     fill="black", font=regular)
        d.text((540, y), f"{price}",   fill="black", font=regular)
        d.text((610, y), f"Rs. {amt}", fill="black", font=regular)
        y += 26

    d.line([(50, y), (WIDTH - 50, y)], fill="black", width=1)
    y += 8
    y = _text(d, [
        "",
        "                             Sub Total   : Rs. 1,377",
        "                             GST (5% avg): Rs.    68",
        "                             Loyalty Pts :     - 50",
        "                             NET PAYABLE : Rs. 1,395",
        "",
        "Payment Mode: UPI (Google Pay)  |  Transaction ID: UPI24110117423",
        "",
        "Thank you for shopping at FreshMart!",
        "Customer care: 1800-XXX-XXXX",
    ], regular, y)
    img.save(out / "unrelated_receipt.png")


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    prescription_clean(out)
    bill_clean(out)
    bill_apollo(out)
    pharmacy_bill_blurry(out)
    prescription_wrong_patient(out)
    dental_bill_mixed(out)
    # new documents
    lab_report_cbc(out)
    hospital_bill_highvalue(out)
    discharge_summary(out)
    vision_prescription(out)
    unrelated_receipt(out)
    files = list(out.glob("*.png"))
    print(f"wrote {len(files)} docs to {out}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="sample_docs", help="output directory")
    args = parser.parse_args()
    main(Path(args.out))
