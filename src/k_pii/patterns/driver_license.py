"""운전면허번호 (Driver License Number) detection.

12-digit format: XX-YY-NNNNNN-CC.
  XX: 지방경찰청 코드 (11~28 range historically assigned)
  YY: 면허 발급 연도 끝 2자리
  NNNNNN: 일련번호
  CC: 위변조 식별번호 (check) — the algorithm is not publicly standardized,
      so this module verifies format and region code only, not the check.

Legal basis: 개인정보보호법 시행령 제19조 (고유식별정보의 범위 — 운전면허번호).
"""
from __future__ import annotations

import re
from typing import Iterator

from k_pii.core.types import DetectionResult, RiskLevel

LABEL = "DRIVER_LICENSE"
LEGAL_BASIS = "개인정보보호법 시행령 제19조"
CATEGORY = "고유식별정보"

# 지방경찰청 region codes (도로교통공단). 11~28 covers the historically
# assigned range including 세종(28). 27 was not in regular use.
_VALID_REGION_CODES: set[str] = {f"{n:02d}" for n in range(11, 29)}

_PATTERN = re.compile(
    r"(?<![0-9])"
    r"([0-9]{2})-?"
    r"([0-9]{2})-?"
    r"([0-9]{6})-?"
    r"([0-9]{2})"
    r"(?![0-9])"
)


def detect(text: str) -> Iterator[DetectionResult]:
    for m in _PATTERN.finditer(text):
        region = m.group(1)
        if region not in _VALID_REGION_CODES:
            continue
        yield DetectionResult(
            label=LABEL,
            text=m.group(0),
            start=m.start(),
            end=m.end(),
            risk_level=RiskLevel.CRITICAL,
            confidence=0.85,
            evidence=["pattern:driver_license", f"region:{region}"],
            legal_basis=LEGAL_BASIS,
            extra={
                "region_code": region,
                "year_2digit": m.group(2),
                "sequence": m.group(3),
                "check_2digit": m.group(4),
                "category": CATEGORY,
            },
        )
