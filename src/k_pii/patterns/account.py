"""은행 계좌번호 (Bank Account Number) — keyword-anchored baseline.

Korean bank account formats vary widely (10–14 digits, multiple group styles)
and a raw structural match has too many false positives (phone numbers,
business numbers, …). This Phase 2 baseline requires a "계좌" keyword
immediately before the candidate.

A future iteration can add bank-specific format validation (KB/우리/신한/
농협/하나/카카오/토스 등) once the bank dictionary is in place.

Legal basis: 개인정보보호법 제2조; 금융실명거래 및 비밀보장에 관한 법률.
"""
from __future__ import annotations

import re
from typing import Iterator

from k_pii.core.types import DetectionResult, RiskLevel

LABEL = "ACCOUNT"
LEGAL_BASIS = "개인정보보호법 제2조; 금융실명법"
CATEGORY = "일반개인정보"

_PATTERN = re.compile(
    r"(?:계좌\s*(?:번호|번)?\s*:?\s*)"
    r"([0-9][\s\-]*(?:[0-9][\s\-]*){9,19})"
)


def detect(text: str) -> Iterator[DetectionResult]:
    for m in _PATTERN.finditer(text):
        raw = m.group(1)
        digits = re.sub(r"[\s\-]", "", raw)
        if not (10 <= len(digits) <= 16):
            continue
        yield DetectionResult(
            label=LABEL,
            text=raw.strip(),
            start=m.start(1),
            end=m.start(1) + len(raw.rstrip()),
            risk_level=RiskLevel.HIGH,
            confidence=0.9,
            evidence=["pattern:account", "keyword:계좌"],
            legal_basis=LEGAL_BASIS,
            extra={
                "digits": digits,
                "length": len(digits),
                "category": CATEGORY,
            },
        )
