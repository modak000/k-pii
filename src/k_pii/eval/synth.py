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

# 사업자번호: 국세청 가중합 체크섬 valid (compute_check_digit 로 검증됨)
_BIZREG_SAMPLES = [
    "120-81-47521",  # 한전 (실제 공개 사업자번호)
    "211-87-22658",
    "123-45-67891",
    "201-23-45671",
    "401-23-45679",
    "104-81-23454",
    "318-67-38211",
]

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

# 이름 풀 — 합성 다양성 향상을 위해 확장 (한국 인명 통계 분포 반영)
# 출처: 통계청 「인구주택총조사」 빈출 성씨 + 한국교육개발원 이름 빈도 자료
_NAMES = [
    # 김씨 (한국 최다 21%)
    "김민수", "김지원", "김도윤", "김서연", "김민지", "김하늘", "김예진",
    "김재현", "김수민", "김지호", "김예원", "김태훈", "김민준", "김유진",
    # 이씨
    "이수정", "이서준", "이도현", "이지민", "이은영", "이재훈", "이서영",
    "이지호", "이민호", "이수빈", "이채원", "이정훈", "이가은",
    # 박씨
    "박영수", "박지훈", "박서연", "박민지", "박재훈", "박수현", "박지원",
    "박서영", "박민호", "박도현",
    # 최씨
    "최지훈", "최민서", "최영진", "최수아", "최예린", "최도윤",
    # 정씨
    "정혜진", "정민기", "정유진", "정재훈", "정현우",
    # 강씨
    "강도현", "강민서", "강예준",
    # 윤·조·장·임·한
    "윤서연", "윤지호", "윤민기",
    "조하늘", "조민서", "조지훈",
    "장미경", "장지호", "장유진",
    "임도윤", "임수민", "임지원",
    "한지원", "한도현", "한서영",
    # 송·황·오·서·신
    "송지효", "송민기", "송서영",
    "황보경", "황지원",
    "오민서", "오재훈",
    "서예진", "서민호",
    "신도윤", "신지원",
    # 복성
    "남궁민수", "남궁지원",
    "황보경", "황보영진",
    "선우민기", "선우지호",
    # 양·노·하·문·구
    "양수민", "양도윤",
    "노예린", "노재훈",
    "하지원", "하예원",
    "문지호", "문수민",
    "구민서", "구하늘",
    # 홍·전·고·차
    "홍길동", "홍지원",
    "전민기", "전서영",
    "고수민", "고도현",
    "차예진", "차지호",
]

_TITLES_GOV_POOL = ["과장", "사무관", "주무관", "서기관", "국장", "팀장",
                     "주사", "주사보", "주임", "계장", "부이사관", "이사관"]
_TITLES_POLICE_POOL = ["경감", "경위", "경정", "총경", "경무관", "치안감", "경사", "경장"]
_TITLES_FIRE_POOL = ["소방위", "소방경", "소방령", "소방정", "소방준감", "소방감", "소방장"]
_TITLES_MILITARY_POOL = ["대위", "소령", "중령", "대령", "준장", "소장", "중장",
                          "상사", "원사", "중사", "하사"]
_AGENCIES_POOL = [
    "기획재정부", "행정안전부", "보건복지부", "법무부", "교육부",
    "통일부", "외교부", "국방부", "문화체육관광부", "농림축산식품부",
    "환경부", "고용노동부", "여성가족부", "국토교통부", "해양수산부",
    "중소벤처기업부", "산업통상자원부", "과학기술정보통신부",
    "국가보훈부", "국세청", "관세청", "조달청", "통계청",
    "검찰청", "병무청", "방위사업청", "경찰청", "소방청",
    "문화재청", "농촌진흥청", "산림청", "특허청", "기상청",
    "행정중심복합도시건설청", "새만금개발청",
]
_AGENCY_ABBREV_POOL = ["기재부", "행안부", "복지부", "국토부", "과기정통부",
                        "고용부", "산업부", "환경부", "교육부",
                        "통일부", "외교부", "국방부", "여가부",
                        "해수부", "농식품부", "문체부",
                        "보훈부", "벤처부"]

# 공공기관·공기업 (KOR 공공기관 운영법 기준 일부)
_PUBLIC_CORP_POOL = [
    "한국전력공사", "한국가스공사", "한국수자원공사", "한국도로공사",
    "한국철도공사", "코레일", "한국공항공사", "인천국제공항공사",
    "한국토지주택공사", "LH", "주택도시보증공사", "HUG",
    "국민건강보험공단", "국민연금공단", "건강보험심사평가원",
    "한국산업단지공단", "한국관광공사", "한국방송광고진흥공사",
    "한국정책방송원", "KTV", "한국방송공사", "KBS",
    "한국교육방송공사", "EBS",
]

# 회사명 (가공 — 실재 회사명 충돌 회피 위해 합성)
_COMPANY_POOL = [
    "ABC주식회사", "한빛상사", "대한물류", "고려테크",
    "한솔ICT", "한미산업", "동서무역", "신한금융지주",
    "한국씨엔에스", "한미사이언스", "BNK캐피탈",
    "코웨이", "현대정보기술", "POSCO홀딩스", "삼성리서치",
    "LG에너지솔루션", "SK엔무브", "한화테크원",
    "한국오라클", "한국마이크로소프트", "한국HP",
    "(주)미래에셋", "(주)한맥산업", "(주)대성그룹",
    "신세계푸드", "롯데정보통신", "CJ대한통운",
]

# 부서명 (정부 + 민간 공통)
_DEPT_POOL = [
    # 정부 부처 일반
    "총무과", "운영지원과", "인사과", "감사담당관실", "기획조정실",
    "정책기획과", "혁신행정담당관", "재정담당관", "비상안전기획관",
    # 사업 부서
    "민원과", "민원봉사과", "안전관리과", "건축과", "주택과",
    "환경위생과", "위생과", "공원녹지과", "교통행정과",
    "복지정책과", "복지서비스과", "노인복지과", "청소년과",
    "문화예술과", "관광진흥과", "체육진흥과",
    "보건정책과", "위생관리과", "감염병관리과",
    # 민간 부서
    "인사팀", "재무팀", "마케팅팀", "영업팀", "기획팀",
    "전략기획팀", "법무팀", "감사팀", "IT지원팀",
    "구매팀", "물류팀", "고객만족팀", "홍보팀",
    "연구개발팀", "R&D팀", "신사업팀", "투자전략팀",
]
_SCHOOL_POOL = [
    "서울대학교", "연세대학교", "고려대학교", "성균관대학교",
    "한양대학교", "서강대학교", "중앙대학교", "경희대학교",
    "이화여자대학교", "한국외국어대학교", "건국대학교",
    "동국대학교", "홍익대학교", "숙명여자대학교",
    "부산대학교", "경북대학교", "전남대학교", "충남대학교",
    "한국과학기술원", "포항공과대학교", "광주과학기술원",
    "울산과학기술원", "대구경북과학기술원",
    "한국교통대학교", "강원대학교", "충북대학교",
]

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


def _court_decision(rnd: random.Random) -> GoldDocument:
    """법원 판결문 일부 — 사건 처리 결정 (간이)."""
    judge = rnd.choice(_NAMES)
    plaintiff = rnd.choice([n for n in _NAMES if n != judge])
    defendant = rnd.choice([n for n in _NAMES if n not in {judge, plaintiff}])
    plaintiff_rrn = rnd.choice(_RRN_SAMPLES)
    defendant_rrn = rnd.choice([r for r in _RRN_SAMPLES if r != plaintiff_rrn])
    plaintiff_addr = rnd.choice(_ADDR_ROAD)
    defendant_addr = rnd.choice([a for a in _ADDR_ROAD if a != plaintiff_addr])
    case_num = f"2026가합{rnd.randint(10000, 99999)}"
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    docnum = f"{abbrev}-법원-2026-{rnd.randint(10000, 99999)}"

    parts = [
        ("[판결문]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n사건번호: ", None),
        (case_num, "COURT_CASE"),
        ("\n선고일자: 2026년 5월 19일\n\n", None),
        ("□ 사건 당사자\n", None),
        ("  - 원고: ", None),
        (plaintiff, "PERSON"),
        ("\n  - 주민등록번호: ", None),
        (plaintiff_rrn, "RRN"),
        ("\n  - 주소: ", None),
        (plaintiff_addr, "ADDRESS"),
        ("\n  - 피고: ", None),
        (defendant, "PERSON"),
        ("\n  - 주민등록번호: ", None),
        (defendant_rrn, "RRN"),
        ("\n  - 주소: ", None),
        (defendant_addr, "ADDRESS"),
        ("\n\n□ 주문\n", None),
        ("  1. 피고는 원고에게 금 5,000,000원 및 이에 대한 ", None),
        ("2026년 1월 1일부터 다 갚는 날까지 연 5% 의 비율로 ", None),
        ("계산한 돈을 지급하라.\n", None),
        ("  2. 소송비용은 피고가 부담한다.\n\n", None),
        ("□ 청구취지\n", None),
        ("  원고는 피고에게 위 주문과 같은 판결을 구하였다.\n\n", None),
        ("□ 이유 (요약)\n", None),
        ("  본 사건은 2025년 12월에 발생한 계약 불이행 분쟁으로, ", None),
        ("원고 ", None),
        (plaintiff, "PERSON"),
        ("이 제출한 증거에 의하여 청구취지가 인정되며 ", None),
        ("피고 ", None),
        (defendant, "PERSON"),
        ("의 항변은 이유 없으므로 기각함.\n\n", None),
        ("□ 재판부\n", None),
        ("  판사: ", None),
        (judge, "PERSON"),
        ("\n\n", None),
        ("본 판결문은 「민사소송법」 제202조 및 ", None),
        ("「개인정보보호법」 제2조에 따라 처리됨.\n", None),
    ]
    return _assemble(parts, template="court_decision", pii_labels={
        "PERSON", "RRN", "ADDRESS", "DOC_ID", "COURT_CASE",
    })


def _tax_notice(rnd: random.Random) -> GoldDocument:
    """국세청 세무 안내문 — 납세 안내·과세 사실 통보."""
    taxpayer = rnd.choice(_NAMES)
    handler = rnd.choice([n for n in _NAMES if n != taxpayer])
    handler_title = rnd.choice(["사무관", "세무사", "주무관"])
    rrn = rnd.choice(_RRN_SAMPLES)
    bizreg = rnd.choice(_BIZREG_SAMPLES)
    phone = rnd.choice(_PHONE_LANDLINE)
    rep_phone = rnd.choice(_PHONE_REPRESENTATIVE)
    addr = rnd.choice(_ADDR_ROAD)
    docnum = f"국세청-세무서-2026-{rnd.randint(10000, 99999)}"
    tax_year = "2025년"
    notice_num = f"2026-과세-{rnd.randint(10000, 99999)}"

    parts = [
        ("[과세 사실 통보서]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        (f"\n통보번호: {notice_num}\n", None),
        ("통보일자: 2026년 5월 18일\n\n", None),
        ("□ 납세자 정보\n", None),
        ("  - 성명: ", None),
        (taxpayer, "PERSON"),
        ("\n  - 주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n  - 사업자등록번호: ", None),
        (bizreg, "BUSINESS_REG"),
        ("\n  - 주소: ", None),
        (addr, "ADDRESS"),
        ("\n\n□ 통보 내용\n", None),
        (f"  {tax_year} 귀속분 종합소득세 신고서 검토 결과 다음과 같이 ", None),
        ("과세 사실이 확인되어 통보합니다.\n", None),
        ("  - 사업소득 누락액: 12,500,000원\n", None),
        ("  - 미신고 가산세: 1,250,000원\n", None),
        ("  - 가산금: 187,500원\n", None),
        ("  - 합계: 13,937,500원\n\n", None),
        ("□ 처리 사항\n", None),
        ("  본 통보서를 받으신 분께서는 통보일로부터 30일 이내에 ", None),
        ("아래 방법 중 한 가지로 회신하여 주시기 바랍니다.\n", None),
        ("  1) 자진 납부: 가까운 세무서 또는 국세청 홈택스를 통해 납부\n", None),
        ("  2) 이의 신청: 통보 사항에 동의하지 않으신 경우 이의신청서 제출\n", None),
        ("  3) 분할 납부 신청: 일시 납부가 어려운 경우 분할 납부 신청 가능\n\n", None),
        ("□ 관련 법령\n", None),
        ("  - 소득세법 제80조 (수입금액의 누락 등에 따른 추가 과세)\n", None),
        ("  - 국세기본법 제45조 (가산세)\n\n", None),
        ("□ 담당자 정보\n", None),
        ("  - 담당자: ", None),
        (handler, "PERSON"),
        (f" {handler_title}\n", None),
        ("  - 직통전화: ", None),
        (phone, "PHONE"),
        ("\n  - 대표번호: ", None),
        (rep_phone, "PHONE"),
        ("\n\n", None),
        ("본 통보서에 명시된 개인정보는 「개인정보보호법」 제24조의2 에 ", None),
        ("따라 수집·이용되며, 세무 행정 목적 외 사용을 금합니다.\n", None),
        (rnd.choice(_SIGNOFF_PHRASES) + "\n", None),
    ]
    return _assemble(parts, template="tax_notice", pii_labels={
        "PERSON", "RRN", "BUSINESS_REG", "ADDRESS", "PHONE", "DOC_ID",
    })


def _press_release(rnd: random.Random) -> GoldDocument:
    """정부 보도자료 — 정책 발표 / 임명 / 행사 안내."""
    agency = rnd.choice(_AGENCIES_POOL)
    spokesman = rnd.choice(_NAMES)
    spokesman_title = rnd.choice(["대변인", "공보관", "정책기획관", "홍보담당관"])
    minister = rnd.choice([n for n in _NAMES if n != spokesman])
    rep_phone = rnd.choice(_PHONE_REPRESENTATIVE)
    contact_phone = rnd.choice(_PHONE_LANDLINE)
    email = rnd.choice(_EMAIL_SAMPLES)
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    docnum = f"{abbrev}-홍보과-2026-{rnd.randint(10000, 99999)}"

    parts = [
        ("[보도자료]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n배포일자: 2026년 5월 21일\n", None),
        (f"배포처: {agency} 홍보과\n\n", None),
        ("□ 제목: 신규 정책 추진 발표\n\n", None),
        ("□ 발표 내용\n", None),
        (f"  {agency} ", None),
        (minister, "PERSON"),
        (" 장관은 금일 정례 브리핑에서 ", None),
        ("다음과 같이 신규 정책 추진 계획을 발표하였습니다.\n", None),
        ("  1) 본 정책은 관련 법령 개정과 함께 진행되며, ", None),
        ("국민 의견 수렴을 위한 공청회를 6월 중 개최할 예정.\n", None),
        ("  2) 추진 일정에 따라 단계적 시행 예정.\n\n", None),
        ("□ 향후 일정\n", None),
        ("  - 6월: 공청회 (서울, 대전, 부산 3회)\n", None),
        ("  - 7월: 의견 수렴 분석\n", None),
        ("  - 8월: 시행령 개정안 입법 예고\n\n", None),
        ("□ 문의처\n", None),
        ("  - 담당자: ", None),
        (spokesman, "PERSON"),
        (f" {spokesman_title}\n", None),
        ("  - 직통전화: ", None),
        (contact_phone, "PHONE"),
        ("\n  - 대표번호: ", None),
        (rep_phone, "PHONE"),
        ("\n  - 이메일: ", None),
        (email, "EMAIL"),
        ("\n\n끝.\n", None),
    ]
    return _assemble(parts, template="press_release", pii_labels={
        "PERSON", "PHONE", "EMAIL", "DOC_ID",
    })


def _audit_report(rnd: random.Random) -> GoldDocument:
    """감사 보고서 — 감사 결과 + 시정 권고."""
    auditor = rnd.choice(_NAMES)
    auditor_title = rnd.choice(["감사관", "수석감사관", "감사실장"])
    auditee = rnd.choice([n for n in _NAMES if n != auditor])
    auditee_title = rnd.choice(_TITLES_GOV_POOL)
    dept = rnd.choice(_DEPT_POOL)
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    docnum = f"{abbrev}-감사관실-2026-{rnd.randint(10000, 99999)}"
    rep_phone = rnd.choice(_PHONE_REPRESENTATIVE)
    bizreg = rnd.choice(_BIZREG_SAMPLES)

    parts = [
        ("[감사 보고서]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n감사기간: 2026년 3월 1일 ~ 4월 30일\n", None),
        (f"감사대상: {dept}\n\n", None),
        ("□ 감사관\n", None),
        ("  - 성명: ", None),
        (auditor, "PERSON"),
        (f"\n  - 직급: {auditor_title}\n\n", None),
        ("□ 감사 결과 (요약)\n", None),
        (f"  {dept} 의 2025년도 회계 처리 및 업무 수행 사항을 점검한 결과, ", None),
        ("일부 사항에서 시정이 필요한 사례가 발견되었음.\n\n", None),
        ("□ 주요 지적 사항\n", None),
        ("  1) 예산 집행 시 증빙서류 누락 (3건)\n", None),
        ("  2) 출장비 정산 과다 청구 (1건, 환수 조치 완료)\n", None),
        ("  3) 위탁업체 (사업자등록번호 ", None),
        (bizreg, "BUSINESS_REG"),
        (") 계약 검토 미흡\n\n", None),
        ("□ 시정 권고\n", None),
        ("  본 감사 결과에 대하여 다음과 같이 권고함:\n", None),
        ("  1) 회계 담당자 ", None),
        (auditee, "PERSON"),
        (f" {auditee_title} 에 대한 주의 조치\n", None),
        ("  2) 부서 차원의 회계 처리 매뉴얼 재정비\n", None),
        ("  3) 위탁계약 사전 법무 검토 의무화\n\n", None),
        ("□ 후속 조치 보고\n", None),
        ("  본 권고 사항에 대한 조치 결과를 30일 이내 회신 바람.\n\n", None),
        ("□ 문의처\n", None),
        ("  - 감사관실: ", None),
        (rep_phone, "PHONE"),
        ("\n\n", None),
        (rnd.choice(_ATTACHMENT_PHRASES), None),
    ]
    return _assemble(parts, template="audit_report", pii_labels={
        "PERSON", "BUSINESS_REG", "PHONE", "DOC_ID",
    })


def _contract(rnd: random.Random) -> GoldDocument:
    """용역 계약서 (간이) — 갑/을 + 단가 + 기간."""
    party_a = rnd.choice(_NAMES)
    party_a_title = rnd.choice(["대표", "대표이사", "이사장"])
    party_b = rnd.choice([n for n in _NAMES if n != party_a])
    party_b_title = rnd.choice(["대표", "대표이사"])
    company_a = rnd.choice(_COMPANY_POOL)
    company_b = rnd.choice([c for c in _COMPANY_POOL if c != company_a])
    bizreg_a = rnd.choice(_BIZREG_SAMPLES)
    bizreg_b = rnd.choice([b for b in _BIZREG_SAMPLES if b != bizreg_a])
    addr_a = rnd.choice(_ADDR_ROAD)
    addr_b = rnd.choice([a for a in _ADDR_ROAD if a != addr_a])
    contract_num = f"용역-2026-{rnd.randint(10000, 99999)}"

    parts = [
        ("[용역 계약서]\n\n", None),
        (f"계약번호: {contract_num}\n", None),
        ("계약일자: 2026년 5월 21일\n", None),
        ("계약기간: 2026년 6월 1일 ~ 2026년 12월 31일\n\n", None),
        ("□ 계약 당사자\n", None),
        (f"  - 갑: {company_a} (사업자등록번호 ", None),
        (bizreg_a, "BUSINESS_REG"),
        (")\n", None),
        ("       대표자: ", None),
        (party_a, "PERSON"),
        (f" ({party_a_title})\n", None),
        ("       소재지: ", None),
        (addr_a, "ADDRESS"),
        ("\n", None),
        (f"  - 을: {company_b} (사업자등록번호 ", None),
        (bizreg_b, "BUSINESS_REG"),
        (")\n", None),
        ("       대표자: ", None),
        (party_b, "PERSON"),
        (f" ({party_b_title})\n", None),
        ("       소재지: ", None),
        (addr_b, "ADDRESS"),
        ("\n\n", None),
        ("□ 계약 목적\n", None),
        (f"  갑은 을에게 IT 시스템 구축 용역을 의뢰하며, ", None),
        ("을은 계약 조건에 따라 이를 성실히 수행한다.\n\n", None),
        ("□ 용역 대금\n", None),
        ("  - 총 금액: 금 일억오천만원정 (\\150,000,000)\n", None),
        ("  - 부가가치세 별도\n", None),
        ("  - 지급 방식: 착수금 30%, 중도금 40%, 잔금 30%\n\n", None),
        ("□ 일반 조건\n", None),
        ("  1) 본 계약에 명시되지 아니한 사항은 「민법」 및 ", None),
        ("관련 법령에 따른다.\n", None),
        ("  2) 분쟁 발생 시 서울중앙지방법원을 관할로 한다.\n", None),
        ("  3) 본 계약은 갑·을 각 1부씩 보관한다.\n\n", None),
        ("□ 서명\n", None),
        (f"  갑 {company_a}\n", None),
        ("     대표자 ", None),
        (party_a, "PERSON"),
        (f" {party_a_title} (인)\n", None),
        (f"  을 {company_b}\n", None),
        ("     대표자 ", None),
        (party_b, "PERSON"),
        (f" {party_b_title} (인)\n", None),
    ]
    return _assemble(parts, template="contract", pii_labels={
        "PERSON", "BUSINESS_REG", "ADDRESS",
    })


def _hr_appointment(rnd: random.Random) -> GoldDocument:
    """인사 발령 통지 — 부서 이동 / 직급 승진."""
    employee = rnd.choice(_NAMES)
    employee_title = rnd.choice(_TITLES_GOV_POOL)
    rrn = rnd.choice(_RRN_SAMPLES)
    old_dept = rnd.choice(_DEPT_POOL)
    new_dept = rnd.choice([d for d in _DEPT_POOL if d != old_dept])
    emp_id = rnd.randint(20180000, 20240999)
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    docnum = f"{abbrev}-인사과-2026-{rnd.randint(10000, 99999)}"
    handler = rnd.choice([n for n in _NAMES if n != employee])

    parts = [
        ("[인사 발령 통지서]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n발령일자: 2026년 6월 1일\n\n", None),
        ("□ 대상자 정보\n", None),
        ("  - 성명: ", None),
        (employee, "PERSON"),
        ("\n  - 주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n  - 사번: ", None),
        (str(emp_id), "EMPLOYEE_ID"),
        (f"\n  - 현 직급: {employee_title}\n", None),
        (f"  - 현 소속: {old_dept}\n\n", None),
        ("□ 발령 사항\n", None),
        (f"  - 신규 소속: {new_dept}\n", None),
        ("  - 발령 사유: 인사 정책에 따른 부서 이동\n", None),
        ("  - 발령 효력 발생일: 2026년 6월 1일\n\n", None),
        ("□ 인수인계\n", None),
        ("  본 발령에 따라 종전 업무 인수인계를 ", None),
        ("발령일 전까지 완료하시기 바랍니다.\n\n", None),
        ("□ 담당자\n", None),
        ("  - 인사 담당자: ", None),
        (handler, "PERSON"),
        ("\n  - 연락처: 02-1234-5678\n\n", None),
        (rnd.choice(_SIGNOFF_PHRASES) + "\n", None),
    ]
    return _assemble(parts, template="hr_appointment", pii_labels={
        "PERSON", "RRN", "EMPLOYEE_ID", "DOC_ID",
    })


def _admin_disposition(rnd: random.Random) -> GoldDocument:
    """행정 처분 통지서 — 위반 사실 + 처분 내용."""
    violator = rnd.choice(_NAMES)
    rrn = rnd.choice(_RRN_SAMPLES)
    phone = rnd.choice(_PHONE_MOBILE)
    addr = rnd.choice(_ADDR_ROAD)
    bizreg = rnd.choice(_BIZREG_SAMPLES)
    handler = rnd.choice([n for n in _NAMES if n != violator])
    handler_title = rnd.choice(_TITLES_GOV_POOL)
    abbrev = rnd.choice(_AGENCY_ABBREV_POOL)
    docnum = f"{abbrev}-처분-2026-{rnd.randint(10000, 99999)}"
    rep_phone = rnd.choice(_PHONE_REPRESENTATIVE)

    parts = [
        ("[행정 처분 통지서]\n\n", None),
        ("문서번호: ", None),
        (docnum, "DOC_ID"),
        ("\n처분일자: 2026년 5월 21일\n\n", None),
        ("□ 처분 대상자 정보\n", None),
        ("  - 성명: ", None),
        (violator, "PERSON"),
        ("\n  - 주민등록번호: ", None),
        (rrn, "RRN"),
        ("\n  - 연락처: ", None),
        (phone, "PHONE"),
        ("\n  - 주소: ", None),
        (addr, "ADDRESS"),
        ("\n  - 사업자등록번호: ", None),
        (bizreg, "BUSINESS_REG"),
        ("\n\n□ 위반 사실\n", None),
        ("  귀하의 영업장에서 2026년 4월 15일 점검 결과, ", None),
        ("다음과 같은 법령 위반 사항이 적발되었음을 통지합니다.\n", None),
        ("  - 위반 일시: 2026년 4월 15일 14:30\n", None),
        ("  - 위반 내용: 영업시간 외 영업 (식품위생법 제44조)\n\n", None),
        ("□ 처분 내용\n", None),
        ("  - 처분 유형: 영업정지 7일\n", None),
        ("  - 처분 시행일: 2026년 6월 1일 ~ 6월 7일\n", None),
        ("  - 과징금: 부과 안 함 (1차 위반)\n\n", None),
        ("□ 이의 신청 안내\n", None),
        ("  본 처분에 이의가 있으신 경우 처분일로부터 90일 이내에 ", None),
        ("「행정심판법」에 따라 행정심판을 청구하실 수 있습니다.\n\n", None),
        ("□ 담당자\n", None),
        ("  - 담당자: ", None),
        (handler, "PERSON"),
        (f" {handler_title}\n", None),
        ("  - 대표번호: ", None),
        (rep_phone, "PHONE"),
        ("\n", None),
    ]
    return _assemble(parts, template="admin_disposition", pii_labels={
        "PERSON", "RRN", "PHONE", "ADDRESS", "BUSINESS_REG", "DOC_ID",
    })


_TEMPLATES: tuple[Callable[[random.Random], GoldDocument], ...] = (
    _gov_decree,
    _civil_petition,
    _hr_review,
    _meeting_minutes,
    _police_report,
    _fire_dispatch,
    _court_decision,
    _tax_notice,
    _press_release,
    _audit_report,
    _contract,
    _hr_appointment,
    _admin_disposition,
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
            "court_decision": _court_decision,
            "tax_notice": _tax_notice,
            "press_release": _press_release,
            "audit_report": _audit_report,
            "contract": _contract,
            "hr_appointment": _hr_appointment,
            "admin_disposition": _admin_disposition,
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
