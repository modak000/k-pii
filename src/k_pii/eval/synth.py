"""합성 공문서 생성기 — Precision/Recall 측정을 위한 라벨 셋.

원칙:
- **외부 의존성 없음** (Faker 사용 금지). Python 표준 라이브러리 ``random`` 만 사용.
- 합성 PII 는 손계산으로 검증된 valid 예시들로부터 random.choice. 체크섬을
  통과하는 값만 사용 (RRN/사업자/카드 등).
- 각 문서는 ``GoldSpan`` (정답 라벨 + span) 리스트와 함께 생성됨.
- 템플릿은 한국 공공 부문 문서 4종: 결재공문, 민원 답변서, 인사 평가서, 회의록.

Legal basis: 본 합성 데이터는 평가용으로만 사용 — 실제 인물·기관과 무관.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

# ---------------- 검증된 합성 PII 풀 (체크섬/포맷 OK) ----------------------

# RRN: 모두 체크섬 valid (손계산 또는 라이브러리로 확인)
_RRN_SAMPLES = [
    "880101-1234568", "950101-2345676", "770515-1234565",
    "020405-3000007", "850729-2123456", "660312-1234562",
]

_PHONE_MOBILE = [
    "010-1234-5678", "010-9876-5432", "011-222-3333",
    "010 1111 2222", "01088889999",
]

_PHONE_LANDLINE = [
    "02-123-4567", "02-7654-3210", "031-234-5678", "051-987-6543",
]

# 사업자번호: 체크섬 valid
_BIZREG_SAMPLES = ["123-45-67890", "1234567893", "211-87-22653"]

_EMAIL_SAMPLES = [
    "kim.minsu@example.go.kr", "yhpark@gov.kr",
    "hong.gildong@gmail.com", "applicant@example.com",
]

_VEHICLE_SAMPLES = ["12가3456", "87나4321", "123다4567", "44마7890"]

_ADDR_ROAD = [
    "서울특별시 종로구 세종대로 209",
    "경기도 성남시 분당구 정자로 1",
    "부산광역시 해운대구 우동로 123",
]

_ADDR_JIBUN = [
    "서울특별시 강남구 역삼동 123",
    "경기도 가평군 청평면 청평리 45-6",
]

# 이름 풀 (성씨 + 이름 1~2글자) — 공공기관과의 우연 충돌을 피하려고 흔한 조합 사용
_NAMES = [
    "홍길동", "김민수", "박영수", "이수정", "최지훈", "정혜진",
    "강도현", "남궁민수", "황보경", "송지효",
]

_TITLES_GOV_POOL = ["과장", "사무관", "주무관", "서기관", "국장", "팀장"]
_TITLES_POLICE_POOL = ["경감", "경위", "경정", "총경"]
_TITLES_FIRE_POOL = ["소방위", "소방경", "소방령"]
_TITLES_MILITARY_POOL = ["대위", "소령", "대령"]
_AGENCIES_POOL = ["기획재정부", "행정안전부", "보건복지부", "법무부", "교육부"]
_AGENCY_ABBREV_POOL = ["기재부", "행안부", "복지부", "국토부", "과기정통부"]


@dataclass
class GoldSpan:
    label: str
    start: int
    end: int
    text: str


@dataclass
class GoldDocument:
    text: str
    spans: list[GoldSpan] = field(default_factory=list)
    template: str = ""


# ---------------- 템플릿 ----------------------

def _gov_decree(rnd: random.Random) -> GoldDocument:
    """결재 공문 템플릿."""
    agency = rnd.choice(_AGENCIES_POOL)
    name = rnd.choice(_NAMES)
    title = rnd.choice(_TITLES_GOV_POOL)
    rrn = rnd.choice(_RRN_SAMPLES)
    phone = rnd.choice(_PHONE_MOBILE)
    email = rnd.choice(_EMAIL_SAMPLES)
    addr = rnd.choice(_ADDR_ROAD)

    parts: list[tuple[str, str | None]] = [
        (f"[{agency} 결재공문]\n\n", None),
        ("수신자: ", None),
        (rnd.choice(_AGENCIES_POOL), "AGENCY"),
        (" 장관\n", None),
        ("참조: ", None),
        (name, "PERSON"),
        (f" {title}\n\n", None),
        ("신청인: ", None),
        (rnd.choice(_NAMES), "PERSON"),
        ("\n주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n연락처: ", None),
        (phone, "PHONE"),
        ("\n이메일: ", None),
        (email, "EMAIL"),
        ("\n주소: ", None),
        (addr, "ADDRESS"),
        ("\n\n위 사항을 확인하여 주시기 바랍니다.\n", None),
    ]
    # AGENCY 는 PII 가 아니므로 정답에서 제외 (이름 탐지가 헷갈리지 않는지 점검용)
    return _assemble(parts, template="gov_decree", pii_labels={
        "PERSON", "RRN", "PHONE", "EMAIL", "ADDRESS",
    })


def _civil_petition(rnd: random.Random) -> GoldDocument:
    """민원 답변서 템플릿."""
    name = rnd.choice(_NAMES)
    phone = rnd.choice(_PHONE_MOBILE)
    addr = rnd.choice(_ADDR_JIBUN)
    rrn = rnd.choice(_RRN_SAMPLES)

    parts = [
        ("[민원 답변서]\n\n", None),
        ("민원인: ", None),
        (name, "PERSON"),
        ("\n주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n연락처: ", None),
        (phone, "PHONE"),
        ("\n주소: ", None),
        (addr, "ADDRESS"),
        ("\n\n귀하의 민원에 다음과 같이 답변드립니다.\n", None),
        (name, "PERSON"),  # second occurrence — accumulation must pick this up
        (" 님께서 제출하신 사항은 관련 부서에서 검토 중이며, ", None),
        ("처리 결과는 통보드릴 예정입니다.\n", None),
    ]
    return _assemble(parts, template="civil_petition", pii_labels={
        "PERSON", "RRN", "PHONE", "ADDRESS",
    })


def _hr_review(rnd: random.Random) -> GoldDocument:
    """인사 평가서 템플릿."""
    name = rnd.choice(_NAMES)
    title = rnd.choice(_TITLES_GOV_POOL)
    rrn = rnd.choice(_RRN_SAMPLES)
    email = rnd.choice(_EMAIL_SAMPLES)
    phone = rnd.choice(_PHONE_LANDLINE)

    parts = [
        ("[인사 평가서]\n\n", None),
        ("성명: ", None),
        (name, "PERSON"),
        (f" ({title})\n", None),
        ("주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n사무실 번호: ", None),
        (phone, "PHONE"),
        ("\n이메일: ", None),
        (email, "EMAIL"),
        ("\n\n평가 의견: 본인은 성실하게 직무를 수행함.\n", None),
    ]
    return _assemble(parts, template="hr_review", pii_labels={
        "PERSON", "RRN", "PHONE", "EMAIL",
    })


def _meeting_minutes(rnd: random.Random) -> GoldDocument:
    """회의록 템플릿."""
    a = rnd.choice(_NAMES)
    b = rnd.choice([n for n in _NAMES if n != a])
    title_a = rnd.choice(_TITLES_GOV_POOL)
    title_b = rnd.choice(_TITLES_GOV_POOL)
    vehicle = rnd.choice(_VEHICLE_SAMPLES)

    parts = [
        ("[회의록]\n\n", None),
        ("참석자: ", None),
        (a, "PERSON"),
        (f" {title_a}, ", None),
        (b, "PERSON"),
        (f" {title_b}\n\n", None),
        ("논의 사항:\n", None),
        ("1. 청사 출입 차량 ", None),
        (vehicle, "VEHICLE"),
        ("의 통행 허용 여부.\n", None),
        ("2. 다음 주 보고회 일정 협의.\n", None),
    ]
    return _assemble(parts, template="meeting_minutes", pii_labels={
        "PERSON", "VEHICLE",
    })


def _police_report(rnd: random.Random) -> GoldDocument:
    """경찰서 사건 보고서 템플릿 (특정직 직급 + 약칭)."""
    name = rnd.choice(_NAMES)
    rank = rnd.choice(["경감", "경위", "경정", "총경"])
    rrn = rnd.choice(_RRN_SAMPLES)
    phone = rnd.choice(_PHONE_MOBILE)
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    docnum = f"{abbrev}-수사과-2024-{rnd.randint(10000, 99999)}"

    parts = [
        ("[경찰 사건 처리 보고서]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n수사관: ", None),
        (name, "PERSON"),
        (f" {rank}\n\n", None),
        ("피의자 정보:\n", None),
        ("성명: ", None),
        (rnd.choice([n for n in _NAMES if n != name]), "PERSON"),
        ("\n주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n연락처: ", None),
        (phone, "PHONE"),
        ("\n\n조사 내용: 본 건은 일반 조사 단계임.\n", None),
    ]
    return _assemble(parts, template="police_report", pii_labels={
        "PERSON", "RRN", "PHONE", "DOC_ID",
    })


def _fire_dispatch(rnd: random.Random) -> GoldDocument:
    """소방 출동 보고서 템플릿."""
    name = rnd.choice(_NAMES)
    rank = rnd.choice(_TITLES_FIRE_POOL)
    addr = rnd.choice(_ADDR_ROAD)
    phone = rnd.choice(_PHONE_LANDLINE)

    parts = [
        ("[소방 출동 보고]\n\n", None),
        ("출동대장: ", None),
        (name, "PERSON"),
        (f" {rank}\n", None),
        ("신고자: ", None),
        (rnd.choice([n for n in _NAMES if n != name]), "PERSON"),
        ("\n신고지: ", None),
        (addr, "ADDRESS"),
        ("\n연락처: ", None),
        (phone, "PHONE"),
        ("\n\n상황 종료 보고서 첨부.\n", None),
    ]
    return _assemble(parts, template="fire_dispatch", pii_labels={
        "PERSON", "ADDRESS", "PHONE",
    })


_TEMPLATES: tuple[Callable[[random.Random], GoldDocument], ...] = (
    _gov_decree,
    _civil_petition,
    _hr_review,
    _meeting_minutes,
    _police_report,
    _fire_dispatch,
)


def _assemble(
    parts: list[tuple[str, str | None]],
    template: str,
    pii_labels: set[str],
) -> GoldDocument:
    text_parts: list[str] = []
    spans: list[GoldSpan] = []
    cursor = 0
    for chunk, label in parts:
        if label is not None and label in pii_labels:
            spans.append(GoldSpan(
                label=label,
                start=cursor,
                end=cursor + len(chunk),
                text=chunk,
            ))
        text_parts.append(chunk)
        cursor += len(chunk)
    return GoldDocument(text="".join(text_parts), spans=spans, template=template)


def generate_document(seed: int | None = None, template: str | None = None) -> GoldDocument:
    """Return one synthetic document with gold-standard PII spans.

    ``template``: optional template name; if omitted one is picked at random.
    """
    rnd = random.Random(seed)
    if template is None:
        fn = rnd.choice(_TEMPLATES)
    else:
        mapping = {
            "gov_decree": _gov_decree,
            "civil_petition": _civil_petition,
            "hr_review": _hr_review,
            "meeting_minutes": _meeting_minutes,
            "police_report": _police_report,
            "fire_dispatch": _fire_dispatch,
        }
        if template not in mapping:
            raise ValueError(f"Unknown template: {template}")
        fn = mapping[template]
    return fn(rnd)


def generate_corpus(n: int, seed: int = 0) -> list[GoldDocument]:
    rnd = random.Random(seed)
    out: list[GoldDocument] = []
    for i in range(n):
        # Reseed deterministically per doc so the corpus is reproducible
        out.append(generate_document(seed=rnd.randint(0, 10**9)))
    return out
