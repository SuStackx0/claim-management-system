from __future__ import annotations
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str
    amount: int
    quantity: int = 1

class PrescriptionData(BaseModel):
    doctor_name: str | None = None
    doctor_registration: str | None = None
    patient_name: str | None = None
    date: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medicines: list[str] = Field(default_factory=list)
    tests_ordered: list[str] = Field(default_factory=list)

class BillData(BaseModel):
    hospital_name: str | None = None
    patient_name: str | None = None
    date: str | None = None
    bill_number: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    total: int | None = None

class LabReportData(BaseModel):
    lab_name: str | None = None
    patient_name: str | None = None
    test_name: str | None = None
    report_date: str | None = None

class PharmacyBillData(BaseModel):
    pharmacy_name: str | None = None
    patient_name: str | None = None
    date: str | None = None
    total: int | None = None

SCHEMA_BY_DOCTYPE = {
    "PRESCRIPTION": PrescriptionData,
    "HOSPITAL_BILL": BillData,
    "PHARMACY_BILL": PharmacyBillData,
    "LAB_REPORT": LabReportData,
    "DIAGNOSTIC_REPORT": LabReportData,
    "DISCHARGE_SUMMARY": BillData,
    "DENTAL_REPORT": PrescriptionData,
}
