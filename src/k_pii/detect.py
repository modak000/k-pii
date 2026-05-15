"""All-detector entry point — 모든 카테고리 검출기를 한 번에 실행."""
from __future__ import annotations

from typing import Iterable, Iterator, Optional

from k_pii.core.types import DetectionResult
from k_pii.domain import civil_petition as _dom_petition
from k_pii.domain import government as _dom_gov
from k_pii.domain import hr as _dom_hr
from k_pii.patterns import (
    account,
    address,
    business_reg,
    card,
    corp_reg,
    driver_license,
    email,
    fax,
    frn,
    ip,
    medical_insurance,
    passport,
    person,
    phone,
    pnu,
    postal_code,
    prescription,
    rrn,
    url,
    vehicle,
)

DETECTORS = (
    rrn.detect,
    frn.detect,
    business_reg.detect,
    corp_reg.detect,
    driver_license.detect,
    passport.detect,
    card.detect,
    medical_insurance.detect,
    prescription.detect,
    pnu.detect,
    fax.detect,
    phone.detect,
    email.detect,
    postal_code.detect,
    ip.detect,
    vehicle.detect,
    url.detect,
    address.detect,
    account.detect,
    person.detect,
    # Domain-specific (Phase 4)
    _dom_gov.detect,
    _dom_petition.detect,
    _dom_hr.detect,
)


def detect_all(
    text: str,
    include: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
) -> list[DetectionResult]:
    """Run every detector and return a merged, conflict-resolved list.

    Overlapping spans are resolved by (a) higher risk level, then (b) longer
    span, then (c) earlier start. This matches the design decisions D-002 /
    D-003 / D-006 / D-008 in CLAUDE.md.

    ``include`` / ``exclude`` filter on the resulting DetectionResult labels.
    """
    raw: list[DetectionResult] = []
    for fn in DETECTORS:
        raw.extend(fn(text))

    inc = set(include) if include else None
    exc = set(exclude) if exclude else set()
    if inc is not None:
        raw = [d for d in raw if d.label in inc]
    if exc:
        raw = [d for d in raw if d.label not in exc]

    return _resolve_overlaps(raw)


def _resolve_overlaps(
    detections: Iterable[DetectionResult],
) -> list[DetectionResult]:
    """Deterministic overlap resolution.

    Sort by (start asc, -risk_level, -length, -confidence). Then sweep:
    a later detection that *starts inside* an already-accepted one is dropped.
    """
    items = sorted(
        detections,
        key=lambda d: (
            d.start,
            -int(d.risk_level),
            -(d.end - d.start),
            -d.confidence,
        ),
    )
    out: list[DetectionResult] = []
    occupied_end = -1
    for d in items:
        if d.start < occupied_end:
            continue
        out.append(d)
        occupied_end = max(occupied_end, d.end)
    return out
