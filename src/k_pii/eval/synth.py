"""합성 공문서 생성기 — Precision/Recall 측정을 위한 라벨 셋.

원칙:
- **외부 의존성 없음** (Faker 사용 금지). Python 표준 라이브러리 ``random`` 만 사용.
- 합성 PII 는 손계산으로 검증된 valid 예시들로부터 random.choice. 체크섬을
  통과하는 값만 사용 (RRN/사업자/카드 등).
- 각 문서는 ``GoldSpan`` (정답 라벨 + span) 리스트와 함께 생성됨.
- 템플릿은 한국 공공 부문 문서 6종: 결재공문, 민원 답변서, 인사 평가서,
  회의록, 경찰 보고서, 소방 출동 보고서.
- **풍부화 정책** — 단순 양식이 아닌 실제 공문서 분량/표현:
  본문 다단락 + 붙임·법령 인용·서명 라인 + 노이즈 문장 (PII 아닌 일반 텍스트).

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

_PHONE_REPRESENTATIVE = ["1588-1234", "1644-5566", "1577-0000", "1899-7777"]

# 사업자번호: 체크섬 valid
_BIZREG_SAMPLES = ["123-45-67890", "1234567893", "211-87-22653"]

_EMAIL_SAMPLES = [
    "kim.minsu@example.go.kr", "yhpark@gov.kr",
    "hong.gildong@gmail.com", "applicant@example.com",
    "petition@seoul.go.kr", "noreply@minwon.go.kr",
]

_VEHICLE_SAMPLES = ["12가3456", "87나4321", "123다4567", "44마7890"]

_ADDR_ROAD = [
    "서울특별시 종로구 세종대로 209",
    "경기도 성남시 분당구 정자로 1",
    "부산광역시 해운대구 우동로 123",
    "서울특별시 강남구 테헤란로 152",
    "인천광역시 연수구 컨벤시아대로 165",
]

_ADDR_JIBUN = [
    "서울특별시 강남구 역삼동 123",
    "경기도 가평군 청평면 청평리 45-6",
    "서울특별시 마포구 합정동 372-1",
]

# 이름 풀 (성씨 + 이름 1~2글자) — 공공기관과의 우연 충돌을 피하려고 흔한 조합 사용
_NAMES = [
    "홍길동", "김민수", "박영수", "이수정", "최지훈", "정혜진",
    "강도현", "남궁민수", "황보경", "송지효",
    "윤서연", "임도윤", "조하늘", "장미경", "한지원",
]

_TITLES_GOV_POOL = ["과장", "사무관", "주무관", "서기관", "국장", "팀장"]
_TITLES_POLICE_POOL = ["경감", "경위", "경정", "총경"]
_TITLES_FIRE_POOL = ["소방위", "소방경", "소방령"]
_TITLES_MILITARY_POOL = ["대위", "소령", "대령"]
_AGENCIES_POOL = ["기획재정부", "행정안전부", "보건복지부", "법무부", "교육부"]
_AGENCY_ABBREV_POOL = ["기재부", "행안부", "복지부", "국토부", "과기정통부"]

# 노이즈 — PII 가 아닌 본문 문장 (실제 공문서에서 자주 등장)
_BOILERPLATE_LAW_CITATIONS = [
    "개인정보보호법 제24조의2",
    "개인정보보호법 제29조 안전조치의무",
    "행정절차법 제20조",
    "민원처리에 관한 법률 제18조",
    "공공기관의 정보공개에 관한 법률 제11조",
    "행정심판법 제27조",
]

_DECISION_PHRASES = [
    "관련 법령에 따라 다음과 같이 처리하였음을 알려드립니다.",
    "검토 결과 다음과 같은 의견을 회신 드립니다.",
    "본 건은 소관 부서와 협의를 거쳐 다음과 같이 결정되었습니다.",
    "관계 법령과 본 기관 내부 규정을 종합적으로 고려하여 회신 드립니다.",
]

_ATTACHMENT_PHRASES = [
    "[붙임]\n1. 신청서 사본 1부\n2. 증빙 서류 1부\n3. 처리 결과 안내 1부.  끝.",
    "[붙임]\n1. 처리 내역서 1부\n2. 관련 자료 1부.  끝.",
    "[붙임]\n1. 회의 자료 1부\n2. 참석자 명단 1부\n3. 결의 사항 정리 1부.  끝.",
]

_SIGNOFF_PHRASES = [
    "끝까지 읽어 주셔서 감사합니다.",
    "추가 문의 사항이 있으시면 담당자에게 연락 주시기 바랍니다.",
    "본 회신이 도움이 되시길 바라며, 항상 건강하시기 바랍니다.",
]


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
    """결재 공문 템플릿 — 정부 부처 → 부처 결재 라인."""
    agency = rnd.choice(_AGENCIES_POOL)
    drafter = rnd.choice(_NAMES)
    drafter_title = rnd.choice(_TITLES_GOV_POOL)
    reviewer = rnd.choice([n for n in _NAMES if n != drafter])
    reviewer_title = rnd.choice(["과장", "국장"])
    approver = rnd.choice([n for n in _NAMES if n not in {drafter, reviewer}])
    approver_title = "장관"
    applicant = rnd.choice(_NAMES)
    rrn = rnd.choice(_RRN_SAMPLES)
    phone = rnd.choice(_PHONE_MOBILE)
    rep_phone = rnd.choice(_PHONE_REPRESENTATIVE)
    email = rnd.choice(_EMAIL_SAMPLES)
    addr = rnd.choice(_ADDR_ROAD)
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    docnum = f"{abbrev}-총무과-2026-{rnd.randint(10000, 99999)}"
    law = rnd.choice(_BOILERPLATE_LAW_CITATIONS)
    decision = rnd.choice(_DECISION_PHRASES)

    parts: list[tuple[str, str | None]] = [
        (f"[{agency} 결재공문]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n시행일자: 2026년 5월 20일\n", None),
        ("수신: 각 부서장\n", None),
        ("참조: ", None),
        (reviewer, "PERSON"),
        (f" {reviewer_title}\n\n", None),
        ("□ 제목: 민원 처리 협조 요청 건\n\n", None),
        ("□ 신청 내용\n", None),
        ("  - 신청인: ", None),
        (applicant, "PERSON"),
        (" (개인)\n", None),
        ("  - 주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n  - 연락처: ", None),
        (phone, "PHONE"),
        ("\n  - 이메일: ", None),
        (email, "EMAIL"),
        ("\n  - 주소: ", None),
        (addr, "ADDRESS"),
        ("\n\n□ 처리 의견\n", None),
        (f"  {decision}\n", None),
        (f"  본 건은 「{law}」에 따라 처리되며, ", None),
        ("우리 부서 관련 사항을 적극 협조해 주시기 바랍니다.\n\n", None),
        ("□ 회신 방법\n", None),
        ("  - 대표전화: ", None),
        (rep_phone, "PHONE"),
        ("\n  - 담당자: ", None),
        (drafter, "PERSON"),
        (f" {drafter_title}\n\n", None),
        ("□ 결재 라인\n", None),
        ("  기안자 ", None),
        (drafter, "PERSON"),
        (f" {drafter_title} → 검토 ", None),
        (reviewer, "PERSON"),
        (f" {reviewer_title} → 결재 ", None),
        (approver, "PERSON"),
        (f" {approver_title}\n\n", None),
        (rnd.choice(_ATTACHMENT_PHRASES), None),
    ]
    return _assemble(parts, template="gov_decree", pii_labels={
        "PERSON", "RRN", "PHONE", "EMAIL", "ADDRESS", "DOC_ID",
    })


def _civil_petition(rnd: random.Random) -> GoldDocument:
    """민원 답변서 템플릿 — 시청/구청 → 시민 회신."""
    petitioner = rnd.choice(_NAMES)
    phone = rnd.choice(_PHONE_MOBILE)
    addr = rnd.choice(_ADDR_JIBUN)
    rrn = rnd.choice(_RRN_SAMPLES)
    email = rnd.choice(_EMAIL_SAMPLES)
    handler = rnd.choice([n for n in _NAMES if n != petitioner])
    handler_title = rnd.choice(_TITLES_GOV_POOL)
    rep_phone = rnd.choice(_PHONE_REPRESENTATIVE)
    petition_num = f"민원-2026-{rnd.randint(10000, 99999)}"
    law = rnd.choice(_BOILERPLATE_LAW_CITATIONS)
    received = f"2026년 0{rnd.randint(1, 5)}월 {rnd.randint(10, 28)}일"
    answered = f"2026년 0{rnd.randint(1, 5)}월 {rnd.randint(10, 28)}일"
    decision = rnd.choice(_DECISION_PHRASES)

    parts = [
        ("[민원 답변서]\n\n", None),
        ("접수번호: ", None),
        (petition_num, "PETITION_ID"),
        ("\n접수일자: ", None),
        (received, None),
        ("\n회신일자: ", None),
        (answered, None),
        ("\n\n□ 민원인 정보\n", None),
        ("  - 성명: ", None),
        (petitioner, "PERSON"),
        ("\n  - 주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n  - 연락처: ", None),
        (phone, "PHONE"),
        ("\n  - 이메일: ", None),
        (email, "EMAIL"),
        ("\n  - 주소: ", None),
        (addr, "ADDRESS"),
        ("\n\n□ 민원 내용 (요약)\n", None),
        ("  귀하께서 제출하신 민원은 주차장 운영 관련 사항으로, ", None),
        ("관할 부서에서 현장 점검 후 결과를 회신해 드립니다.\n\n", None),
        ("□ 처리 결과\n", None),
        (f"  {decision}\n", None),
        (f"  본 건은 「{law}」 및 우리 시 「주차장 관리 조례」 제8조에 따라 ", None),
        ("다음과 같이 처리하였음을 알려드립니다:\n", None),
        ("  1) 현장 점검 결과 위반 사항 확인되어 시정 명령서 발부.\n", None),
        ("  2) 시정 기한: 회신일로부터 14일 이내.\n", None),
        ("  3) 미이행 시 「도로교통법」 제32조에 따라 추가 조치 예정.\n\n", None),
        ("□ 회신에 대한 이의가 있으신 경우\n", None),
        ("  회신서 수령일로부터 90일 이내에 행정심판을 제기하실 수 있습니다.\n", None),
        ("  자세한 사항은 우리 시 행정심판 안내 페이지를 참고해 주시기 바랍니다.\n\n", None),
        ("□ 담당자\n", None),
        ("  - 처리자: ", None),
        (handler, "PERSON"),
        (f" {handler_title}\n", None),
        ("  - 대표전화: ", None),
        (rep_phone, "PHONE"),
        ("\n\n", None),
        ("재차 안내드리자면 ", None),
        (petitioner, "PERSON"),  # second occurrence — accumulation must pick this up
        (" 님께서 제출하신 사항은 위와 같이 처리되었으며, ", None),
        ("처리 결과에 대한 만족도 조사가 별도로 발송될 예정입니다.\n\n", None),
        (rnd.choice(_SIGNOFF_PHRASES) + "\n", None),
    ]
    return _assemble(parts, template="civil_petition", pii_labels={
        "PERSON", "RRN", "PHONE", "EMAIL", "ADDRESS", "PETITION_ID",
    })


def _hr_review(rnd: random.Random) -> GoldDocument:
    """인사 평가서 템플릿 — 정부 부처 내부 평가."""
    employee = rnd.choice(_NAMES)
    title = rnd.choice(_TITLES_GOV_POOL)
    rrn = rnd.choice(_RRN_SAMPLES)
    email = rnd.choice(_EMAIL_SAMPLES)
    phone = rnd.choice(_PHONE_LANDLINE)
    addr = rnd.choice(_ADDR_ROAD)
    evaluator = rnd.choice([n for n in _NAMES if n != employee])
    evaluator_title = rnd.choice(["국장", "본부장"])
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    emp_id = rnd.randint(20180000, 20240999)
    docnum = f"{abbrev}-인사과-2026-{rnd.randint(10000, 99999)}"

    parts = [
        ("[인사 평가서]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n평가기간: 2025년 1월 1일 ~ 2025년 12월 31일\n\n", None),
        ("□ 피평가자 정보\n", None),
        ("  - 성명: ", None),
        (employee, "PERSON"),
        (f" ({title})\n", None),
        ("  - 주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n  - 사번: ", None),
        (str(emp_id), "EMPLOYEE_ID"),
        ("\n", None),
        ("  - 사무실 번호: ", None),
        (phone, "PHONE"),
        ("\n  - 이메일: ", None),
        (email, "EMAIL"),
        ("\n  - 자택 주소: ", None),
        (addr, "ADDRESS"),
        ("\n\n□ 직무 수행 평가\n", None),
        ("  1) 직무 지식: 우수 (S)\n", None),
        ("  2) 업무 추진력: 우수 (S)\n", None),
        ("  3) 협업 능력: 양호 (A)\n", None),
        ("  4) 책임감: 우수 (S)\n", None),
        ("  5) 조직 기여도: 양호 (A)\n\n", None),
        ("□ 평가 의견\n", None),
        ("  본인은 성실하게 직무를 수행하였으며, ", None),
        ("부여된 업무에 대하여 책임감 있게 임함. 특히 민원 응대 분야에서 ", None),
        ("탁월한 성과를 보였으며, 동료들과의 협력 관계도 원만함. ", None),
        ("향후 추가 교육 이수를 통하여 전문성 강화를 권고함.\n\n", None),
        ("□ 종합 의견 및 등급\n", None),
        ("  종합 등급: B+ (양호)\n", None),
        ("  승진 추천 여부: 차년도 검토 권고\n\n", None),
        ("□ 평가자\n", None),
        ("  - 평가자: ", None),
        (evaluator, "PERSON"),
        (f" {evaluator_title}\n", None),
        ("  - 평가일자: 2026년 1월 15일\n\n", None),
        ("평가 결과에 대한 이의 신청은 평가자에게 직접 또는 인사위원회를 통해 ", None),
        ("회신일로부터 7일 이내에 가능합니다.\n", None),
    ]
    return _assemble(parts, template="hr_review", pii_labels={
        "PERSON", "RRN", "PHONE", "EMAIL", "ADDRESS", "DOC_ID", "EMPLOYEE_ID",
    })


def _meeting_minutes(rnd: random.Random) -> GoldDocument:
    """회의록 템플릿 — 부서 정기 회의."""
    a = rnd.choice(_NAMES)
    b = rnd.choice([n for n in _NAMES if n != a])
    c = rnd.choice([n for n in _NAMES if n not in {a, b}])
    title_a = rnd.choice(_TITLES_GOV_POOL)
    title_b = rnd.choice(_TITLES_GOV_POOL)
    title_c = rnd.choice(_TITLES_GOV_POOL)
    vehicle = rnd.choice(_VEHICLE_SAMPLES)
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    docnum = f"{abbrev}-총무과-2026-{rnd.randint(10000, 99999)}"
    chairperson_phone = rnd.choice(_PHONE_LANDLINE)
    chairperson_email = rnd.choice(_EMAIL_SAMPLES)

    parts = [
        ("[회의록]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n회의일자: 2026년 5월 15일 (수) 14:00 ~ 16:00\n", None),
        ("회의장소: 본청 3층 회의실\n\n", None),
        ("□ 참석자\n", None),
        ("  - 의장: ", None),
        (a, "PERSON"),
        (f" {title_a}\n", None),
        ("  - 참석: ", None),
        (b, "PERSON"),
        (f" {title_b}, ", None),
        (c, "PERSON"),
        (f" {title_c}\n", None),
        ("  - 서기: 별도 지정자 없음 (의장 직접 기록)\n\n", None),
        ("□ 의제\n", None),
        ("  1) 청사 출입 차량 통행 허용 여부\n", None),
        ("  2) 다음 분기 보고회 일정 협의\n", None),
        ("  3) 인사 발령 후속 처리 협의\n\n", None),
        ("□ 논의 내용\n", None),
        ("  1) 청사 출입 차량 ", None),
        (vehicle, "VEHICLE"),
        ("의 통행 허용 건\n", None),
        ("     - 본 차량은 협력업체 소속으로, 보안 검토 후 출입 허가 의견.\n", None),
        ("     - 출입 시간은 평일 09:00 ~ 18:00 으로 제한.\n", None),
        ("     - 의결: 만장일치 가결.\n\n", None),
        ("  2) 다음 분기 보고회 일정\n", None),
        ("     - 일정: 2026년 8월 12일 (수) 14:00 ~ 17:00 (잠정).\n", None),
        ("     - 장소: 본청 5층 대회의실.\n", None),
        ("     - 의결: 추후 부서별 일정 취합 후 확정.\n\n", None),
        ("  3) 인사 발령 후속 처리\n", None),
        ("     - 신규 발령자 대상 OJT 진행 (담당: ", None),
        (b, "PERSON"),
        (f" {title_b}).\n", None),
        ("     - 인수인계 자료 표준화 검토.\n\n", None),
        ("□ 다음 회의\n", None),
        ("  일시: 2026년 6월 19일 (금) 14:00\n", None),
        ("  의제: 미정 (각 부서에서 사전 의제 제출 바람)\n\n", None),
        ("□ 회의 문의\n", None),
        ("  - 담당: ", None),
        (a, "PERSON"),
        (f" {title_a}\n", None),
        ("  - 연락처: ", None),
        (chairperson_phone, "PHONE"),
        ("\n  - 이메일: ", None),
        (chairperson_email, "EMAIL"),
        ("\n", None),
    ]
    return _assemble(parts, template="meeting_minutes", pii_labels={
        "PERSON", "VEHICLE", "DOC_ID", "PHONE", "EMAIL",
    })


def _police_report(rnd: random.Random) -> GoldDocument:
    """경찰서 사건 처리 보고서 템플릿 — 풍부한 본문."""
    officer = rnd.choice(_NAMES)
    rank = rnd.choice(_TITLES_POLICE_POOL)
    suspect = rnd.choice([n for n in _NAMES if n != officer])
    victim = rnd.choice([n for n in _NAMES if n not in {officer, suspect}])
    rrn = rnd.choice(_RRN_SAMPLES)
    suspect_phone = rnd.choice(_PHONE_MOBILE)
    victim_phone = rnd.choice(_PHONE_MOBILE)
    addr = rnd.choice(_ADDR_ROAD)
    vehicle = rnd.choice(_VEHICLE_SAMPLES)
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    docnum = f"{abbrev}-수사과-2026-{rnd.randint(10000, 99999)}"
    case_num = f"2026가합{rnd.randint(10000, 99999)}"

    parts = [
        ("[경찰 사건 처리 보고서]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n사건번호: ", None),
        (case_num, "COURT_CASE"),
        ("\n", None),
        ("작성일자: 2026년 5월 18일\n\n", None),
        ("□ 수사관\n", None),
        ("  성명: ", None),
        (officer, "PERSON"),
        (f"\n  계급: {rank}\n", None),
        ("  소속: 본서 수사1과\n\n", None),
        ("□ 사건 개요\n", None),
        ("  본 건은 2026년 5월 15일 발생한 차량 손괴 사건으로, ", None),
        ("피해자 신고에 의하여 접수되었음.\n", None),
        ("  발생장소: ", None),
        (addr, "ADDRESS"),
        ("\n  발생일시: 2026년 5월 15일 (목) 22:30 경\n\n", None),
        ("□ 피의자 정보\n", None),
        ("  성명: ", None),
        (suspect, "PERSON"),
        ("\n  주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n  연락처: ", None),
        (suspect_phone, "PHONE"),
        ("\n  차량번호: ", None),
        (vehicle, "VEHICLE"),
        ("\n\n", None),
        ("□ 피해자 정보\n", None),
        ("  성명: ", None),
        (victim, "PERSON"),
        ("\n  연락처: ", None),
        (victim_phone, "PHONE"),
        ("\n\n", None),
        ("□ 조사 내용\n", None),
        ("  1) 현장 진술 청취 — 피해자 ", None),
        (victim, "PERSON"),
        (" 진술 확보.\n", None),
        ("  2) CCTV 영상 확인 — 피의자 차량 확인됨.\n", None),
        ("  3) 피의자 자백 — 조사 단계에서 사실 인정.\n\n", None),
        ("□ 관계 법령\n", None),
        ("  - 형법 제366조 (재물손괴 등)\n", None),
        ("  - 도로교통법 제54조 (사고 발생 시 조치)\n\n", None),
        ("□ 향후 조치\n", None),
        ("  본 건은 기소 의견으로 검찰 송치 예정이며, ", None),
        ("피해 보상 협의는 별도 진행 예정.\n\n", None),
        (rnd.choice(_ATTACHMENT_PHRASES), None),
    ]
    return _assemble(parts, template="police_report", pii_labels={
        "PERSON", "RRN", "PHONE", "DOC_ID", "ADDRESS", "VEHICLE", "COURT_CASE",
    })


def _fire_dispatch(rnd: random.Random) -> GoldDocument:
    """소방 출동 보고서 템플릿 — 풍부한 본문."""
    commander = rnd.choice(_NAMES)
    rank = rnd.choice(_TITLES_FIRE_POOL)
    reporter = rnd.choice([n for n in _NAMES if n != commander])
    reporter_phone = rnd.choice(_PHONE_MOBILE)
    addr = rnd.choice(_ADDR_ROAD)
    station_phone = rnd.choice(_PHONE_LANDLINE)
    rep_phone = rnd.choice(_PHONE_REPRESENTATIVE)
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    docnum = f"{abbrev}-출동과-2026-{rnd.randint(10000, 99999)}"

    parts = [
        ("[소방 출동 보고]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n출동일자: 2026년 5월 19일 (월) 03:42\n", None),
        ("종결일자: 2026년 5월 19일 (월) 04:55\n\n", None),
        ("□ 출동 정보\n", None),
        ("  - 신고 시각: 03:42\n", None),
        ("  - 도착 시각: 03:49 (소요 7분)\n", None),
        ("  - 종결 시각: 04:55 (총 73분)\n", None),
        ("  - 출동 형태: 화재 (소형)\n\n", None),
        ("□ 출동 인력\n", None),
        ("  - 출동대장: ", None),
        (commander, "PERSON"),
        (f" {rank}\n", None),
        ("  - 펌프차 1대, 구급차 1대, 인원 9명\n\n", None),
        ("□ 신고자\n", None),
        ("  - 성명: ", None),
        (reporter, "PERSON"),
        ("\n  - 연락처: ", None),
        (reporter_phone, "PHONE"),
        ("\n  - 신고지: ", None),
        (addr, "ADDRESS"),
        ("\n\n□ 현장 상황\n", None),
        ("  - 주거용 건물 1층 주방에서 발화 추정.\n", None),
        ("  - 화재 진압 시 인명 피해 없음 (확인).\n", None),
        ("  - 재산 피해: 주방 일부 소실 (추정 약 350만원).\n", None),
        ("  - 발화 원인: 가스레인지 과열 추정 — 정밀 감식 의뢰 예정.\n\n", None),
        ("□ 조치 내용\n", None),
        ("  1) 화재 진압 — 사용 수량 약 1,200 L.\n", None),
        ("  2) 거주자 대피 — 가족 3명 안전 대피 확인.\n", None),
        ("  3) 인근 가구 안전 점검 — 이상 없음.\n\n", None),
        ("□ 향후 조치\n", None),
        ("  본 건은 추가 감식 진행 후 결과 보고 예정이며, ", None),
        ("거주자 임시 거처 안내는 관할 구청과 협의함.\n\n", None),
        ("□ 문의\n", None),
        ("  - 관할 소방서: ", None),
        (station_phone, "PHONE"),
        ("\n  - 119 상황실: ", None),
        (rep_phone, "PHONE"),
        ("\n\n", None),
        ("상황 종료 보고서 및 부속 자료는 본 문서에 첨부함.\n", None),
        (rnd.choice(_ATTACHMENT_PHRASES), None),
    ]
    return _assemble(parts, template="fire_dispatch", pii_labels={
        "PERSON", "ADDRESS", "PHONE", "DOC_ID",
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
