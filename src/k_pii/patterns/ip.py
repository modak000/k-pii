"""IP address detection (IPv4).

Each octet must be 0–255 and have no more than 3 digits. IPv6 is deferred
to a later iteration (rarely appears in Korean public-sector documents).

Legal basis: 개인정보보호법 제2조 — IP 주소는 결합 시 개인을 식별할 수 있는
정보로 보아 보호 대상이 될 수 있음 (방통위/개인정보위 해석).
"""
from __future__ import annotations

import re
from typing import Iterator

from k_pii.core.types import DetectionResult, RiskLevel

LABEL = "IP"
LEGAL_BASIS = "개인정보보호법 제2조"
CATEGORY = "일반개인정보"

_IPV4 = re.compile(
    r"(?<![0-9.])"
    r"((?:[0-9]{1,3}\.){3}[0-9]{1,3})"
    r"(?![0-9.])"
)


def _is_valid_ipv4(addr: str) -> bool:
    parts = addr.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit() or not (1 <= len(p) <= 3):
            return False
        if not (0 <= int(p) <= 255):
            return False
    return True


def detect(text: str) -> Iterator[DetectionResult]:
    for m in _IPV4.finditer(text):
        addr = m.group(1)
        if not _is_valid_ipv4(addr):
            continue
        yield DetectionResult(
            label=LABEL,
            text=addr,
            start=m.start(),
            end=m.end(),
            risk_level=RiskLevel.MEDIUM,
            confidence=1.0,
            evidence=["pattern:ipv4"],
            legal_basis=LEGAL_BASIS,
            extra={
                "version": 4,
                "value": addr,
                "category": CATEGORY,
            },
        )
