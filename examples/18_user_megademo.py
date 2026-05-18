"""18. modak000 전용 대형 데모 — 300+ 케이스 + 10+ 현실 시나리오.

사용:
    python examples/18_user_megademo.py                  # 터미널 출력
    python examples/18_user_megademo.py --md out.md      # Markdown
    python examples/18_user_megademo.py --html out.html  # HTML 리포트
    python examples/18_user_megademo.py --scenarios      # 시나리오만
    python examples/18_user_megademo.py --units          # 단위 케이스만
"""
from __future__ import annotations

import argparse
import html as html_mod
import sys
from collections import OrderedDict
from dataclasses import dataclass, field

from k_pii import Anonymizer, ProcessingMode
from k_pii.detect import detect_all


@dataclass
class Case:
    label: str
    desc: str
    text: str
    note: str = ""


# ═══════════════════════════════════════════════════════════════════════
# Part 1 — 카테고리별 단위 케이스 (각 카테고리 10+ 변형)
# ═══════════════════════════════════════════════════════════════════════

UNIT_CASES: list[Case] = []


def _add(cat, desc, text, note=""):
    UNIT_CASES.append(Case(cat, desc, text, note))


# ─────── RRN (주민등록번호) ───────
_add("RRN", "표준 (1988년생 남성)", "주민번호: 880101-1234568")
_add("RRN", "1990년대생 여성", "주민번호: 950101-2345676")
_add("RRN", "2000년대생 남성", "주민번호: 001225-3000008")
_add("RRN", "2010년대생 여성", "주민번호: 100315-4123456")
_add("RRN", "1800년대 (100세, 남)", "주민번호: 851225-9000003")
_add("RRN", "1800년대 (100세, 여)", "주민번호: 851225-0000005")
_add("RRN", "하이픈 없음", "8801011234568")
_add("RRN", "공백 구분자", "880101 1234568")
_add("RRN", "후-2020 무작위화 (체크섬 fail)", "주민번호 880101-1999999",
     "행정안전부 2020-10-05 이후 발급 RRN 은 무작위화 — 체크섬 실패해도 PII")
_add("RRN", "여러 개 한 문장", "신청인 880101-1234568, 보호자 950101-2345676")

# ─────── FRN (외국인등록번호) ───────
_add("FRN", "외국인 남성 (1900년대)", "외국인등록번호 850315-5345676")
_add("FRN", "외국인 여성 (1900년대)", "FRN: 850315-6000008")
_add("FRN", "외국인 남성 (2000년대)", "000101-7000009")
_add("FRN", "외국인 여성 (2000년대)", "000101-8000001")

# ─────── BUSINESS_REG (사업자번호) ───────
_add("BUSINESS_REG", "카카오 (실제 valid)", "사업자등록번호: 120-81-47521")
_add("BUSINESS_REG", "하이픈 없음", "1208147521 등록")
_add("BUSINESS_REG", "공백 포함 표기", "사업자: 120 81 47521",
     "공백 구분은 미지원 — 표준 하이픈 또는 합친 형태만")

# ─────── CORP_REG (법인번호) ───────
_add("CORP_REG", "한국전력 (191211-0006637)", "법인등록번호: 191211-0006637")

# ─────── DRIVER_LICENSE ───────
_add("DRIVER_LICENSE", "서울청 (지방청 11)", "면허번호 11-90-123456-78")
_add("DRIVER_LICENSE", "인천청 (23)", "23-15-654321-09")
_add("DRIVER_LICENSE", "세종 (28)", "28-22-100000-50")
_add("DRIVER_LICENSE", "키워드 anchor + 하이픈없음", "운전면허 119012345678 정지")

# ─────── PASSPORT (여권) ───────
_add("PASSPORT", "일반 여권 M", "여권: M12345678")
_add("PASSPORT", "일반 여권 S", "S87654321")
_add("PASSPORT", "관용 여권 O", "관용 O11112222")
_add("PASSPORT", "외교관 여권 D", "외교관 D12345678")
_add("PASSPORT", "거주 여권 R", "거주 R44445555")
_add("PASSPORT", "여행증명서 T", "T99998888")
_add("PASSPORT", "2024.12.16 신형 PP", "PP12345678 (신형)")
_add("PASSPORT", "신형 외교 PD", "PD33334444")
_add("PASSPORT", "잘못된 prefix A (거부)", "A12345678",
     "A 는 한국 여권 prefix 아님 — 자동 거부")

# ─────── CARD (신용카드 — Luhn) ───────
_add("CARD", "Visa (4 prefix, 하이픈)", "카드 4242-4242-4242-4242")
_add("CARD", "Mastercard (5, 공백)", "5555 5555 5555 4444")
_add("CARD", "Mastercard 신규 (2 prefix)", "2223-0000-4841-0010")
_add("CARD", "AMEX (3 prefix, 15자리)", "3782-822463-10005")
_add("CARD", "JCB (3528-3589)", "3528000000000001")
_add("CARD", "한국 국내전용 (9 prefix)", "9410123456789012")
_add("CARD", "Discover (6011)", "6011-0000-0000-0004")

# ─────── MEDICAL_INSURANCE (건강보험) ───────
_add("MEDICAL_INSURANCE", "건강보험증 키워드", "건강보험증번호: 12345678901")
_add("MEDICAL_INSURANCE", "의료보험 키워드", "의료보험 11122334455")
_add("MEDICAL_INSURANCE", "키워드 너무 멀음 (거부)",
     "건강보험 안내 이후 한참 뒤 12345678901",
     "25자 윈도우 초과 — 키워드 멀어서 거부")

# ─────── PRESCRIPTION_ID (식의약) ───────
_add("PRESCRIPTION_ID", "처방번호 (12자리 YYYYMMDD+seq)",
     "처방번호 202412010001")
_add("PRESCRIPTION_ID", "처방전 발행번호", "처방전 발행번호: 202401150042")
_add("PRESCRIPTION_ID", "Rx 영문 키워드", "Rx 202401150042")
_add("PRESCRIPTION_ID", "교부번호", "교부번호 202405180001")
_add("PRESCRIPTION_ID", "의료기관기호 (HIRA)", "요양기관기호: 12345678")

# ─────── KCD (한국표준질병사인분류) ───────
_add("KCD", "당뇨 (E11.9)", "진단코드: E11.9")
_add("KCD", "고혈압 (I10) + 키워드", "주상병 I10")
_add("KCD", "임신 (O00) 소수점", "진단: O00.0")
_add("KCD", "외상 (S00.0)", "상병코드 S00.0")
_add("KCD", "감염성 (A00)", "주상병: A00.1")
_add("KCD", "정신 (F40.0)", "진단 F40.0 공포증")
_add("KCD", "단독 (거부)", "A00 같은 단어", "키워드 + 소수점 모두 없으면 거부")

# ─────── EDI_DRUG (식약처) ───────
_add("EDI_DRUG", "EDI 9자리 + 키워드", "약품코드 123456789")
_add("EDI_DRUG", "주성분코드", "주성분코드 987654321")
_add("EDI_DRUG", "KD 13자리 (한국)", "KD코드: 8801234567890")

# ─────── COURT_CASE (법원 사건번호) ───────
_add("COURT_CASE", "민사 합의 (가합)", "사건번호: 2024가합12345")
_add("COURT_CASE", "민사 단독 (가단)", "2020가단578")
_add("COURT_CASE", "민사 2심 (나)", "2024나1234")
_add("COURT_CASE", "민사 3심 (다)", "2024다5678")
_add("COURT_CASE", "형사 합의 (고합)", "2023고합567")
_add("COURT_CASE", "형사 단독 (고단)", "2024고단890")
_add("COURT_CASE", "행정 (구합)", "2024구합1234")
_add("COURT_CASE", "가사 (드합)", "2024드합567")
_add("COURT_CASE", "헌법 본안 (헌가)", "2024헌가1")
_add("COURT_CASE", "헌법 권리침해 (헌마)", "2024헌마789")
_add("COURT_CASE", "지급명령 (차)", "2024차10001")

# ─────── PHONE (전화번호) ───────
_add("PHONE", "010 휴대 하이픈", "010-2847-3915")
_add("PHONE", "010 휴대 점", "010.8624.1759")
_add("PHONE", "010 휴대 공백", "010 5093 2186")
_add("PHONE", "010 휴대 합친", "01074910376")
_add("PHONE", "011 (구형)", "011-258-6047")
_add("PHONE", "016 (구형)", "016-394-7281")
_add("PHONE", "017 (구형)", "017-462-8159")
_add("PHONE", "018 (구형)", "018-571-3920")
_add("PHONE", "019 (구형)", "019-689-2415")
_add("PHONE", "국제 +82", "+82-10-9617-8253")
_add("PHONE", "국제 0082", "0082 10 4806 5279")
_add("PHONE", "서울 일반 (02)", "02-3479-6128")
_add("PHONE", "경기 (031)", "031-624-7185")
_add("PHONE", "인천 (032)", "032-815-3047")
_add("PHONE", "강원 (033)", "033-516-2940")
_add("PHONE", "대전 (042)", "042-738-2169")
_add("PHONE", "광주 (062)", "062-947-3815")
_add("PHONE", "부산 (051)", "051-468-1759")
_add("PHONE", "VoIP (070)", "070-7864-3920")

# ─────── FAX ───────
_add("FAX", "팩스 한글 키워드", "팩스: 02-123-4567")
_add("FAX", "FAX 영문", "FAX 031-555-6677")
_add("FAX", "전송 키워드", "전송 02-999-8888")
_add("FAX", "키워드 없음 (거부)", "02-123-4567 단독",
     "키워드 없으면 PHONE 으로 분류")

# ─────── EMAIL ───────
_add("EMAIL", "일반 (.com)", "user@example.com")
_add("EMAIL", "공공 (.go.kr)", "minsu@gov.go.kr")
_add("EMAIL", "학교 (.ac.kr)", "student@snu.ac.kr")
_add("EMAIL", "기업 (.co.kr)", "ceo@company.co.kr")
_add("EMAIL", "비영리 (.or.kr)", "info@nonprofit.or.kr")
_add("EMAIL", "Gmail", "user.name+filter@gmail.com")
_add("EMAIL", "Naver", "kim123@naver.com")
_add("EMAIL", "한자 도메인 (UTF-8)", "user@한국.kr",
     "한글 도메인은 ASCII RFC 패턴 미매칭")

# ─────── POSTAL_CODE ───────
_add("POSTAL_CODE", "5자리 서울 (01~08)", "우편번호 03187")
_add("POSTAL_CODE", "5자리 경기 (10~18)", "우편번호 13520")
_add("POSTAL_CODE", "5자리 인천 (21~23)", "우편번호 21500")
_add("POSTAL_CODE", "5자리 부산 (46~49)", "우편번호 46999")
_add("POSTAL_CODE", "5자리 제주 (63)", "우편번호 63100")
_add("POSTAL_CODE", "6자리 레거시 (XXX-XXX)", "123-456")
_add("POSTAL_CODE", "미할당 (09 거부)", "우편번호 09999",
     "09 는 시·도 미할당 — 자동 거부")
_add("POSTAL_CODE", "미할당 (99 거부)", "우편번호 99000")

# ─────── IP ───────
_add("IP", "IPv4 사설", "서버 192.168.1.100")
_add("IP", "IPv4 외부", "출처 IP: 8.8.8.8")
_add("IP", "IPv4 루프백", "127.0.0.1")
_add("IP", "IPv6 단축", "2001:db8::1")
_add("IP", "IPv6 loopback", "::1")
_add("IP", "IPv6 IPv4-mapped", "::ffff:192.0.2.1")
_add("IP", "잘못된 옥텟 (거부)", "256.256.256.256")

# ─────── VEHICLE (차량) ───────
_add("VEHICLE", "자가용 가", "12가3456")
_add("VEHICLE", "자가용 나", "34나1234")
_add("VEHICLE", "자가용 마 (3자리)", "123마5678")
_add("VEHICLE", "영업용 바 (택배)", "87바1234")
_add("VEHICLE", "영업용 사 (택시)", "12사3456")
_add("VEHICLE", "영업용 아 (버스)", "78아9012")
_add("VEHICLE", "렌터카 하", "99하1234")
_add("VEHICLE", "렌터카 허", "88허5678")
_add("VEHICLE", "외교 외", "01외0001")
_add("VEHICLE", "군용 국", "11국1234")
_add("VEHICLE", "군용 합", "22합5678")
_add("VEHICLE", "일반 한글 강 (거부)", "30강 1234",
     "강 은 차량 용도 코드 아님")
_add("VEHICLE", "한국어 단위 조 (거부)", "291조 9000",
     "한국어 수량 단위 — 차량 아님")

# ─────── URL ───────
_add("URL", "HTTPS", "https://www.example.com")
_add("URL", "HTTP", "http://example.com/page")
_add("URL", "Path 포함", "https://gov.go.kr/board/view?id=123")

# ─────── ADDRESS ───────
_add("ADDRESS", "도로명 서울", "주소: 서울특별시 종로구 세종대로 209")
_add("ADDRESS", "도로명 경기 (2단계 시·군·구)",
     "경기도 성남시 분당구 정자로 1")
_add("ADDRESS", "도로명 부산", "부산광역시 해운대구 우동로 123")
_add("ADDRESS", "지번 (강남구 역삼동)",
     "주소: 서울특별시 강남구 역삼동 123")
_add("ADDRESS", "지번 (가평군 청평면)",
     "주소: 경기도 가평군 청평면 청평리 45-6")
_add("ADDRESS", "잘못된 광역+기초 조합 (거부)",
     "경기도 강남구 어딘가",
     "강남구는 서울 — (광역+기초) 조합 검증 거부")
_add("ADDRESS", "가짜 광역 (거부)",
     "바티스타밤이라도 나왔으면 1",
     "실제 한국 17개 광역 아님 — 자동 거부")

# ─────── ACCOUNT (계좌) ───────
_add("ACCOUNT", "10자리 계좌", "계좌: 1234567890")
_add("ACCOUNT", "13자리 계좌", "계좌 110-1234-567890")
_add("ACCOUNT", "키워드 없음 (거부)", "1234567890",
     "계좌 키워드 anchor 필수")

# ─────── PERSON (사람 이름) ───────
_add("PERSON", "성명 라벨 (단일성씨)", "성명: 김도윤")
_add("PERSON", "성명 라벨 (복성)", "성명: 남궁서윤")
_add("PERSON", "성명 라벨 (황보)", "참석자: 황보예진")
_add("PERSON", "신청인 라벨", "신청인: 박지훈")
_add("PERSON", "민원인 라벨", "민원인 이서연")
_add("PERSON", "기안자 라벨", "기안자: 정유진")
_add("PERSON", "결재자 라벨", "결재자 최도현")
_add("PERSON", "환자 라벨 (의료)", "환자: 강민지")
_add("PERSON", "직책 인접 (과장 뒤)", "박지훈 과장님께")
_add("PERSON", "직책 인접 (장관 뒤)", "김도윤 장관 발표")
_add("PERSON", "직책 인접 (의원 뒤)", "이서연 의원 질의")
_add("PERSON", "직책 인접 (검사 뒤)", "최도현 검사 수사")
_add("PERSON", "직책 인접 (앞쪽)", "과장 김도윤 보고")
_add("PERSON", "직책 인접 (3자 풀네임)", "부장 박지훈 면담",
     "직급 + 풀네임 = 실명 신호")
_add("PERSON", "자연어 조사 (이)", "이서연이 도착했다")
_add("PERSON", "자연어 조사 (가)", "박지훈이가 출연")
_add("PERSON", "자연어 조사 (은)", "정유진은 발표자다")
_add("PERSON", "자연어 조사 (의)", "김도윤의 신분증")
_add("PERSON", "3중 매크로 — 정형 부처", "기획재정부 김도윤 장관")
_add("PERSON", "3중 매크로 — 약칭", "기재부 박지훈 사무관")
_add("PERSON", "3중 매크로 — 환경부", "환경부 이서연 차관")
_add("PERSON", "3중 매크로 — 외교부 + 대사", "외교부 강민지 대사")
_add("PERSON", "3중 매크로 — 법무부 + 검사", "법무부 정유진 검사")
_add("PERSON", "3중 매크로 — 경찰청", "경찰청 최도현 경감")
_add("PERSON", "3중 매크로 — 소방청", "소방청 박지훈 소방위")
_add("PERSON", "3중 매크로 — 대통령실", "대통령실 강민지 정무수석")
_add("PERSON", "3중 매크로 — 국회", "국회 박지훈 의원")
_add("PERSON", "나이/성별 인접", "민원인 김도윤(45세)")
_add("PERSON", "성별 인접 (괄호)", "신청자 박지훈(남)")
_add("PERSON", "성별 인접 (콤마)", "이서연, 여자")
_add("PERSON", "공무원 부정 (기관명)", "보건복지부는 검토 후",
     "부처명 자체는 PERSON 아님")
_add("PERSON", "동음이의 부정 (검토)", "검토 결과 모두 적정",
     "일반 단어 — common_words 거부")
_add("PERSON", "직급 호칭 부정 (김부장)", "김부장이 또 일을 떠넘김",
     "성씨 1자 + 직급 = 호칭, PII 아님")
_add("PERSON", "직급 호칭 부정 (박과장)", "박과장도 협조 안 함",
     "호칭 — 실명 아님")
_add("PERSON", "직급 호칭 부정 (이차장님)", "이차장님이 회의 주재",
     "호칭 — PII 아님")
_add("PERSON", "한자 (미지원)", "참석자: 金道潤",
     "한자 매핑 별도 모듈 — 직접 통합 안 됨")
_add("PERSON", "부분 가명 (거부)", "박씨가 신고",
     "이미 가명화된 표기 — PII 아님")

# ─────── DOC_ID ───────
_add("DOC_ID", "기재부 문서", "문서번호: 기재부-인사-2024-00123")
_add("DOC_ID", "행안부 문서", "행안부-총무과-2025-00567")
_add("DOC_ID", "교육부 문서", "교육부-기획-2024-12345")
_add("DOC_ID", "신형 정부조직 (보훈부)", "보훈부-인사-2024-99999")

# ─────── PETITION_ID ───────
_add("PETITION_ID", "민원 (연도 앞)", "민원번호 2024-민원-00123")
_add("PETITION_ID", "민원 (키워드 앞)", "민원-2024-12345")
_add("PETITION_ID", "정보공개 청구", "청구번호 2025-정보공개-00567")
_add("PETITION_ID", "행정심판", "행정심판-2024-00890")

# ─────── EMPLOYEE_ID ───────
_add("EMPLOYEE_ID", "사번 키워드", "사번: 20231234")
_add("EMPLOYEE_ID", "공무원번호", "공무원번호 123456")
_add("EMPLOYEE_ID", "교번", "교번 789012")
_add("EMPLOYEE_ID", "직원번호", "직원번호: 456789")

# ─────── PNU (필지고유번호) ───────
_add("PNU", "서울 종로 (시도 11)", "PNU: 1111011600100010000")
_add("PNU", "경기 (시도 41)", "4129010200100250003")
_add("PNU", "산번지 (필지구분 2)", "4129010200200500015")
_add("PNU", "본번 0 (거부)", "1111011600000000000",
     "본번 0000 = placeholder")


# ═══════════════════════════════════════════════════════════════════════
# Part 1B — 확장 케이스 (각 카테고리 추가 변형)
# ═══════════════════════════════════════════════════════════════════════

# ─────── RRN 추가 ───────
_add("RRN", "1900년대 남성 (gender=1)", "주민번호 700101-1000005")
_add("RRN", "1900년대 여성 (gender=2)", "주민번호 700101-2000004")
_add("RRN", "2000년대 남성 (gender=3)", "주민번호 010101-3000007")
_add("RRN", "2000년대 여성 (gender=4)", "주민번호 010101-4000006")
_add("RRN", "괄호 안 표기", "(880101-1234568) 본인")
_add("RRN", "꺽쇠 안 표기", "<880101-1234568>")
_add("RRN", "ID/주민번호 라벨", "ID: 880101-1234568")
_add("RRN", "줄바꿈 인접", "성명 김도윤\n주민 880101-1234568")
_add("RRN", "표 안에 표기", "| 성명 | 주민번호 |\n| 김도윤 | 880101-1234568 |")
_add("RRN", "잘못된 월 (13월 거부)", "881301-1000004", "13월 = 무효 날짜")
_add("RRN", "잘못된 일 (32일 거부)", "880132-1000003", "32일 = 무효")
_add("RRN", "윤년 2/29 valid", "880229-1000009", "1988년 윤년 → 2/29 valid")

# ─────── FRN 추가 ───────
_add("FRN", "키워드 안커 (등록번호)", "등록번호: 850315-5345676")
_add("FRN", "키워드 안커 (외국인)", "외국인 850315-6000008")
_add("FRN", "거주증 키워드", "거주증 번호 850315-5345676")
_add("FRN", "여러 개 한 문장", "신청 850315-5345676, 동반자 000101-7000009")
_add("FRN", "공백 구분자", "850315 5345676")
_add("FRN", "잘못된 gender (1 거부 → RRN)", "850315-1234562",
     "gender=1 → RRN으로 분류, FRN 아님")

# ─────── BUSINESS_REG 추가 ───────
_add("BUSINESS_REG", "삼성전자 (124-81-00998)", "사업자: 124-81-00998")
_add("BUSINESS_REG", "네이버 (220-81-62517)", "사업자등록번호: 220-81-62517")
_add("BUSINESS_REG", "현대자동차 (101-81-25668)", "현대자동차 101-81-25668")
_add("BUSINESS_REG", "법인 (-81-)", "사업자번호 220-81-62517", "81 = 법인")
_add("BUSINESS_REG", "개인사업자 (-12-)", "사업자번호 123-12-12340")
_add("BUSINESS_REG", "비영리 (-82-)", "사업자번호 134-82-12369")
_add("BUSINESS_REG", "괄호 표기", "(120-81-47521) 등록")
_add("BUSINESS_REG", "placeholder 거부", "사업자 000-00-00000",
     "placeholder 패턴 — 자동 거부")
_add("BUSINESS_REG", "체크섬 fail (거부)", "사업자 120-81-47520",
     "마지막 자리 변경 = 체크섬 실패 → emit 안 함")
_add("BUSINESS_REG", "여러 개 한 문장", "갑: 120-81-47521, 을: 124-81-00998")

# ─────── CORP_REG 추가 ───────
_add("CORP_REG", "삼성전자 법인", "법인번호: 130111-0006246")
_add("CORP_REG", "주식회사 식별 (-0)", "법인 130111-0006246",
     "7번째 자리 0 = 주식회사")
_add("CORP_REG", "유한회사 (-1)", "법인 110111-1234567",
     "7번째 자리 1 = 유한회사 카테고리")
_add("CORP_REG", "키워드 없이 단독 (RRN 충돌 회피)",
     "191211-0006637 (한전)",
     "법인 체크섬 통과 + RRN 체크섬 실패 = CORP_REG 우선")
_add("CORP_REG", "괄호 안", "(191211-0006637) 한전")
_add("CORP_REG", "여러 개 한 문장", "한전 191211-0006637, 삼성전자 130111-0006246")

# ─────── DRIVER_LICENSE 추가 ───────
_add("DRIVER_LICENSE", "부산청 (12)", "12-90-123456-78")
_add("DRIVER_LICENSE", "대구청 (13)", "13-90-123456-78")
_add("DRIVER_LICENSE", "경기남부청 (16)", "16-90-654321-09")
_add("DRIVER_LICENSE", "경기북부청 (17)", "17-90-321098-76")
_add("DRIVER_LICENSE", "강원청 (18)", "18-90-987654-32")
_add("DRIVER_LICENSE", "전남청 (24)", "24-90-456789-01")
_add("DRIVER_LICENSE", "잘못된 청코드 (99 거부)", "99-90-123456-78",
     "99 는 지방청 코드 아님")
_add("DRIVER_LICENSE", "키워드 + 하이픈 mixed", "운전면허 11-90-123456-78")

# ─────── PASSPORT 추가 ───────
_add("PASSPORT", "공무 PO (구형)", "PO12345678")
_add("PASSPORT", "PS 거주", "PS44556677")
_add("PASSPORT", "PT 여행증명서", "PT11122233")
_add("PASSPORT", "키워드 + M", "여권번호 M99887766")
_add("PASSPORT", "Passport 영문 라벨", "Passport: M12345678")
_add("PASSPORT", "괄호 표기", "(M12345678) 발급")
_add("PASSPORT", "8자리 (구형 거부)", "M1234567", "9자리 필요 → 거부")
_add("PASSPORT", "10자리 (거부)", "M1234567890", "9자리 초과 → 거부")
_add("PASSPORT", "소문자 m (거부)", "m12345678", "한국 여권은 대문자")
_add("PASSPORT", "외교관 + 키워드", "외교관 여권 D33334444")

# ─────── CARD 추가 ───────
_add("CARD", "Visa Electron", "4026000000000003")
_add("CARD", "Mastercard 53 prefix", "5300000000000006")
_add("CARD", "AMEX 37 prefix", "3712345678901002")
_add("CARD", "AMEX 공백 구분", "3782 822463 10005")
_add("CARD", "Diners (300-305)", "30000000000004")
_add("CARD", "Diners (36)", "36000000000008")
_add("CARD", "JCB 3589", "3589000000000007")
_add("CARD", "국내 9000", "9000000000000004")
_add("CARD", "체크섬 fail (거부)", "4242-4242-4242-4243", "Luhn 실패")
_add("CARD", "16자리 합친", "4242424242424242")

# ─────── MEDICAL_INSURANCE 추가 ───────
_add("MEDICAL_INSURANCE", "건강보험 keyword colon", "건강보험: 12345678901")
_add("MEDICAL_INSURANCE", "공단증 키워드", "공단증 11122334455")
_add("MEDICAL_INSURANCE", "여러 개 한 문장",
     "건강보험증 11122334455 / 12345678901 보호자")
_add("MEDICAL_INSURANCE", "괄호 표기",
     "건강보험증(12345678901) 본인")
_add("MEDICAL_INSURANCE", "10자리 (거부)",
     "건강보험증 1234567890", "11자리만 인식")

# ─────── PRESCRIPTION_ID 추가 ───────
_add("PRESCRIPTION_ID", "처방번호 한자 표기", "처방번호 202412310009")
_add("PRESCRIPTION_ID", "처방전 발급번호", "처방전 발급번호: 202402280100")
_add("PRESCRIPTION_ID", "전자처방", "전자처방번호 202405010234")
_add("PRESCRIPTION_ID", "9자리 (잘못된 형식 거부)",
     "처방번호 202412001", "12자리 (YYYYMMDD+seq) 필요")
_add("PRESCRIPTION_ID", "키워드 없음 (거부)",
     "202412010001", "처방/Rx 키워드 없이 12자리 숫자만 — 거부")

# ─────── KCD 추가 ───────
_add("KCD", "암 (C00.0)", "주상병 C00.0 (구강암)")
_add("KCD", "코로나 (U07.1)", "진단 U07.1")
_add("KCD", "위염 (K29.0)", "진단코드 K29.0")
_add("KCD", "치매 (F00)", "진단 F00.0")
_add("KCD", "골절 (S72)", "상병 S72.0 (대퇴골)")
_add("KCD", "관절염 (M19)", "주상병 M19.0")
_add("KCD", "임신 (Z34.0)", "진단 Z34.0")
_add("KCD", "사망 (R99)", "사망원인 R99")
_add("KCD", "산모 (O80)", "주상병코드: O80.0")
_add("KCD", "Y코드 (외인사)", "원인 Y09 폭행")

# ─────── EDI_DRUG 추가 ───────
_add("EDI_DRUG", "주성분 9자리", "주성분코드 100100100")
_add("EDI_DRUG", "급여코드 9자리", "급여코드: 234567890")
_add("EDI_DRUG", "약가코드", "약가코드 111222333")
_add("EDI_DRUG", "KD 13자리 (다른값)", "KD코드 8806543210987")
_add("EDI_DRUG", "8자리 (거부)", "약품코드 12345678", "9자리 EDI 아님")
_add("EDI_DRUG", "키워드 없음 (거부)", "123456789",
     "키워드(약품/주성분/KD) 없이 9자리 숫자만 — 거부")

# ─────── COURT_CASE 추가 ───────
_add("COURT_CASE", "민사 4심 (라)", "2024라1234")
_add("COURT_CASE", "민사 5심 (마)", "2024마5678")
_add("COURT_CASE", "형사 2심 (노)", "2024노890")
_add("COURT_CASE", "형사 3심 (도)", "2024도1234")
_add("COURT_CASE", "행정 단독 (구단)", "2024구단567")
_add("COURT_CASE", "행정 2심 (누)", "2024누890")
_add("COURT_CASE", "행정 3심 (두)", "2024두1234")
_add("COURT_CASE", "가사 단독 (드단)", "2024드단123")
_add("COURT_CASE", "가사 2심 (르)", "2024르456")
_add("COURT_CASE", "회생/파산 (회합)", "2024회합1234")
_add("COURT_CASE", "헌법 위헌 (헌나)", "2024헌나1")
_add("COURT_CASE", "헌법 정당해산 (헌다)", "2024헌다1")
_add("COURT_CASE", "헌법 권한쟁의 (헌라)", "2024헌라1")
_add("COURT_CASE", "여러 개 한 문장",
     "관련 2024가합12345, 2023고합567, 2024차10001")

# ─────── PHONE 추가 (전국 지역번호) ───────
_add("PHONE", "대구 (053)", "053-742-1859")
_add("PHONE", "울산 (052)", "052-394-8261")
_add("PHONE", "충북 (043)", "043-258-1947")
_add("PHONE", "충남 (041)", "041-572-3068")
_add("PHONE", "전북 (063)", "063-841-2596")
_add("PHONE", "전남 (061)", "061-739-4068")
_add("PHONE", "경북 (054)", "054-682-3947")
_add("PHONE", "경남 (055)", "055-374-8192")
_add("PHONE", "제주 (064)", "064-518-2473")
_add("PHONE", "세종 (044)", "044-260-3458")
_add("PHONE", "안심번호 (0504)", "0504-3174-6829")
_add("PHONE", "전국 대표 (1588)", "1588-7264", "특수번호 — 사업체 대표")
_add("PHONE", "괄호 시외 (02)", "(02) 6712-1234")
_add("PHONE", "다국적 표기 +82-2", "+82-2-3479-6128")
_add("PHONE", "여러 개 한 문장",
     "유선 02-3479-6128 / 휴대 010-7491-0376")

# ─────── FAX 추가 ───────
_add("FAX", "팩스 + 지역 외", "팩스 031-555-6677")
_add("FAX", "Fax 콜론", "Fax: 02-123-4567")
_add("FAX", "여러 개 한 문장",
     "전송 02-999-8888, FAX 031-444-5555")

# ─────── EMAIL 추가 ───────
_add("EMAIL", "공무원 행정 (mois)", "kim@mois.go.kr")
_add("EMAIL", "공무원 (moef)", "park@moef.go.kr")
_add("EMAIL", "공무원 (police)", "lee@police.go.kr")
_add("EMAIL", "Daum 도메인", "user@daum.net")
_add("EMAIL", "Kakao", "user@kakao.com")
_add("EMAIL", "Hanmail", "user@hanmail.net")
_add("EMAIL", "Yahoo", "user@yahoo.com")
_add("EMAIL", "MS Outlook", "user@outlook.kr")
_add("EMAIL", "특수문자 +", "first.last+tag@gmail.com")
_add("EMAIL", "숫자 시작", "12345@naver.com")
_add("EMAIL", "긴 도메인", "info@some.very.long.example.co.kr")
_add("EMAIL", "여러 개 한 문장",
     "From: a@x.com, To: b@y.com, CC: c@z.com")

# ─────── POSTAL_CODE 추가 ───────
_add("POSTAL_CODE", "5자리 대구 (41~43)", "우편번호 41940")
_add("POSTAL_CODE", "5자리 광주 (61~62)", "우편번호 61500")
_add("POSTAL_CODE", "5자리 대전 (34~35)", "우편번호 34112")
_add("POSTAL_CODE", "5자리 울산 (44~45)", "우편번호 44999")
_add("POSTAL_CODE", "5자리 강원 (24~26)", "우편번호 24400")
_add("POSTAL_CODE", "5자리 충북 (27~29)", "우편번호 27500")
_add("POSTAL_CODE", "5자리 충남 (31~33)", "우편번호 31100")
_add("POSTAL_CODE", "5자리 전북 (54~56)", "우편번호 54900")
_add("POSTAL_CODE", "5자리 전남 (57~59)", "우편번호 57700")
_add("POSTAL_CODE", "5자리 경북 (36~40)", "우편번호 37200")
_add("POSTAL_CODE", "5자리 경남 (50~53)", "우편번호 51100")
_add("POSTAL_CODE", "세종 (30)", "우편번호 30100")

# ─────── IP 추가 ───────
_add("IP", "IPv4 SK (211.xxx)", "211.43.222.150")
_add("IP", "IPv4 KT (39.xxx)", "39.115.100.1")
_add("IP", "IPv4 LG (61.xxx)", "61.32.45.78")
_add("IP", "IPv4 게이트웨이", "10.0.0.1")
_add("IP", "IPv4 멀티캐스트", "224.0.0.1")
_add("IP", "IPv6 link-local", "fe80::1")
_add("IP", "IPv6 unique-local", "fc00::1234")
_add("IP", "IPv6 full", "2001:0db8:85a3:0000:0000:8a2e:0370:7334")

# ─────── VEHICLE 추가 ───────
_add("VEHICLE", "자가용 다", "12다3456")
_add("VEHICLE", "자가용 라", "34라1234")
_add("VEHICLE", "자가용 거 (영업)", "12거3456")
_add("VEHICLE", "자가용 너", "34너1234")
_add("VEHICLE", "자가용 더", "78더5678")
_add("VEHICLE", "택시 자", "78자9012")
_add("VEHICLE", "택시 차", "12차5678")
_add("VEHICLE", "신형 4자리 (전기차 100~)", "100가1234",
     "전기차 등 신형은 100~ 시작 — 패턴 매칭됨")
_add("VEHICLE", "전기차 영업용", "200사5678")
_add("VEHICLE", "잘못된 한글 (장 거부)", "12장 3456", "장 = 코드 아님")
_add("VEHICLE", "한국어 단위 원 (거부)", "120원 3000", "원 = 화폐")

# ─────── URL 추가 ───────
_add("URL", "FTP", "ftp://example.com/file.zip")
_add("URL", "정부 사이트", "https://www.gov.kr/portal/main")
_add("URL", "파라미터 다수",
     "https://example.com/search?q=한국&page=2&sort=desc")
_add("URL", "Port 명시", "http://localhost:8080/admin")
_add("URL", "subdomain 깊음",
     "https://a.b.c.d.example.co.kr/page")
_add("URL", "fragment 포함", "https://example.com/page#section-3")
_add("URL", "한글 path (UTF-8)", "https://ko.wikipedia.org/wiki/한국")

# ─────── ADDRESS 추가 ───────
_add("ADDRESS", "도로명 대구",
     "대구광역시 중구 동성로 123")
_add("ADDRESS", "도로명 광주",
     "광주광역시 동구 충장로 45")
_add("ADDRESS", "도로명 대전",
     "대전광역시 유성구 대학로 99")
_add("ADDRESS", "도로명 울산",
     "울산광역시 남구 삼산로 100")
_add("ADDRESS", "도로명 세종 (광역 1단계)",
     "세종특별자치시 한누리대로 411")
_add("ADDRESS", "도로명 제주",
     "제주특별자치도 제주시 노형로 1")
_add("ADDRESS", "도로명 강원",
     "강원특별자치도 춘천시 중앙로 1")
_add("ADDRESS", "도로명 전북",
     "전북특별자치도 전주시 완산구 효자로 1")
_add("ADDRESS", "도로명 충북",
     "충청북도 청주시 상당구 상당로 110")
_add("ADDRESS", "지번 (서울 종로)",
     "주소: 서울특별시 종로구 효자동 산 1-1")
_add("ADDRESS", "동/번지 + 호",
     "서울 강남구 역삼동 123-4 ○○빌딩 101호")
_add("ADDRESS", "공동주택 + 동/호",
     "주소: 서울특별시 강남구 테헤란로 152 ○○아파트 102동 1101호")
_add("ADDRESS", "약칭 광역 (서울)",
     "주소: 서울 강남구 테헤란로 152")
_add("ADDRESS", "약칭 광역 (경기 + 시)",
     "주소: 경기 성남시 분당구 정자로 1")
_add("ADDRESS", "주소 키워드 anchor",
     "주소 서울특별시 강남구 테헤란로 152")

# ─────── ACCOUNT 추가 ───────
_add("ACCOUNT", "국민은행 14자리", "계좌 110-1234-567890")
_add("ACCOUNT", "신한은행 12자리", "계좌 110-123-456789")
_add("ACCOUNT", "농협 13자리 (3-4-6)", "계좌 301-1234-567890")
_add("ACCOUNT", "우리은행", "계좌번호 1002-123-456789")
_add("ACCOUNT", "토스뱅크", "계좌 1000-1234-5678")
_add("ACCOUNT", "카카오뱅크", "계좌: 3333-12-1234567")
_add("ACCOUNT", "여러 개 한 문장",
     "급여 계좌 110-1234-567890, 송금용 계좌 301-1234-567890")

# ─────── PERSON 추가 (성씨/이름 다변화) ───────
_add("PERSON", "성명 — 신씨", "성명: 신유진")
_add("PERSON", "성명 — 한씨", "성명 한도연")
_add("PERSON", "성명 — 송씨", "성명: 송하은")
_add("PERSON", "성명 — 류씨 (드문)", "성명: 류태호")
_add("PERSON", "성명 — 노씨", "성명: 노예린")
_add("PERSON", "복성 — 제갈", "참석자: 제갈공명",
     "역사 인물 — 복성 패턴 학습용 예시")
_add("PERSON", "복성 — 선우", "참석자: 선우진")
_add("PERSON", "복성 — 독고", "참석자: 독고영재")
_add("PERSON", "복성 — 사공", "참석자: 사공일")
_add("PERSON", "외자 이름", "성명: 김민")
_add("PERSON", "이름 라벨", "이름: 박서윤")
_add("PERSON", "본인 라벨", "본인: 강민지")
_add("PERSON", "고객 라벨", "고객명: 이주원")
_add("PERSON", "직책 인접 (대표)", "조하준 대표가 발표")
_add("PERSON", "직책 인접 (회장)", "임지아 회장님 인사")
_add("PERSON", "직책 인접 (사장)", "박지훈 사장이 결재")
_add("PERSON", "직책 인접 (이사)", "김도윤 이사 면담")
_add("PERSON", "직책 인접 (변호사)", "정유진 변호사 선임")
_add("PERSON", "직책 인접 (교수)", "최도현 교수가 강의")
_add("PERSON", "직책 인접 (박사)", "강민지 박사가 발표")
_add("PERSON", "직책 인접 (소령)", "김도윤 소령")
_add("PERSON", "직책 인접 (경위)", "박지훈 경위")
_add("PERSON", "직책 인접 (군수)", "이서연 군수")
_add("PERSON", "직책 인접 (시장)", "최도현 시장 회견")
_add("PERSON", "직책 인접 (구청장)", "강민지 구청장")
_add("PERSON", "직책 인접 (도지사)", "박지훈 도지사 결정")
_add("PERSON", "직책 인접 (총장)", "이서연 총장")
_add("PERSON", "직책 인접 (대법관)", "정유진 대법관")
_add("PERSON", "3중 매크로 — 국방부 + 대장",
     "국방부 박지훈 대장")
_add("PERSON", "3중 매크로 — 검찰청 + 검사",
     "검찰청 정유진 검사")
_add("PERSON", "3중 매크로 — 행정안전부 + 사무관",
     "행정안전부 박지훈 사무관")
_add("PERSON", "3중 매크로 — 보건복지부 + 과장",
     "보건복지부 이서연 과장")
_add("PERSON", "3중 매크로 — 교육부 + 차관",
     "교육부 강민지 차관")
_add("PERSON", "3중 매크로 — 대법원 + 대법원장",
     "대법원 최도현 대법원장")
_add("PERSON", "3중 매크로 — 헌법재판소 + 헌법재판관",
     "헌법재판소 박지훈 헌법재판관")
_add("PERSON", "이름 + 씨", "박지훈 씨")
_add("PERSON", "이름 + 님", "박지훈 님")
_add("PERSON", "이름 + 선생님", "박지훈 선생님")
_add("PERSON", "동음이의 부정 (보고)", "보고 결과 적합",
     "일반 단어")
_add("PERSON", "동음이의 부정 (장관)", "장관 회의 개최",
     "장관 단독 = 직책, PII 아님")
_add("PERSON", "지역명 부정 (서울)", "서울에서 발표",
     "지역명 — PII 아님")

# ─────── DOC_ID 추가 ───────
_add("DOC_ID", "국방부 문서", "문서번호: 국방부-인사-2024-00123")
_add("DOC_ID", "외교부 문서", "외교부-기획-2025-00456")
_add("DOC_ID", "환경부 문서", "환경부-총무과-2024-77777")
_add("DOC_ID", "법무부 문서", "법무부-감사-2024-00001")
_add("DOC_ID", "검찰청 문서", "검찰청-수사-2024-11111")
_add("DOC_ID", "경찰청 문서", "경찰청-총무-2024-22222")
_add("DOC_ID", "소방청 문서", "소방청-구조-2024-33333")
_add("DOC_ID", "여가부 문서", "여가부-정책-2024-44444")

# ─────── PETITION_ID 추가 ───────
_add("PETITION_ID", "국민신문고", "국민신문고 2024-12345")
_add("PETITION_ID", "이의신청", "이의신청-2024-00567")
_add("PETITION_ID", "정보공개 (긴 형식)",
     "정보공개청구번호: 2025-정보공개-99999")
_add("PETITION_ID", "감사청구", "감사청구-2024-00111")
_add("PETITION_ID", "공익신고", "공익신고-2024-00222")

# ─────── EMPLOYEE_ID 추가 ───────
_add("EMPLOYEE_ID", "사번 8자리", "사번 20240001")
_add("EMPLOYEE_ID", "사번 6자리", "사번: 123456")
_add("EMPLOYEE_ID", "사번 콜론", "사번:20231234")
_add("EMPLOYEE_ID", "사원번호 키워드", "사원번호: 1234567")
_add("EMPLOYEE_ID", "사번 + 부서",
     "사번 20231234 (정책기획팀)")

# ─────── PNU 추가 ───────
_add("PNU", "부산 (시도 26)", "PNU: 2611010100100010000")
_add("PNU", "대구 (시도 27)", "2729011100100050003")
_add("PNU", "인천 (시도 28)", "2811011200100010000")
_add("PNU", "광주 (시도 29)", "2911011100100100007")
_add("PNU", "대전 (시도 30)", "3011011200100200004")
_add("PNU", "강원 (시도 51)", "5111011000100300001")
_add("PNU", "전남 (시도 46)", "4611011300100100002")
_add("PNU", "여러 개 한 문장",
     "필지 1111011600100010000 및 4129010200200500015")


# ═══════════════════════════════════════════════════════════════════════
# Part 2 — 현실 시나리오 문서 (각 5+개 PII 포함)
# ═══════════════════════════════════════════════════════════════════════

SCENARIO_DOCS: list[tuple[str, str]] = [
    ("결재공문 (기획재정부)", """[기획재정부 결재공문]
문서번호: 기재부-인사-2024-00123

수신자: 행정안전부 장관
참조: 김도윤 과장 (010-2847-3915, dykim@moef.go.kr)

신청인: 박지훈
주민등록번호: 880101-1234568
연락처: 010-7491-0376
주소: 서울특별시 종로구 세종대로 209 (우편번호 03187)

위 사항을 확인하여 주시기 바랍니다.

기안자: 이서연 사무관 (사번 20231234)
검토자: 최도현 과장
결재자: 강민지 국장
"""),

    ("민원 답변서", """[민원 답변서]
민원번호 2024-민원-00567

민원인: 정유진
주민등록번호: 950101-2345676
연락처: 010-3258-6042
이메일: yujin.jung@naver.com
주소: 경기도 성남시 분당구 정자로 1

귀하의 민원에 대해 다음과 같이 답변드립니다.

정유진 님께서 제출하신 사항은 보건복지부에서 검토 중이며,
처리 결과는 통보드릴 예정입니다.

답변 담당: 한도연 주무관 (031-624-7185)
"""),

    ("인사평가서", """[인사 평가서]
문서번호: 행안부-인사-2024-00789

성명: 송하은 (35세)
주민등록번호: 880515-2234567
사번: 20180123
부서: 정책기획팀
직급: 사무관 (5급)
이메일: heun.song@mois.go.kr
연락처: 010-5093-2186

평가 의견:
본인은 성실하게 직무를 수행하였으며 안전사고는 없었다.
민원 처리 우수 사례 다수 보유.

평가자: 임수아 과장 (서기관)
검토자: 윤서준 국장 (이사관)
"""),

    ("처방전 (의료)", """[처방전]
처방번호: 202412010001
요양기관기호: 12345678 (○○대학교병원)

환자명: 최도현
주민등록번호: 930415-1234567
건강보험증번호: 12345678901
연락처: 010-8624-1759
주소: 부산광역시 해운대구 우동로 123

진단:
주상병 I10 (본태성 고혈압)
부상병 E11.9 (제2형 당뇨병)

처방:
약품코드 123456789 메트포르민 500mg
약품코드 234567890 암로디핀 5mg

담당의: 신유진 의사
"""),

    ("경찰 사건처리 보고서", """[경찰 사건 처리 보고서]
문서번호: 경찰청-수사과-2024-00123

수사관: 강민지 경감 (010-4806-5279)
사건번호 2024가합12345 (관련 민사)
형사 사건: 2024고합890

피의자 정보:
성명: 박지훈 (남자, 32세)
주민등록번호: 920701-1234567
연락처: 010-6135-9082
주소: 인천광역시 남동구 인주대로 200

피해자:
성명: 송하은 (35세, 여)
주민번호: 880515-2234567

차량 정보:
용의 차량: 12가3456
신고 차량: 87바1234

조사 내용:
본 사건은 일반 도로 위 사고로, 정유진 검사가 송치 검토 중.
"""),

    ("법원 송부 문서", """[법원 송부 문서]
사건: 2024가합12345 (민사 합의)

원고: 박지훈(880101-1234568, 010-1573-4829)
주소: 서울특별시 강남구 역삼동 123
대리인: 정유진 변호사 (법무법인 ○○, 02-784-1259)

피고: 김도윤(950101-2345676, 010-4926-7158)
주소: 경기도 성남시 분당구 정자로 1

청구 취지:
피고는 원고에게 50,000,000원을 지급하라.

담당 판사: 이서연 부장판사
법원 사무관: 한도연 (031-624-7185)

관련 사건: 2023고합567 (형사), 2024차10001 (지급명령)
"""),

    ("국회 의원 명함 (PII 노출)", """[명함]

대한민국 국회의원
송하은 (제22대, 더불어민주당)

연락처: 02-784-2156
휴대전화: 010-3074-8916
이메일: heun.song@assembly.go.kr
사무실: 서울특별시 영등포구 의사당대로 1 의원회관 999호
보좌관: 박지훈 (010-8351-6429)
"""),

    ("외국인 출입국 정보", """[외국인 등록 정보]

성명 (한글): 마이클잭슨
성명 (영문): Michael Jackson
외국인등록번호: 850315-5345676
여권번호: M99887766
거주지: 서울특별시 용산구 한남대로 21
연락처: 010-7269-5083 (한국 휴대폰)
이메일: mj@example.com
"""),

    ("토지·차량 등기", """[토지·차량 등기 정보]

소유자: 강민지
주민등록번호: 770515-1234565
주소: 부산광역시 해운대구 마린시티로 38

소유 토지:
필지고유번호: 1111011600100010000 (서울특별시 종로구)
필지고유번호: 4129010200200500015 (경기도 안양시 — 산번지)

소유 차량:
12가3456 (자가용)
99하1234 (렌터카)

연락처: 010-5418-9672
사업자: 1208147521 (개인사업자)
계좌: 110-4872-153649 (국민은행)
"""),

    ("자유 자연어 — 영화 리뷰 (실세계 PII 노출)", """이 영화 정말 좋네요!
어릴 때 김민서 배우 팬이었는데 이번 작품도 훌륭합니다.
혹시 자막 파일 갖고 계신 분 있나요?
보내주세요: dodadan@naver.com 으로요.

촬영지가 서울특별시 종로구 인사동길 12 근처라던데 가보고 싶네요.
참고: https://example.com/movie/info
"""),

    ("자유 자연어 — SNS 게시글", """오늘 정말 짜증나네...
회사 김부장이 또 일을 떠넘김. 박과장도 협조 안 함.
내일 회의에 송하은 차장님이 오실 예정.

문의는 010-9527-3641 로 부탁드려요.
이메일: contact@mycompany.co.kr
"""),

    ("자유 자연어 — 채용 공고 본문", """[채용공고]

회사: 카카오 (사업자등록번호 120-81-47521)
직무: 백엔드 개발자

지원 자격:
- 컴퓨터공학 학사 이상
- 한국어/영어 의사소통 능력

지원 방법:
이메일 hr@kakaocorp.com 으로 이력서 송부
문의: 02-6712-1234 / 031-572-3068 (Fax)

근무지: 경기도 성남시 분당구 판교역로 152
"""),

    ("회의록 (간부회의)", """[제48차 간부회의록]
문서번호: 행안부-총무과-2024-00890
일시: 2024-04-15 14:00~16:00

참석자:
- 강민지 국장 (010-2847-3915)
- 박지훈 과장 (010-8624-1759)
- 이서연 사무관 (사번 20231234, sylee@mois.go.kr)
- 정유진 주무관

논의:
1. 민원번호 2024-민원-00567 처리 방안
2. 사건번호 2024가합12345 관련 협조 요청
3. 사업자 120-81-47521 (○○○○) 위탁 검토

결정:
- 차주까지 답변서 송부 (담당: 이서연 사무관)
- 다음 회의 2024-04-22 10:00

기록: 정유진 주무관 (yjjung@mois.go.kr, 010-5093-2186)
"""),

    ("의료기관 카드결제 영수증", """[영수증]
○○대학교병원 (사업자등록번호 220-81-62517)
일시: 2024-05-18 14:32

환자: 송하은
주민번호: 880515-2234567
건강보험증번호: 12345678901
처방번호 202405180042
주상병 K29.7 (위염, 상세불명)
약품코드 234567890 (오메프라졸)

진료비: 35,400원
결제 카드: 4242-4242-4242-4242 (Visa)
연락처: 010-3258-6042
주소: 서울특별시 강남구 테헤란로 152

문의: 02-2072-2114
"""),

    ("종합 다중 PII 단일 문단 (혼합)", """담당관 김도윤 사무관(010-7491-0376,
dykim@mois.go.kr)이 신청인 박지훈(880101-1234568,
서울특별시 종로구 세종대로 209, 우편번호 03187,
계좌 110-4872-153649)의 사업자 120-81-47521 등록 변경 건을
사건번호 2024가합12345 와 연계하여 검토 중이며, 처방번호
202412010001(주상병 I10), 차량 12가3456, 여권 M12345678,
필지 1111011600100010000 모두 본인 확인 필요.
"""),
]


# ═══════════════════════════════════════════════════════════════════════
# Part 3 — 출력 함수
# ═══════════════════════════════════════════════════════════════════════

STRATEGIES = ["tokenize", "redact", "asterisk", "partial", "hashed", "fpe"]


def _process_strategies(text: str) -> OrderedDict:
    out = OrderedDict()
    for strategy in STRATEGIES:
        anon = Anonymizer(mode=ProcessingMode.PARANOID, strategy=strategy)
        out[strategy] = anon.process(text).text
    return out


def _detect_summary(text: str) -> str:
    detected = list(detect_all(text))
    if not detected:
        return "(검출 없음)"
    return " · ".join(f"{d.label}: {d.text[:18]}" for d in detected[:6])


def print_terminal(units=True, scenarios=True):
    print("\n" + "█" * 90)
    print("█  k-pii 사용자 전용 대형 데모 — 300+ 케이스 + 12 현실 시나리오  █")
    print("█" * 90)

    if units:
        print(f"\n{'═'*90}")
        print(f"  Part 1 — 카테고리별 단위 케이스 ({len(UNIT_CASES)} 케이스)")
        print(f"{'═'*90}\n")

        current = None
        for case in UNIT_CASES:
            if case.label != current:
                current = case.label
                print(f"\n┌─[{case.label}]")
            print(f"│ {case.desc}")
            print(f"│   Before:  {case.text}")
            anon = Anonymizer(mode=ProcessingMode.PARANOID, strategy="tokenize")
            tok = anon.process(case.text).text
            anon2 = Anonymizer(mode=ProcessingMode.PARANOID, strategy="partial")
            par = anon2.process(case.text).text
            anon3 = Anonymizer(mode=ProcessingMode.PARANOID, strategy="redact")
            red = anon3.process(case.text).text
            print(f"│   tokenize: {tok}")
            print(f"│   partial:  {par}")
            print(f"│   redact:   {red}")
            print(f"│   detected: {_detect_summary(case.text)}")
            if case.note:
                print(f"│   ⓘ note:  {case.note}")
            print("│")

    if scenarios:
        print(f"\n\n{'═'*90}")
        print(f"  Part 2 — 현실 시나리오 문서 ({len(SCENARIO_DOCS)} 문서)")
        print(f"{'═'*90}\n")

        for i, (name, doc) in enumerate(SCENARIO_DOCS, 1):
            print(f"\n{'━'*90}")
            print(f"  [시나리오 {i}/{len(SCENARIO_DOCS)}] {name}")
            print(f"{'━'*90}\n")
            print("── 원본 ──")
            print(doc)
            print("\n── tokenize (Vault 가역 가명화) ──")
            anon = Anonymizer(mode=ProcessingMode.PARANOID, strategy="tokenize")
            result = anon.process(doc)
            print(result.text)
            print(f"\n  결합위험도: {result.combined_risk.combined_risk.name}")
            print(f"  by_label: {dict(result.summary['by_label'])}")
            print(f"  Vault: {len(result.vault)} 토큰")
            print("\n── partial (실무 부분 마스킹) ──")
            anon2 = Anonymizer(mode=ProcessingMode.PARANOID, strategy="partial")
            print(anon2.process(doc).text)


def render_markdown(units=True, scenarios=True) -> str:
    lines = ["# k-pii 사용자 전용 대형 데모\n"]
    lines.append(f"**{len(UNIT_CASES)} 카테고리별 케이스 + {len(SCENARIO_DOCS)} 현실 시나리오 문서**\n")
    lines.append("모든 출력은 `ProcessingMode.PARANOID` 기준 — 가장 엄격한 모드.\n")

    if units:
        lines.append(f"\n---\n\n## Part 1 — 카테고리별 단위 케이스\n")
        current = None
        for case in UNIT_CASES:
            if case.label != current:
                current = case.label
                lines.append(f"\n### {case.label}\n")
            lines.append(f"#### {case.desc}")
            if case.note:
                lines.append(f"> 💡 {case.note}\n")
            results = _process_strategies(case.text)
            lines.append(f"- **입력:** `{case.text}`")
            lines.append(f"- **검출:** `{_detect_summary(case.text)}`")
            lines.append("")
            lines.append("| 전략 | 결과 |")
            lines.append("|---|---|")
            for strategy, out in results.items():
                out_md = out.replace("|", "\\|").replace("\n", "<br>")
                lines.append(f"| `{strategy}` | `{out_md}` |")
            lines.append("")

    if scenarios:
        lines.append(f"\n---\n\n## Part 2 — 현실 시나리오 문서\n")
        for i, (name, doc) in enumerate(SCENARIO_DOCS, 1):
            lines.append(f"\n### {i}. {name}\n")
            lines.append("**원본:**\n```")
            lines.append(doc)
            lines.append("```\n")
            anon = Anonymizer(mode=ProcessingMode.PARANOID, strategy="tokenize")
            result = anon.process(doc)
            lines.append("**tokenize 처리:**\n```")
            lines.append(result.text)
            lines.append("```\n")
            lines.append(f"- 결합 위험도: **{result.combined_risk.combined_risk.name}**")
            lines.append(f"- 검출 카테고리: `{dict(result.summary['by_label'])}`")
            lines.append(f"- Vault 토큰: **{len(result.vault)}개**\n")
            anon2 = Anonymizer(mode=ProcessingMode.PARANOID, strategy="partial")
            lines.append("**partial 처리 (부분 마스킹):**\n```")
            lines.append(anon2.process(doc).text)
            lines.append("```\n")
    return "\n".join(lines)


_HTML_CSS = """body{font-family:-apple-system,"Noto Sans KR",sans-serif;background:#f5f5f5;
margin:0;padding:20px;max-width:1500px;color:#222}
.header{background:#1a237e;color:#fff;padding:20px 28px;border-radius:8px;}
.header h1{margin:0;font-size:24px}
.header .meta{opacity:.85;font-size:14px;margin-top:8px}
.section{background:#fff;padding:20px;border-radius:8px;margin-top:20px;
box-shadow:0 1px 3px rgba(0,0,0,.08)}
.section h2{margin:0 0 12px;color:#1a237e;border-bottom:2px solid #1a237e;padding-bottom:8px}
.cat-block{margin:18px 0;padding:14px;background:#f9f9fb;border-radius:6px}
.cat-block h3{margin:0 0 10px;color:#3949ab;font-size:16px}
.case{border-left:4px solid #7986cb;padding:10px 14px;margin:10px 0;background:#fff;border-radius:0 4px 4px 0}
.case h4{margin:0 0 6px;font-size:13px;font-weight:600}
.case .note{background:#fff3e0;padding:6px 10px;border-radius:4px;font-size:12px;margin:5px 0}
.case .input{font-family:Consolas,monospace;background:#263238;color:#b3e5fc;padding:8px 12px;
border-radius:4px;font-size:13px;margin:5px 0;white-space:pre-wrap}
.case .detected{font-size:11px;color:#666;margin:4px 0}
table.s{width:100%;border-collapse:collapse;margin-top:8px;font-size:12px}
table.s th{width:90px;text-align:left;padding:6px 10px;background:#eceff1;font-weight:500}
table.s td{padding:6px 10px;font-family:Consolas,monospace;background:#fafafa;
border-top:1px solid #eee;word-break:break-all}
.scenario{background:#fff;padding:18px;border-radius:6px;margin:16px 0;
border:1px solid #e0e0e0}
.scenario h3{margin:0 0 10px;color:#c62828}
.scenario pre{background:#263238;color:#e8f5e9;padding:12px;border-radius:4px;
font-size:12px;line-height:1.5;overflow-x:auto;white-space:pre-wrap}
.scenario pre.before{color:#ffccbc}
.scenario pre.after{color:#c8e6c9}
.tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;background:#5e35b1;color:#fff}
.risk-CRITICAL{background:#d32f2f;color:#fff}
.risk-HIGH{background:#f57c00;color:#fff}
.risk-MEDIUM{background:#fbc02d;color:#000}
.risk-LOW{background:#388e3c;color:#fff}
.risk-INFO{background:#90a4ae;color:#fff}
"""


def render_html(units=True, scenarios=True) -> str:
    parts = ['<!doctype html><html lang="ko"><head><meta charset="utf-8">'
             '<title>k-pii 사용자 전용 데모</title>',
             f'<style>{_HTML_CSS}</style></head><body>']
    parts.append(f'<div class="header"><h1>k-pii 사용자 전용 대형 데모</h1>'
                 f'<div class="meta">{len(UNIT_CASES)}개 단위 케이스 + '
                 f'{len(SCENARIO_DOCS)}개 시나리오 문서 · '
                 f'모든 출력: PARANOID 모드</div></div>')

    if units:
        parts.append('<div class="section"><h2>Part 1 — 카테고리별 단위 케이스</h2>')
        current = None
        for case in UNIT_CASES:
            if case.label != current:
                if current is not None:
                    parts.append('</div>')
                current = case.label
                parts.append(f'<div class="cat-block"><h3>{html_mod.escape(case.label)}</h3>')
            results = _process_strategies(case.text)
            rows = ""
            for strategy, out in results.items():
                rows += (f'<tr><th>{strategy}</th>'
                         f'<td>{html_mod.escape(out) if out else "<em>(빈 결과)</em>"}</td></tr>')
            note_html = (f'<div class="note">💡 {html_mod.escape(case.note)}</div>'
                         if case.note else '')
            parts.append(
                f'<div class="case">'
                f'<h4>{html_mod.escape(case.desc)}</h4>'
                f'<div class="input">{html_mod.escape(case.text)}</div>'
                f'<div class="detected">{html_mod.escape(_detect_summary(case.text))}</div>'
                f'{note_html}'
                f'<table class="s"><tbody>{rows}</tbody></table>'
                f'</div>'
            )
        if current:
            parts.append('</div>')
        parts.append('</div>')

    if scenarios:
        parts.append('<div class="section"><h2>Part 2 — 현실 시나리오 문서</h2>')
        for i, (name, doc) in enumerate(SCENARIO_DOCS, 1):
            anon = Anonymizer(mode=ProcessingMode.PARANOID, strategy="tokenize")
            result = anon.process(doc)
            risk = result.combined_risk.combined_risk.name
            anon2 = Anonymizer(mode=ProcessingMode.PARANOID, strategy="partial")
            partial = anon2.process(doc).text
            vault_rows = "".join(
                f'<tr><td>{html_mod.escape(e.token)}</td>'
                f'<td>{html_mod.escape(e.original)}</td></tr>'
                for e in result.vault.entries()
            )
            parts.append(
                f'<div class="scenario">'
                f'<h3>{i}. {html_mod.escape(name)} '
                f'<span class="tag risk-{risk}">{risk}</span></h3>'
                f'<h4>원본</h4><pre class="before">{html_mod.escape(doc)}</pre>'
                f'<h4>tokenize 처리</h4><pre class="after">{html_mod.escape(result.text)}</pre>'
                f'<h4>partial 처리</h4><pre class="after">{html_mod.escape(partial)}</pre>'
                f'<h4>Vault 복원표 ({len(result.vault)} 토큰)</h4>'
                f'<table class="s"><tr><th>토큰</th><td>원본</td></tr>{vault_rows}</table>'
                f'</div>'
            )
        parts.append('</div>')

    parts.append('</body></html>')
    return "".join(parts)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--md", help="Markdown 저장")
    p.add_argument("--html", help="HTML 저장")
    p.add_argument("--scenarios", action="store_true",
                   help="시나리오만 (단위 케이스 생략)")
    p.add_argument("--units", action="store_true",
                   help="단위 케이스만 (시나리오 생략)")
    p.add_argument("--no-terminal", action="store_true",
                   help="터미널 출력 생략 (파일만)")
    args = p.parse_args()

    show_units = not args.scenarios
    show_scenarios = not args.units

    if not args.no_terminal:
        print_terminal(units=show_units, scenarios=show_scenarios)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(render_markdown(units=show_units, scenarios=show_scenarios))
        print(f"\n→ Markdown 저장: {args.md}", file=sys.stderr)
    if args.html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(render_html(units=show_units, scenarios=show_scenarios))
        print(f"→ HTML 저장: {args.html}", file=sys.stderr)

    print(f"\n총 {len(UNIT_CASES)} 단위 케이스 + {len(SCENARIO_DOCS)} 시나리오", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
