"""도로명 주소 (Korean road-name address) — Phase 2 baseline.

Captures addresses ending in 로/길/대로 + a building number. To keep
precision high without a full 행정구역 dictionary, we require *either*:
  - A 시/도/시/군/구 token immediately before the road component, OR
  - A "주소" keyword within 20 characters before the road component.

Limitations (deferred):
  - Full cross-validation against 행정안전부 행정구역 사전
  - 지번 (lot-based) 주소 — to be added with the address dictionary in
    a later phase
  - Detail components such as 동/호/층 inside parentheses are not parsed

Legal basis: 개인정보보호법 제2조 (거주지 식별 가능 정보).
"""
from __future__ import annotations

import re
from typing import Iterator

from k_pii.core.types import DetectionResult, RiskLevel

LABEL = "ADDRESS"
LEGAL_BASIS = "개인정보보호법 제2조"
CATEGORY = "일반개인정보"

# Optional 시/도/시/군/구 prefix + road token + building number
_PATTERN = re.compile(
    r"(?:([가-힣]+(?:특별시|광역시|특별자치도|특별자치시|도))\s+)?"
    r"(?:([가-힣]+(?:시|군|구))\s+)?"
    r"([가-힣A-Za-z0-9]+(?:대로|로|길))"
    r"\s+"
    r"([0-9]+(?:-[0-9]+)?)"
)


def detect(text: str) -> Iterator[DetectionResult]:
    for m in _PATTERN.finditer(text):
        city = m.group(1)
        district = m.group(2)
        # Require some anchor: either a 시/도/시군구 prefix or a "주소" keyword
        # within 20 chars before the match.
        if not (city or district):
            window_start = max(0, m.start() - 20)
            if "주소" not in text[window_start:m.start()]:
                continue
        yield DetectionResult(
            label=LABEL,
            text=m.group(0).strip(),
            start=m.start(),
            end=m.end(),
            risk_level=RiskLevel.MEDIUM,
            confidence=0.8,
            evidence=[
                "pattern:address_road",
                f"anchor:{'prefix' if (city or district) else 'keyword'}",
            ],
            legal_basis=LEGAL_BASIS,
            extra={
                "city": city,
                "district": district,
                "road": m.group(3),
                "building_number": m.group(4),
                "category": CATEGORY,
            },
        )
