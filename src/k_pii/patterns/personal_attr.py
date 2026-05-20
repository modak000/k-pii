"""인적 속성 (Personal Attributes) — 학력·전공·직책·측정치.

검출 카테고리:
- ``EDUCATION`` (OGG_EDUCATION) : 대학교/전문대 (사전 매칭)
- ``MAJOR``     (FD_MAJOR)      : 전공·학과 (사전 + suffix 정규화)
- ``POSITION``  (CV_POSITION)   : 직책·직급 (titles 사전, 단독 emit)
- ``AGE``       (QT_AGE)         : 32세 / 32살
- ``HEIGHT``    (QT_LENGTH)      : 175cm / 1.75m
- ``WEIGHT``    (QT_WEIGHT)      : 70kg / 70kilo

위험도 정책:
- EDUCATION, MAJOR: MEDIUM/LOW (quasi-identifier)
- POSITION: LOW (단독은 직책일 뿐)
- AGE/HEIGHT/WEIGHT: INFO (단독 PII 아님, 결합위험도 산정용)

Legal basis: 개인정보보호법 제2조; 「개인정보 비식별 조치 가이드라인」
준식별자 (Quasi-Identifier) 분류 — 다른 정보와 결합 시 재식별 위험.
"""
from __future__ import annotations

import re
from typing import Iterator

from k_pii.core.types import DetectionResult, RiskLevel

LEGAL_BASIS = "개인정보보호법 제2조"


# ═══════════════════════════════════════════════════════════════════════
# EDUCATION (학력)
# ═══════════════════════════════════════════════════════════════════════
# 대학교 정식명: 2-15자 + (대학교/대학/대학원/전문대학/대학원대학교)
# 약칭: 2-5자 + 대 (서울대/연대/고대 등) — 사전 매칭 필수
# 외국어 약칭: KAIST/POSTECH/UNIST/GIST/DGIST
# 초중고: 2-10자 + (초/중/고/초등학교/중학교/고등학교)
_EDUCATION_PATTERN = re.compile(
    r"(?<![가-힣A-Za-z])"
    r"(?P<full>[가-힣]{2,15}(?:대학교|대학원대학교|전문대학|대학원|대학)|"
    r"(?P<abbrev>[가-힣]{1,5}대)|"  # 1자 prefix 허용 — "고대/홍대/이대/연대/성대"
    r"(?P<eng>KAIST|POSTECH|UNIST|GIST|DGIST)|"
    r"(?P<kor>카이스트|포스텍|유니스트|지스트|디지스트)|"
    r"(?P<elem>[가-힣]{2,10}초등학교|[가-힣]{1,8}초)|"
    r"(?P<mid>[가-힣]{2,10}중학교|[가-힣]{1,8}중)|"
    r"(?P<high>[가-힣]{2,10}고등학교|[가-힣]{1,8}고))"
    r"(?![가-힣A-Za-z])"
)


def detect_education(text: str) -> Iterator[DetectionResult]:
    from k_pii.dictionaries.universities import (
        is_university, normalize_university,
    )
    for m in _EDUCATION_PATTERN.finditer(text):
        raw = m.group(0)
        # 약칭이면 사전 검증
        if m.group("abbrev"):
            if not is_university(raw):
                continue
            canonical = normalize_university(raw)
            edu_type = "university_abbrev"
        elif m.group("full") or m.group("eng") or m.group("kor"):
            if not is_university(raw):
                continue
            canonical = normalize_university(raw)
            edu_type = "university"
        elif m.group("elem"):
            canonical = raw
            edu_type = "elementary_school"
        elif m.group("mid"):
            canonical = raw
            edu_type = "middle_school"
        elif m.group("high"):
            canonical = raw
            edu_type = "high_school"
        else:
            continue
        yield DetectionResult(
            label="EDUCATION",
            text=raw,
            start=m.start(),
            end=m.end(),
            risk_level=RiskLevel.MEDIUM,
            confidence=0.95 if edu_type.startswith("university") else 0.85,
            evidence=["pattern:education", f"type:{edu_type}", f"canonical:{canonical}"],
            legal_basis=LEGAL_BASIS,
            extra={"category": "준식별자", "canonical": canonical, "type": edu_type},
        )


# ═══════════════════════════════════════════════════════════════════════
# MAJOR (전공)
# ═══════════════════════════════════════════════════════════════════════
# 명확한 학과/학부/전공 suffix — lookahead 없음 (조사 부착 "경영학과니까" 매칭).
_MAJOR_PATTERN_LONG = re.compile(
    r"(?<![가-힣A-Za-z])"
    r"([가-힣]{1,11}(?:학과|학부|전공))"
)

# 짧은 학/과 suffix — 합성어 거부 위해 lookahead 유지 ("법학", "의예과").
_MAJOR_PATTERN_SHORT = re.compile(
    r"(?<![가-힣A-Za-z])"
    r"([가-힣]{1,10}(?:학|과))"
    r"(?![가-힣A-Za-z])"
)

# 단과대 약칭 — 의대/공대/미대/약대/법대/치대/한의대 등 (KDPII gold 빈출)
_MAJOR_FACULTY_ABBREV: frozenset[str] = frozenset([
    "의대", "치대", "한의대", "약대", "수의대",
    "법대", "행정대", "경상대학",
    "공대", "미대", "음대", "체대", "예대", "사범대",
    "신학대", "농대", "건축대",
])
_MAJOR_FACULTY_PATTERN = re.compile(
    r"(?<![가-힣A-Za-z])"
    r"([가-힣]{2,4})"
    r"(?![가-힣A-Za-z])"
)


def detect_major(text: str) -> Iterator[DetectionResult]:
    from k_pii.dictionaries.majors import is_major, normalize_major
    seen: set[tuple[int, int]] = set()
    # 1) 학과/학부/전공 suffix (lookahead 없음 — 조사 부착도 매칭)
    for m in _MAJOR_PATTERN_LONG.finditer(text):
        raw = m.group(1)
        if not is_major(raw):
            continue
        span = (m.start(1), m.end(1))
        if span in seen:
            continue
        seen.add(span)
        canonical = normalize_major(raw)
        yield DetectionResult(
            label="MAJOR",
            text=raw,
            start=span[0],
            end=span[1],
            risk_level=RiskLevel.LOW,
            confidence=0.9,
            evidence=["pattern:major", f"canonical:{canonical}"],
            legal_basis=LEGAL_BASIS,
            extra={"category": "준식별자", "canonical": canonical},
        )
    # 2) 짧은 학/과 suffix — "법학", "의예과", "수학" 등
    for m in _MAJOR_PATTERN_SHORT.finditer(text):
        raw = m.group(1)
        if not is_major(raw):
            continue
        span = (m.start(1), m.end(1))
        if any(span[0] < e and s < span[1] for s, e in seen):
            continue
        seen.add(span)
        canonical = normalize_major(raw)
        yield DetectionResult(
            label="MAJOR",
            text=raw,
            start=span[0],
            end=span[1],
            risk_level=RiskLevel.LOW,
            confidence=0.85,
            evidence=["pattern:major_short", f"canonical:{canonical}"],
            legal_basis=LEGAL_BASIS,
            extra={"category": "준식별자", "canonical": canonical},
        )
    # 3) 단과대 약칭 — 의대/공대/미대/약대/법대 등 (KDPII gold MAJOR 로 라벨)
    for m in _MAJOR_FACULTY_PATTERN.finditer(text):
        raw = m.group(1)
        if raw not in _MAJOR_FACULTY_ABBREV:
            continue
        span = (m.start(1), m.end(1))
        if any(span[0] < e and s < span[1] for s, e in seen):
            continue
        seen.add(span)
        yield DetectionResult(
            label="MAJOR",
            text=raw,
            start=span[0],
            end=span[1],
            risk_level=RiskLevel.LOW,
            confidence=0.8,
            evidence=["pattern:major_faculty_abbrev"],
            legal_basis=LEGAL_BASIS,
            extra={"category": "준식별자", "canonical": raw, "kind": "faculty_abbrev"},
        )


# ═══════════════════════════════════════════════════════════════════════
# POSITION (직책)
# ═══════════════════════════════════════════════════════════════════════
# titles 사전을 사용 — 단독 직책 emit (PERSON 컨텍스트와 별개)
# *키워드 anchor 필수* — "직급:" "직책:" "직위:" 등이 5자 이내 앞에 있어야
# 단독 emit. 이게 없으면 PERSON 검출에서 직책 인접 단서로만 사용됨.
_POSITION_ANCHORS = ("직급", "직책", "직위", "보직", "직군")
_POSITION_PATTERN = re.compile(
    r"(?<![가-힣A-Za-z])"
    r"([가-힣]{1,6})"
    r"(?![가-힣A-Za-z])"
)


def _position_anchor_before(text: str, start: int, window: int = 12) -> str | None:
    head = text[max(0, start - window): start]
    for kw in _POSITION_ANCHORS:
        if kw in head:
            return kw
    return None


_POSITION_HONORIFIC_PATTERN = re.compile(
    r"(?<![가-힣A-Za-z])"
    r"([가-힣]{1,6})님"
    # lookahead 제거 — "부장님께/부장님이/팀장님일" 같은 조사 부착 허용
)


def detect_position(text: str) -> Iterator[DetectionResult]:
    from k_pii.dictionaries.titles import is_title, title_domain
    seen: set[tuple[int, int]] = set()
    # 1) 키워드 anchor 모드 ("직급:/직책:/직위:")
    for m in _POSITION_PATTERN.finditer(text):
        raw = m.group(1)
        if not is_title(raw):
            continue
        kw = _position_anchor_before(text, m.start(1))
        if kw is None:
            continue
        span = (m.start(1), m.end(1))
        if span in seen:
            continue
        seen.add(span)
        domain = title_domain(raw) or "unknown"
        yield DetectionResult(
            label="POSITION",
            text=raw,
            start=span[0],
            end=span[1],
            risk_level=RiskLevel.LOW,
            confidence=0.85,
            evidence=["pattern:position", f"keyword:{kw}", f"domain:{domain}"],
            legal_basis=LEGAL_BASIS,
            extra={"category": "준식별자", "domain": domain},
        )

    # 2) 호칭 모드 — "부장님", "사장님", "팀장님" 같이 "님" suffix 가 붙은 직급
    #    KDPII 대화체에서 빈번 ("아 저 재무팀 김명진 과장님 만나러 왔는데요")
    for m in _POSITION_HONORIFIC_PATTERN.finditer(text):
        raw = m.group(1)
        if not is_title(raw):
            continue
        span = (m.start(1), m.end(1))
        # 호칭 자체 ("부장님") 보다는 직급 부분만 ("부장") emit
        if any(span[0] < e and s < span[1] for s, e in seen):
            continue
        seen.add(span)
        domain = title_domain(raw) or "unknown"
        yield DetectionResult(
            label="POSITION",
            text=raw,
            start=span[0],
            end=span[1],
            risk_level=RiskLevel.LOW,
            confidence=0.8,
            evidence=["pattern:position_honorific", f"domain:{domain}"],
            legal_basis=LEGAL_BASIS,
            extra={"category": "준식별자", "domain": domain, "honorific": True},
        )



# ═══════════════════════════════════════════════════════════════════════
# AGE / HEIGHT / WEIGHT (측정치)
# ═══════════════════════════════════════════════════════════════════════
_AGE_PATTERN = re.compile(
    r"(?<![0-9])"
    r"(\d{1,3})"
    r"\s*(?:세|살)"
    r"(?=[은는이가도만에으로의을를과와요예니다,.\s)\]\!\?]|$)"
)

# 한글 음역 — "서른두 살", "스물여섯 살", "마흔 다섯 살" 등
_KOREAN_AGE_TENS = {
    "열": 10, "스물": 20, "서른": 30, "마흔": 40, "쉰": 50,
    "예순": 60, "일흔": 70, "여든": 80, "아흔": 90,
}
_KOREAN_AGE_ONES = {
    "한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5,
    "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9,
}
_KOREAN_AGE_TWENTIES = {
    "스무": 20,
}
_KOREAN_AGE_PATTERN = re.compile(
    r"(?<![가-힣])"
    r"(스무|"
    r"(?:열|스물|서른|마흔|쉰|예순|일흔|여든|아흔)(?:\s*(?:한|두|세|네|다섯|여섯|일곱|여덟|아홉))?)"
    r"\s*살"
)

_HEIGHT_PATTERN = re.compile(
    r"(?<![0-9.])"
    r"(\d{2,3}(?:\.\d{1,2})?)"
    r"\s*(?:cm|센티(?:미터)?|㎝)"
    r"(?![A-Za-z])",
    re.IGNORECASE,
)

# 키 (m 단위): 1.75m / 1m75 — 위험은 일반 거리와 충돌
_HEIGHT_M_PATTERN = re.compile(
    r"(?<![0-9.])"
    r"(1\.\d{1,2})\s*m"
    r"(?![A-Za-z])"
)

_WEIGHT_PATTERN = re.compile(
    r"(?<![0-9.])"
    r"(\d{1,3}(?:\.\d{1,2})?)"
    r"\s*(?:kg|키로(?:그램)?|킬로(?:그램)?|㎏|kilogram)"
    r"(?![A-Za-z])",
    re.IGNORECASE,
)


def _parse_korean_age(token: str) -> int | None:
    """'서른두', '스물여섯', '마흔다섯' 등을 숫자로 변환."""
    if token in _KOREAN_AGE_TWENTIES:
        return _KOREAN_AGE_TWENTIES[token]
    # 분리
    for tens_kor, tens_val in _KOREAN_AGE_TENS.items():
        if token.startswith(tens_kor):
            rest = token[len(tens_kor):].strip()
            if not rest:
                return tens_val
            if rest in _KOREAN_AGE_ONES:
                return tens_val + _KOREAN_AGE_ONES[rest]
    return None


def detect_measurements(text: str) -> Iterator[DetectionResult]:
    seen_age: set[tuple[int, int]] = set()
    for m in _AGE_PATTERN.finditer(text):
        age = int(m.group(1))
        if 0 <= age <= 150:
            span = (m.start(), m.end())
            seen_age.add(span)
            yield DetectionResult(
                label="AGE", text=m.group(0),
                start=span[0], end=span[1],
                risk_level=RiskLevel.INFO, confidence=0.95,
                evidence=["pattern:age", f"value:{age}"],
                legal_basis=LEGAL_BASIS,
                extra={"category": "준식별자", "value": age, "unit": "year"},
            )

    # 한글 음역
    for m in _KOREAN_AGE_PATTERN.finditer(text):
        span = (m.start(), m.end())
        if any(span[0] < e and s < span[1] for s, e in seen_age):
            continue
        token = m.group(1).strip()
        age = _parse_korean_age(token)
        if age is None or not (0 <= age <= 99):
            continue
        seen_age.add(span)
        yield DetectionResult(
            label="AGE", text=m.group(0),
            start=span[0], end=span[1],
            risk_level=RiskLevel.INFO, confidence=0.85,
            evidence=["pattern:age_korean", f"value:{age}", f"token:{token}"],
            legal_basis=LEGAL_BASIS,
            extra={"category": "준식별자", "value": age, "unit": "year",
                   "format": "korean"},
        )

    for m in _HEIGHT_PATTERN.finditer(text):
        height = float(m.group(1))
        if 50 <= height <= 250:
            yield DetectionResult(
                label="HEIGHT", text=m.group(0),
                start=m.start(), end=m.end(),
                risk_level=RiskLevel.INFO, confidence=0.9,
                evidence=["pattern:height", f"value:{height}cm"],
                legal_basis=LEGAL_BASIS,
                extra={"category": "준식별자", "value": height, "unit": "cm"},
            )

    for m in _HEIGHT_M_PATTERN.finditer(text):
        height_m = float(m.group(1))
        if 0.5 <= height_m <= 2.5:
            yield DetectionResult(
                label="HEIGHT", text=m.group(0),
                start=m.start(), end=m.end(),
                risk_level=RiskLevel.INFO, confidence=0.85,
                evidence=["pattern:height_m", f"value:{height_m}m"],
                legal_basis=LEGAL_BASIS,
                extra={"category": "준식별자", "value": height_m * 100, "unit": "cm"},
            )

    for m in _WEIGHT_PATTERN.finditer(text):
        weight = float(m.group(1))
        if 1 <= weight <= 300:
            yield DetectionResult(
                label="WEIGHT", text=m.group(0),
                start=m.start(), end=m.end(),
                risk_level=RiskLevel.INFO, confidence=0.9,
                evidence=["pattern:weight", f"value:{weight}kg"],
                legal_basis=LEGAL_BASIS,
                extra={"category": "준식별자", "value": weight, "unit": "kg"},
            )


# ═══════════════════════════════════════════════════════════════════════
# 통합 detect 진입점
# ═══════════════════════════════════════════════════════════════════════
def detect(text: str) -> Iterator[DetectionResult]:
    """모든 인적 속성 카테고리 검출."""
    yield from detect_education(text)
    yield from detect_major(text)
    yield from detect_position(text)
    yield from detect_measurements(text)
