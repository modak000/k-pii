"""한국 전화번호 detection (휴대전화 / 일반전화 / 인터넷전화).

Covered formats (domestic prefix only — international +82 left as a Phase 2.1
follow-up):
  - Mobile (휴대전화): 010·011·016·017·018·019 + 7~8 digits
  - Seoul landline: 02 + 7~8 digits
  - Regional landline: 031~033, 041~044, 051~055, 061~064 + 7~8 digits
  - VoIP (인터넷전화): 070 + 8 digits

Separators: hyphen, dot, space, or none. Each emitted DetectionResult carries
its sub-type in `extra["type"]` ∈ {"mobile", "landline", "voip"}.

Legal basis: 개인정보보호법 제2조 (개인 식별 정보).
"""
from __future__ import annotations

import re
from typing import Iterator

from k_pii.core.types import DetectionResult, RiskLevel

LABEL = "PHONE"
LEGAL_BASIS = "개인정보보호법 제2조"
CATEGORY = "일반개인정보"

_MOBILE = re.compile(
    r"(?<![0-9])"
    r"(01[01679])"
    r"[-.\s]?"
    r"(\d{3,4})"
    r"[-.\s]?"
    r"(\d{4})"
    r"(?![0-9])"
)

_SEOUL = re.compile(
    r"(?<![0-9])"
    r"(02)"
    r"[-.\s]?"
    r"(\d{3,4})"
    r"[-.\s]?"
    r"(\d{4})"
    r"(?![0-9])"
)

_REGIONAL = re.compile(
    r"(?<![0-9])"
    r"(03[1-3]|04[1-4]|05[1-5]|06[1-4]|070)"
    r"[-.\s]?"
    r"(\d{3,4})"
    r"[-.\s]?"
    r"(\d{4})"
    r"(?![0-9])"
)


def _emit(m: re.Match, phone_type: str) -> DetectionResult:
    digits = re.sub(r"\D", "", m.group(0))
    return DetectionResult(
        label=LABEL,
        text=m.group(0),
        start=m.start(),
        end=m.end(),
        risk_level=RiskLevel.MEDIUM,
        confidence=1.0,
        evidence=["pattern:phone", f"type:{phone_type}"],
        legal_basis=LEGAL_BASIS,
        extra={
            "type": phone_type,
            "prefix": m.group(1),
            "digits_only": digits,
            "category": CATEGORY,
        },
    )


def detect(text: str) -> Iterator[DetectionResult]:
    seen: set[tuple[int, int]] = set()

    for m in _MOBILE.finditer(text):
        span = (m.start(), m.end())
        if span in seen:
            continue
        seen.add(span)
        yield _emit(m, "mobile")

    for m in _REGIONAL.finditer(text):
        span = (m.start(), m.end())
        if span in seen:
            continue
        seen.add(span)
        prefix = m.group(1)
        yield _emit(m, "voip" if prefix == "070" else "landline")

    for m in _SEOUL.finditer(text):
        span = (m.start(), m.end())
        if span in seen:
            continue
        seen.add(span)
        yield _emit(m, "landline")
