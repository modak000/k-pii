"""성명 (Korean person name) 컨텍스트 기반 검출 — Phase 3.

전체 파이프라인:
  1. 결정적 PII (RRN/PHONE/EMAIL/MEDICAL_INSURANCE) 위치를 별도 패스에서
     식별해 두고, 그 근방을 "deterministic_nearby" 플래그로 표시.
  2. 후보 추출: 2~4글자 한글 토큰 + 성씨 시작.
  3. 컨텍스트 점수 (`context.context_rules.score_candidate`) 로 평가.
  4. 임계값 이상이면 emit + 누적 사전 등록.
  5. 누적 사전 보유 이름은 약한 단서로 등장해도 두 번째 패스에서 emit.

Legal basis: 개인정보보호법 제2조 (성명을 통한 개인 식별).
"""
from __future__ import annotations

import re
from typing import Iterable, Iterator

from k_pii.context.context_rules import NameCandidate, score_candidate
from k_pii.context.name_dictionary import NameDictionary
from k_pii.context.particles import strip_trailing_particle
from k_pii.core.types import DetectionResult, RiskLevel
from k_pii.dictionaries.agencies import is_agency
from k_pii.dictionaries.agency_abbrev import normalize_agency
from k_pii.dictionaries.common_words import is_common_word
from k_pii.dictionaries.districts import is_district, is_province
from k_pii.dictionaries.field_labels import is_field_label
from k_pii.dictionaries.surnames import surname_prefix_len
from k_pii.dictionaries.titles import is_title

LABEL = "PERSON"
LEGAL_BASIS = "개인정보보호법 제2조"
CATEGORY = "일반개인정보"

# 이름 후보: 한글 2~4글자 (조사 포함하면 더 길어질 수 있음)
_CANDIDATE = re.compile(r"(?<![가-힣])([가-힣]{2,6})(?![가-힣])")

# 결정적 PII 의 *위치 마커* 만 빠르게 찾기 위한 보조 패턴 (성능)
_DETERMINISTIC_HINTS = re.compile(
    r"\b\d{6}-?\d{7}\b"            # RRN/FRN
    r"|01[01679][-\.\s]?\d{3,4}[-\.\s]?\d{4}"  # mobile
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"  # email
)

# 한국어 동사/형용사·계사(이다) 활용형. 이름은 거의 이 형태로 끝나지 않음.
_VERB_LIKE_SUFFIXES = (
    # 하다 활용
    "하다", "하고", "하여", "하지", "하니", "하면", "한다", "한", "할", "함",
    "하기", "하는", "하신", "하시", "하셨", "하셔", "하게", "하며", "하면서",
    "했다", "했고", "했지", "했음", "했으며",
    # 되다 활용
    "되다", "되고", "되어", "되지", "되니", "되면", "된다", "된", "될", "됨",
    "되기", "되는", "되며", "되었",
    # 드리다 활용
    "드린", "드리는", "드리고", "드립니다", "드린다", "드리며",
    # 이다 계사 + 명사화 (단계임/사실임/현실임 등)
    "임", "임을", "임에", "임으로", "임에도", "임이",
    "인", "인지", "인데", "인가", "이라",
)


def _looks_like_verb_form(token: str) -> bool:
    """Heuristic: True if ``token`` ends with a common Korean verb/adj ending."""
    return any(token.endswith(s) for s in _VERB_LIKE_SUFFIXES)


# 행정구역 접미사. "경기도", "성남시", "가평군" 등이 surname-starting 2~3자
# 토큰으로 보이지만 사람 이름은 거의 이 형태로 끝나지 않는다. 단, 명시적
# field-label-before 가 있으면 override (드물게라도 가능성을 보존).
_ADMIN_UNIT_CHARS: frozenset[str] = frozenset(
    {"시", "군", "구", "도", "읍", "면", "리"}
)
_STREET_SUFFIXES: tuple[str, ...] = ("대로", "로", "길")


def _looks_like_admin_unit(raw: str) -> bool:
    return len(raw) >= 2 and raw[-1] in _ADMIN_UNIT_CHARS


def _looks_like_street_name(raw: str) -> bool:
    return len(raw) >= 3 and any(raw.endswith(s) for s in _STREET_SUFFIXES)


def detect(text: str) -> Iterator[DetectionResult]:
    """Yield PERSON detections.

    Two-pass strategy:
      Pass A: extract candidates, score them, emit those above threshold,
              and register into a per-document NameDictionary.
      Pass B: rescan candidates that were below threshold; if the (stem) is
              now in the dictionary, emit with boosted confidence.
    """
    yield from _detect_with_dict(text, NameDictionary())


def _detect_with_dict(
    text: str, name_dict: NameDictionary
) -> Iterator[DetectionResult]:
    deterministic_spans = [
        (m.start(), m.end()) for m in _DETERMINISTIC_HINTS.finditer(text)
    ]
    threshold = 0.50

    pending: list[tuple[NameCandidate, float, list[str], str | None]] = []
    # ------ Pass A
    for m in _CANDIDATE.finditer(text):
        raw = m.group(1)
        label_before = _label_before(text, m.start())
        # Reject raw tokens that match an agency in the dictionary, or look
        # like an administrative-unit name (경기도, 성남시, 가평군) — unless
        # a person-field label is right before.
        if not label_before:
            # Reject any token that is a known agency (full or abbreviation),
            # district, province, or street/admin-unit by suffix shape.
            if (is_agency(raw)
                    or normalize_agency(raw) is not None
                    or is_province(raw) or is_district(raw)
                    or _looks_like_admin_unit(raw)
                    or _looks_like_street_name(raw)):
                continue
        # Try stripping a trailing particle to get the bare name
        stem, particle = strip_trailing_particle(raw)
        if len(stem) < 2 or len(stem) > 4:
            continue
        if is_common_word(stem):
            continue
        # Skip tokens that are themselves dictionary words (field label,
        # title, agency) — those are infrastructure markers, not names.
        if is_field_label(stem) or is_title(stem) or is_agency(stem):
            continue
        # Skip tokens that look like Korean verb/adjective conjugations.
        if _looks_like_verb_form(stem):
            continue
        # Heuristic: skip tokens without any leading surname unless the
        # field label is right before (we'll let the scorer decide).
        sp = surname_prefix_len(stem)
        if sp == 0 and not label_before:
            continue

        cand_start = m.start()
        cand_end = m.start() + len(stem)
        cand = NameCandidate(name=stem, start=cand_start, end=cand_end)
        det_nearby = _is_within(deterministic_spans, cand_start, window=25)
        score = score_candidate(
            text, cand,
            deterministic_nearby=det_nearby,
            name_dictionary_boost=name_dict.boost_for(stem),
        )
        if score.value >= threshold:
            name_dict.add(
                stem, score.value, (cand_start, cand_end), score.evidence
            )
            yield _emit(cand, particle, score.value, score.evidence)
        else:
            pending.append((cand, score.value, score.evidence, particle))

    # ------ Pass B: re-score pending using the now-populated dictionary
    for cand, _score_a, ev_a, particle in pending:
        boost = name_dict.boost_for(cand.name)
        if boost <= 0:
            continue
        rescored = score_candidate(
            text, cand,
            deterministic_nearby=_is_within(
                deterministic_spans, cand.start, window=25
            ),
            name_dictionary_boost=boost,
        )
        if rescored.value >= threshold:
            yield _emit(cand, particle, rescored.value, rescored.evidence)


from k_pii.dictionaries.field_labels import FIELD_LABELS_NAME


def _label_before(text: str, start: int) -> bool:
    head = text[max(0, start - 10): start]
    return any(lbl in head for lbl in FIELD_LABELS_NAME)


def _is_within(
    spans: Iterable[tuple[int, int]], pos: int, window: int = 25
) -> bool:
    for s, e in spans:
        if abs(s - pos) <= window or abs(e - pos) <= window:
            return True
    return False


def _emit(
    cand: NameCandidate,
    particle: str | None,
    score: float,
    evidence: list[str],
) -> DetectionResult:
    return DetectionResult(
        label=LABEL,
        text=cand.name,
        start=cand.start,
        end=cand.end,
        risk_level=RiskLevel.HIGH,
        confidence=score,
        evidence=evidence,
        legal_basis=LEGAL_BASIS,
        extra={
            "category": CATEGORY,
            "particle": particle,
        },
    )
