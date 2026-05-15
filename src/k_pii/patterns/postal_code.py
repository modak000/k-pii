"""우편번호 (Korean Postal Code) detection.

Two historical formats:
  - 5-digit (2015-08-01 onward): YXXXX
  - 6-digit legacy (~2015):       XXX-XXX

5-digit codes are not matched unaided — too many 5-digit numeric runs would
become false positives. We require a "우편번호 / 우편" keyword immediately
before. The 6-digit hyphenated form is matched without keyword (the hyphen
structure itself is enough of a signal).

Legal basis: 개인정보보호법 제2조 (지역 식별 가능 정보).
"""
from __future__ import annotations

import re
from typing import Iterator

from k_pii.core.types import DetectionResult, RiskLevel

LABEL = "POSTAL_CODE"
LEGAL_BASIS = "개인정보보호법 제2조"
CATEGORY = "일반개인정보"

_LEGACY = re.compile(
    r"(?<![0-9])"
    r"([0-9]{3}-[0-9]{3})"
    r"(?![0-9])"
)

_NEW_WITH_KEYWORD = re.compile(
    r"(?:우편\s*번호|우편번호|우편)\s*:?\s*"
    r"([0-9]{5})"
    r"(?![0-9])"
)


def detect(text: str) -> Iterator[DetectionResult]:
    seen: set[tuple[int, int]] = set()

    for m in _NEW_WITH_KEYWORD.finditer(text):
        span = (m.start(1), m.end(1))
        if span in seen:
            continue
        seen.add(span)
        yield DetectionResult(
            label=LABEL,
            text=m.group(1),
            start=m.start(1),
            end=m.end(1),
            risk_level=RiskLevel.LOW,
            confidence=1.0,
            evidence=["pattern:postal_code", "format:5_digit", "keyword:우편번호"],
            legal_basis=LEGAL_BASIS,
            extra={"value": m.group(1), "format": "5_digit", "category": CATEGORY},
        )

    for m in _LEGACY.finditer(text):
        span = (m.start(), m.end())
        if span in seen:
            continue
        seen.add(span)
        yield DetectionResult(
            label=LABEL,
            text=m.group(1),
            start=m.start(),
            end=m.end(),
            risk_level=RiskLevel.LOW,
            confidence=0.85,
            evidence=["pattern:postal_code", "format:6_digit_legacy"],
            legal_basis=LEGAL_BASIS,
            extra={"value": m.group(1), "format": "6_digit", "category": CATEGORY},
        )
