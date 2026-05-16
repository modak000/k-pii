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
from k_pii.context.name_origin import classify_name_origin
from k_pii.context.name_syllables import name_shape_bonus
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
    # 형용사 관형형 / 활용형 (강한·이상한·민감한 등 — surname-시작 2~3자 빈출)
    "운", "운데", "운지",         # 즐거운·괜찮은
    "라운", "로운", "스러운",      # 사랑스러운·풍요로운
    "이다", "이며", "이지만", "이라서",
    # 부사형
    "히",                         # 분명히·정확히 (단, 명사 부분 보존)
    # 어미 자주 끝
    "에서", "에는", "에도", "에게",
)


# 부분 가명 (이미 가명화된 표기) — PII 가 아니므로 거부
# "박씨", "정모", "이씨", "김군", "박양", "강씨" 등
_ANONYMIZED_MARKERS: frozenset[str] = frozenset({
    "씨", "모", "군", "양",
})


def _looks_like_anonymized(raw: str) -> bool:
    """길이 2자 + 끝 글자가 가명 마커 → 이미 익명화된 표기."""
    return len(raw) == 2 and raw[-1] in _ANONYMIZED_MARKERS


# 한국어 명사 접미사 / 복수 표지 — 사람 이름에는 거의 안 등장
# - 들 (복수: 사람들·배우들·국민들·우리들)
# - 성 (성격·가능성·정확성·매력·생산성)
# - 력 (연기력·실력·매력·동력·체력) — 단, "력" 단독 글자가 일부 이름에 있음
# - 감 (정의감·만족감·소외감·책임감·기대감)
# - 률 (성공률·시청률·확률)
# - 도 (정확도·만족도) — 단, 행정 단위 "도" 와 충돌 — admin_unit 에서 이미 처리
# - 적 (긍정적·일반적·전반적) — 형용사 접미사
_NOUN_SUFFIXES_FORBIDDEN: tuple[str, ...] = (
    "들", "성", "력", "감", "률", "적",
)


def _looks_like_common_noun_suffix(raw: str) -> bool:
    """3자+ 토큰 끝이 일반 명사 접미사면 True (예: 사람들·연기력·매력·기대감)."""
    return len(raw) >= 3 and any(raw.endswith(s) for s in _NOUN_SUFFIXES_FORBIDDEN)


# 한국어 동사 어간 빈출 패턴 — "다" 없이 종결되어 candidate 가 매칭되는 형태
# 예: "나오", "만드", "추정되", "재미있", "흘러내리"
# 끝이 *어간 + 종결* 패턴 (오/되/있/지/리/하/가/와/와) 인 3자+ 토큰 페널티
_VERB_STEM_FINAL_PATTERNS: tuple[str, ...] = (
    "추정되", "재미있", "재밌",
    "나오", "들어가", "들어와",
    "만드", "만들", "만나", "흐르",
)


def _looks_like_verb_stem(raw: str) -> bool:
    return any(raw.endswith(p) for p in _VERB_STEM_FINAL_PATTERNS)


# 토큰 안에 직책이 *포함* 된 경우 — 예: "강회장이", "김의원이", "박교수가"
# stem 끝 부분이 직책이면 직책 부분 떼고 앞부분만 PERSON 후보로 처리.
_EMBEDDED_TITLE_SUFFIXES: tuple[str, ...] = (
    "회장", "사장", "이사", "대표", "대표이사", "부사장", "전무", "상무",
    "본부장", "팀장", "실장", "센터장", "원장", "지점장",
    "의원", "장관", "차관", "총리", "비서관", "보좌관",
    "교수", "박사", "강사",
    "의사", "약사", "간호사", "한의사",
    "변호사", "검사", "판사", "법무사",
    "대사", "총영사", "영사",
    "선수", "감독", "코치",
    "기자", "PD", "작가",
)


def _split_embedded_title(stem: str) -> tuple[str, str | None]:
    """``"강회장"`` → ``("강", "회장")``. 분리 안 되면 ``(stem, None)``.

    조건: stem 끝이 직책으로 끝나야 하고, 앞부분이 1~3자 한글이어야 한다.
    """
    for suf in sorted(_EMBEDDED_TITLE_SUFFIXES, key=len, reverse=True):
        if stem.endswith(suf) and len(stem) > len(suf):
            front = stem[: -len(suf)]
            if 1 <= len(front) <= 3 and all("가" <= c <= "힣" for c in front):
                return front, suf
    return stem, None


# 이름 끝 음절 자주 등장 패턴 — recall 보강용 보너스 (강한 신호 아님)
_NAME_FINAL_SYLLABLES: frozenset[str] = frozenset({
    # 남자 이름 빈출
    "수", "호", "준", "훈", "진", "민", "철", "혁", "한", "현",
    "성", "석", "환", "식", "원", "운", "웅", "용", "영", "정",
    "재", "재", "균", "근", "광", "관", "구", "규", "기", "길",
    "동", "두", "찬", "철", "충", "탁", "태", "택", "필", "필",
    # 여자 이름 빈출
    "지", "희", "은", "정", "영", "미", "현", "주", "경", "선",
    "연", "린", "린", "옥", "원", "유", "윤", "이", "인", "임",
    "자", "전", "정", "조", "주", "지", "지", "진", "참", "채",
    "혜", "화", "효", "후", "흠", "흥",
    # 중성
    "아", "야", "예", "오", "우", "원", "유", "은", "이",
})


def _has_name_like_final(stem: str) -> bool:
    """이름 끝 글자가 *흔한 이름 글자* 면 True (약한 신호)."""
    return len(stem) >= 2 and stem[-1] in _NAME_FINAL_SYLLABLES


# 나이·성별·신원 단서 — 이름 인접 시 PERSON 확신 ↑
# "홍길동(32세)", "홍길동 32세", "홍길동, 남자", "홍길동(남)"
# "남"/"여" 단독은 동사·일반어 (남기다/여기다) 충돌 우려 → 괄호 안일 때만 허용
_AGE_GENDER_PATTERN = re.compile(
    r"\s*\(\s*(?:\d{1,3}\s*세|남자|여자|남|여|미혼|기혼)\s*\)"
    r"|\s*,\s*(?:\d{1,3}\s*세|남자|여자|미혼|기혼)"
    r"|\s+\d{1,3}\s*세\b"
)


def _has_age_or_gender_after(text: str, end: int, window: int = 12) -> str | None:
    tail = text[end: end + window]
    m = _AGE_GENDER_PATTERN.match(tail)
    if m:
        return m.group(0).strip()
    return None


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
    emitted: list[tuple] = []  # (cand, particle, score, evidence)
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
        # 부분 가명 표기 (박씨/이모/김군) — 이미 익명화된 표기이므로 거부
        if _looks_like_anonymized(stem):
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
        # Skip 복수형 (X들) / 명사 접미사 (X성·X력·X감 등) — 사람 이름 아님
        if _looks_like_common_noun_suffix(stem):
            continue
        # Skip 동사 어간 패턴 (나오·추정되·재미있 등)
        if _looks_like_verb_stem(stem):
            continue

        # Embedded title — "강회장이" 같이 토큰 안에 직책이 들어있으면
        # 직책 부분 떼고 앞부분 (성+이름 후보) 만 사용
        embedded_title: str | None = None
        original_stem = stem
        front, title_suffix = _split_embedded_title(stem)
        if title_suffix and len(front) >= 2:
            stem = front
            embedded_title = title_suffix
        elif title_suffix and len(front) == 1:
            # 1자 + 직책 (예: "강회장") — 1자 단독은 신뢰도 너무 낮음 → 거부
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
        # 추가 신호: 토큰 안 직책, 이름끝 음절, 나이/성별 인접, 음절 통계
        extra_signals: list[str] = []
        extra_score = 0.0
        if embedded_title:
            extra_score += 0.35
            extra_signals.append(f"pos:embedded_title({embedded_title})")
        if _has_name_like_final(stem):
            extra_score += 0.10
            extra_signals.append("pos:name_final_syllable")
        # Method 1: 음절 통계 likelihood
        shape_bonus = name_shape_bonus(stem)
        if shape_bonus > 0:
            extra_score += shape_bonus
            extra_signals.append(f"pos:name_likelihood({shape_bonus:.2f})")
        # 원본 토큰 끝(particle 포함) 다음 위치에서 나이/성별 단서
        age_gender = _has_age_or_gender_after(text, m.end())
        if age_gender:
            extra_score += 0.30
            extra_signals.append(f"pos:age_gender_after({age_gender})")
        score = score_candidate(
            text, cand,
            deterministic_nearby=det_nearby,
            name_dictionary_boost=name_dict.boost_for(stem),
        )
        # 추가 신호 합산
        total_value = min(1.0, score.value + extra_score)
        total_evidence = list(score.evidence) + extra_signals

        # 동적 threshold:
        # - 2자 토큰: 끝 글자가 *이름 글자가 아니면* 엄격 (+0.10)
        # - 3자+ 토큰: 기본 임계값
        # - field_label 가 직전에 있거나 직책이 명시되면 기본 임계값
        eff_threshold = threshold
        if (len(stem) == 2
                and not _has_name_like_final(stem)
                and not label_before
                and not embedded_title
                and "pos:field_label" not in " ".join(total_evidence)
                and "pos:title" not in " ".join(total_evidence)):
            eff_threshold = threshold + 0.10
            total_evidence.append("threshold:strict_short")

        if total_value >= eff_threshold:
            name_dict.add(
                stem, total_value, (cand_start, cand_end), total_evidence
            )
            emitted.append((cand, particle, total_value, total_evidence))
        else:
            pending.append((cand, total_value, total_evidence, particle))

    # ------ Method 2: 같은 문장 내 후보 상호 보강 (Co-occurrence Boost)
    # Pass A 에서 *높은 신뢰* PERSON 이 잡힌 문장의 *약한 후보* 들도 +0.15
    # 보강 후 임계값 재평가.
    sentence_boundaries = _find_sentence_boundaries(text)
    strong_sentence_ids: set[int] = set()
    for cand, _p, score_v, _ev in emitted:
        if score_v >= 0.70:
            sid = _sentence_id(cand.start, sentence_boundaries)
            strong_sentence_ids.add(sid)

    co_boosted: list[tuple] = []
    still_pending: list[tuple] = []
    for cand, score_v, ev, particle in pending:
        sid = _sentence_id(cand.start, sentence_boundaries)
        if sid in strong_sentence_ids:
            boosted_score = min(1.0, score_v + 0.15)
            boosted_ev = list(ev) + ["pos:co_occurrence_in_sentence"]
            if boosted_score >= threshold:
                co_boosted.append((cand, particle, boosted_score, boosted_ev))
                name_dict.add(cand.name, boosted_score,
                              (cand.start, cand.end), boosted_ev)
                continue
        still_pending.append((cand, score_v, ev, particle))

    # 모두 emit
    for cand, particle, score_v, ev in emitted + co_boosted:
        yield _emit(cand, particle, score_v, ev)

    # ------ Pass B: re-score remaining pending using the now-populated dictionary
    for cand, _score_a, ev_a, particle in still_pending:
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
    origin = classify_name_origin(cand.name)
    return DetectionResult(
        label=LABEL,
        text=cand.name,
        start=cand.start,
        end=cand.end,
        risk_level=RiskLevel.HIGH,
        confidence=score,
        evidence=evidence + [f"origin:{origin}"],
        legal_basis=LEGAL_BASIS,
        extra={
            "category": CATEGORY,
            "particle": particle,
            "origin": origin,
        },
    )


# ---------------------------------------------------------------------
# Method 2 보조: 문장 경계 (마침표·줄바꿈·물음표·느낌표)
# ---------------------------------------------------------------------

def _find_sentence_boundaries(text: str) -> list[int]:
    """Return list of sentence start offsets (sorted)."""
    starts = [0]
    for i, ch in enumerate(text):
        if ch in ".!?\n":
            if i + 1 < len(text):
                starts.append(i + 1)
    return starts


def _sentence_id(pos: int, boundaries: list[int]) -> int:
    """Return the sentence index (0-based) containing `pos`."""
    import bisect
    idx = bisect.bisect_right(boundaries, pos) - 1
    return max(0, idx)
