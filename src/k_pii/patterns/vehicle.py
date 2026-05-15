"""자동차 등록번호 (Vehicle License Plate) detection.

Korean plate format (post-2004 — the only form effectively in use today):
  NN[가-힣] NNNN  or  NNN[가-힣] NNNN
  ─ 2 or 3 digit prefix
  ─ 1 Korean character (purpose code: 가/나/다 personal, 바/사/아/자 commercial,
    하/허/호 rental, 외/협 diplomatic, etc.)
  ─ 4 digit suffix

The Korean character + the digit-Korean-digit structure makes this fairly
specific; surrounding digit/Korean lookarounds prevent matches inside larger
mixed sequences.

Legal basis: 개인정보보호법 제2조 (차량 소유자 식별 가능 정보).
"""
from __future__ import annotations

import re
from typing import Iterator

from k_pii.core.types import DetectionResult, RiskLevel

LABEL = "VEHICLE"
LEGAL_BASIS = "개인정보보호법 제2조"
CATEGORY = "일반개인정보"

_PATTERN = re.compile(
    r"(?<![0-9가-힣])"
    r"([0-9]{2,3})\s?([가-힣])\s?([0-9]{4})"
    r"(?![0-9가-힣])"
)


def detect(text: str) -> Iterator[DetectionResult]:
    for m in _PATTERN.finditer(text):
        yield DetectionResult(
            label=LABEL,
            text=m.group(0),
            start=m.start(),
            end=m.end(),
            risk_level=RiskLevel.LOW,
            confidence=0.85,
            evidence=["pattern:vehicle"],
            legal_basis=LEGAL_BASIS,
            extra={
                "prefix": m.group(1),
                "purpose_char": m.group(2),
                "suffix": m.group(3),
                "category": CATEGORY,
            },
        )
