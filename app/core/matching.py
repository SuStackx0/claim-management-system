from __future__ import annotations

# Keys mirror policy_terms.json waiting_periods.specific_conditions
CONDITION_KEYWORDS: dict[str, list[str]] = {
    "diabetes": ["diabetes", "diabetic", "t2dm", "dm"],
    "hypertension": ["hypertension", "htn"],
    "thyroid_disorders": ["thyroid", "hypothyroid", "hyperthyroid"],
    "joint_replacement": ["joint replacement", "knee replacement", "hip replacement"],
    "maternity": ["maternity", "pregnancy", "antenatal", "delivery"],
    "mental_health": ["depression", "anxiety", "psychiatric", "mental health"],
    "obesity_treatment": ["obesity", "bariatric", "weight loss"],
    "hernia": ["hernia"],
    "cataract": ["cataract"],
}

# Keys mirror policy_terms.json exclusions.conditions entries
EXCLUSION_KEYWORDS: dict[str, list[str]] = {
    "Self-inflicted injuries": ["self-inflicted", "self inflicted"],
    "Substance abuse treatment": ["substance abuse", "de-addiction", "deaddiction"],
    "Experimental treatments": ["experimental"],
    "Infertility and assisted reproduction": ["infertility", "ivf", "assisted reproduction"],
    "Obesity and weight loss programs": ["obesity", "weight loss", "diet plan",
                                         "diet and nutrition", "diet program"],
    "Bariatric surgery": ["bariatric"],
    "Cosmetic or aesthetic procedures": ["cosmetic", "aesthetic", "whitening", "veneer", "bleaching"],
    "Health supplements and tonics": ["supplement", "tonic"],
}

def match_condition(*texts: str | None) -> str | None:
    blob = " ".join(t.lower() for t in texts if t)
    for cond, kws in CONDITION_KEYWORDS.items():
        if any(kw in blob for kw in kws):
            return cond
    return None

def match_exclusion(*texts: str | None) -> str | None:
    blob = " ".join(t.lower() for t in texts if t)
    for name, kws in EXCLUSION_KEYWORDS.items():
        if any(kw in blob for kw in kws):
            return name
    return None

def text_matches_any(text: str, candidates: list[str]) -> str | None:
    """Case-insensitive substring match either direction; returns matched candidate."""
    t = text.lower()
    for c in candidates:
        if c.lower() in t or t in c.lower():
            return c
    return None
