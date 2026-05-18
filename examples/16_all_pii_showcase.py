"""16. 모든 PII 카테고리 × 6 처리 전략 매트릭스 — Before/After 비교.

실행::

    python examples/16_all_pii_showcase.py [--html out.html] [--md out.md]

50+ 샘플 케이스를 모든 처리 전략에 적용하여 비교 출력.
부정 케이스 (가짜 PII / 일반 어휘) 도 포함하여 FP 거부도 검증.
"""
from __future__ import annotations

import argparse
import dataclasses
import html
import sys
from collections import OrderedDict
from typing import Iterable

from k_pii import Anonymizer, ProcessingMode
from k_pii.detect import detect_all


@dataclasses.dataclass
class SampleCase:
    label: str            # 카테고리 식별자 (RRN, PHONE, ...)
    description: str      # 케이스 설명
    text: str             # 입력 텍스트
    expected_labels: list[str] = dataclasses.field(default_factory=list)
    note: str = ""


# ─────────────────────────────────────────────────────────────────────
# 모든 PII 카테고리 × 다양한 형태 케이스
# ─────────────────────────────────────────────────────────────────────

SAMPLES: list[SampleCase] = [
    # === 1. RRN (주민등록번호) — 모든 형태 ===
    SampleCase("RRN", "표준 하이픈 형태",
               "주민번호: 880101-1234568", ["RRN"]),
    SampleCase("RRN", "하이픈 없음 (13자리 합친)",
               "신청인 정보 8801011234568 확인", ["RRN"]),
    SampleCase("RRN", "공백 구분자",
               "주민등록번호 880101 1234568", ["RRN"]),
    SampleCase("RRN", "체크섬 fail (후-2020 무작위화)",
               "880101-1999999 입니다", ["RRN"],
               note="신뢰도 0.7 — 후-2020 무작위 가능"),
    SampleCase("RRN", "2000년대생 (gender 3)",
               "주민번호 001225-3000008", ["RRN"]),

    # === 2. FRN (외국인등록번호) ===
    SampleCase("FRN", "외국인등록번호 (gender 5)",
               "외국인등록번호: 850315-5345676", ["FRN"]),

    # === 3. 사업자등록번호 (체크섬 검증) ===
    SampleCase("BUSINESS_REG", "카카오 사업자번호 (실제 valid)",
               "사업자등록번호: 120-81-47521", ["BUSINESS_REG"]),
    SampleCase("BUSINESS_REG", "하이픈 없는 valid 사업자번호",
               "사업자 1208147521", ["BUSINESS_REG"]),

    # === 4. 법인등록번호 ===
    SampleCase("CORP_REG", "한국전력 법인번호 (RRN 충돌 우선순위 검증)",
               "법인등록번호: 191211-0006637", ["CORP_REG"],
               note="6자리 첫부분 = 19121 (날짜 형식이지만 체크섬 실패 → CORP_REG 우선)"),

    # === 5. 운전면허 ===
    SampleCase("DRIVER_LICENSE", "운전면허 (하이픈 형식)",
               "면허번호 11-90-123456-78", ["DRIVER_LICENSE"]),
    SampleCase("DRIVER_LICENSE", "운전면허 (키워드 anchor)",
               "운전면허 119012345678 정지 처분", ["DRIVER_LICENSE"]),

    # === 6. 여권 ===
    SampleCase("PASSPORT", "일반 여권 M prefix",
               "여권: M12345678", ["PASSPORT"]),
    SampleCase("PASSPORT", "외교관 여권 D",
               "외교관 여권 D12345678", ["PASSPORT"]),
    SampleCase("PASSPORT", "2024.12.16 신형 PP",
               "여권 PP87654321 발급", ["PASSPORT"]),

    # === 7. 신용카드 (Luhn) ===
    SampleCase("CARD", "Visa (4 prefix) 하이픈 구분",
               "카드 4242-4242-4242-4242", ["CARD"]),
    SampleCase("CARD", "Mastercard (5 prefix) 공백 구분",
               "5555 5555 5555 4444", ["CARD"]),
    SampleCase("CARD", "한국 국내전용 (9 prefix)",
               "9410123456789012", ["CARD"]),

    # === 8. 의료보험 ===
    SampleCase("MEDICAL_INSURANCE", "건강보험증 (키워드 필수)",
               "건강보험증번호: 12345678901", ["MEDICAL_INSURANCE"]),

    # === 9. 처방번호 (식의약) ===
    SampleCase("PRESCRIPTION_ID", "처방번호 12자리 (YYYYMMDD + 일련)",
               "처방번호 202412010001", ["PRESCRIPTION_ID"]),
    SampleCase("PRESCRIPTION_ID", "의료기관기호 8자리",
               "요양기관기호: 12345678", ["PRESCRIPTION_ID"]),

    # === 11. EDI 약품코드 ===
    SampleCase("EDI_DRUG", "약품코드 9자리",
               "약품코드 123456789 처방", ["EDI_DRUG"]),

    # === 12. 법원 사건번호 ===
    SampleCase("COURT_CASE", "민사 합의 (가합)",
               "사건번호: 2024가합12345", ["COURT_CASE"]),
    SampleCase("COURT_CASE", "형사 (고합)",
               "2023고합567 선고", ["COURT_CASE"]),
    SampleCase("COURT_CASE", "헌법재판소 (헌마)",
               "2024헌마789 결정", ["COURT_CASE"]),

    # === 13. 전화번호 (모든 형태) ===
    SampleCase("PHONE", "휴대 표준 (하이픈)",
               "연락처: 010-1234-5678", ["PHONE"]),
    SampleCase("PHONE", "휴대 점 구분자",
               "010.1234.5678 으로 연락", ["PHONE"]),
    SampleCase("PHONE", "휴대 공백 구분자",
               "010 1234 5678", ["PHONE"]),
    SampleCase("PHONE", "휴대 합친 11자리",
               "전화 01012345678", ["PHONE"]),
    SampleCase("PHONE", "국제 형식 +82",
               "Tel: +82-10-1234-5678", ["PHONE"]),
    SampleCase("PHONE", "국제 형식 0082",
               "0082 10 9876 5432", ["PHONE"]),
    SampleCase("PHONE", "서울 일반전화 02",
               "02-3456-7890 사무실", ["PHONE"]),
    SampleCase("PHONE", "지방 (031 경기)",
               "031-987-6543 본사", ["PHONE"]),
    SampleCase("PHONE", "VoIP 070",
               "070-7878-1234 인터넷전화", ["PHONE"]),

    # === 14. FAX ===
    SampleCase("FAX", "팩스번호 (키워드 anchor)",
               "팩스: 02-123-4567", ["FAX"]),
    SampleCase("FAX", "FAX 영문",
               "FAX 031-555-6677", ["FAX"]),

    # === 15. 이메일 ===
    SampleCase("EMAIL", "일반 이메일",
               "user@example.com 으로 연락", ["EMAIL"]),
    SampleCase("EMAIL", "공공 .go.kr",
               "담당: minsu@gov.go.kr", ["EMAIL"]),
    SampleCase("EMAIL", "+ 필터 기호",
               "user.name+filter@company.co.kr", ["EMAIL"]),

    # === 16. 우편번호 ===
    SampleCase("POSTAL_CODE", "신 5자리 (서울)",
               "우편번호 03187 종로구", ["POSTAL_CODE"]),
    SampleCase("POSTAL_CODE", "신 5자리 (제주)",
               "우편번호 63100 서귀포", ["POSTAL_CODE"]),

    # === 17. IP 주소 ===
    SampleCase("IP", "IPv4",
               "서버 IP: 192.168.1.100", ["IP"]),
    SampleCase("IP", "IPv6 단축",
               "주소 2001:db8::1", ["IP"]),
    SampleCase("IP", "IPv6 loopback",
               "로컬 ::1", ["IP"]),

    # === 18. 차량번호 ===
    SampleCase("VEHICLE", "자가용 (가)",
               "차량 12가3456 입차", ["VEHICLE"]),
    SampleCase("VEHICLE", "영업용 택시 (바)",
               "87바1234 운행", ["VEHICLE"]),
    SampleCase("VEHICLE", "렌터카 (하)",
               "렌터카 99하1234", ["VEHICLE"]),
    SampleCase("VEHICLE", "3자리 prefix",
               "신차 123다4567", ["VEHICLE"]),

    # === 19. URL ===
    SampleCase("URL", "HTTPS URL",
               "참고: https://www.example.com/page", ["URL"]),

    # === 20. 주소 (도로명 + 지번) ===
    SampleCase("ADDRESS", "도로명 + 시·도 + 시·군·구",
               "주소: 서울특별시 종로구 세종대로 209", ["ADDRESS"]),
    SampleCase("ADDRESS", "도로명 + 2단계 시·군·구",
               "경기도 성남시 분당구 정자로 1", ["ADDRESS"]),
    SampleCase("ADDRESS", "지번 주소",
               "주소: 서울특별시 강남구 역삼동 123", ["ADDRESS"]),

    # === 21. 계좌번호 ===
    SampleCase("ACCOUNT", "은행 계좌 (키워드 anchor)",
               "계좌: 1234-567-890123", ["ACCOUNT"]),

    # === 22. PERSON (사람 이름) — 다양한 컨텍스트 ===
    SampleCase("PERSON", "성명 필드 라벨",
               "성명: 홍길동", ["PERSON"]),
    SampleCase("PERSON", "신청인 라벨",
               "신청인 김민수", ["PERSON"]),
    SampleCase("PERSON", "직책 인접",
               "기획재정부 박영수 과장이 발표", ["PERSON"]),
    SampleCase("PERSON", "조사 인접 (자연어)",
               "장혁이 영화에 출연했다", ["PERSON"],
               note="자연어에서 조사 + 성씨 = 인명 인식"),
    SampleCase("PERSON", "복성 (남궁)",
               "성명: 남궁민수", ["PERSON"]),
    SampleCase("PERSON", "한자 surname (황보)",
               "참석자: 황보경", ["PERSON"]),
    SampleCase("PERSON", "3중 매크로 (기관+인명+직책)",
               "환경부 박영수 차관이 인사말", ["PERSON"],
               note="매크로 패턴 — 최고 신뢰 0.95"),
    SampleCase("PERSON", "약칭 매크로",
               "기재부 김민수 사무관 보고", ["PERSON"]),
    SampleCase("PERSON", "나이/성별 인접",
               "민원인 홍길동(45세)", ["PERSON"]),

    # === 23. 도메인 PII ===
    SampleCase("DOC_ID", "정부 문서번호",
               "문서번호: 기재부-인사-2024-00123", ["DOC_ID"]),
    SampleCase("PETITION_ID", "민원번호",
               "민원번호 2024-민원-00123", ["PETITION_ID"]),
    SampleCase("EMPLOYEE_ID", "공무원 사번",
               "공무원번호: 20231234", ["EMPLOYEE_ID"]),

    # === 24. PNU (토지) ===
    SampleCase("PNU", "필지고유번호 19자리",
               "PNU: 1111011600100010000", ["PNU"]),

    # ─────────────────────────────────────────────────────────
    # === 부정 검증 — FP 거부 (잡으면 안 됨) ===
    # ─────────────────────────────────────────────────────────
    SampleCase("FP-NEG", "한국어 수량 (조 단위)",
               "예산 291조 9000억 원 집행", [],
               note="VEHICLE 차량으로 오탐 X"),
    SampleCase("FP-NEG", "일반 명사 (지난·이날)",
               "지난해 이날 자신의 일을 회상", [],
               note="PERSON FP X"),
    SampleCase("FP-NEG", "동사 활용형",
               "검토 결과 모두 적정", [],
               note="검토 = 일반 단어"),
    SampleCase("FP-NEG", "Luhn 우연 통과 카드 흉내",
               "주문번호 1111-2222-3333-4444", [],
               note="BIN 1 거부 — 진짜 카드 아님"),
    SampleCase("FP-NEG", "미할당 우편번호",
               "우편번호 99999 (가짜)", [],
               note="시·도 코드 화이트리스트 거부"),
    SampleCase("FP-NEG", "잘못된 광역+기초 조합",
               "주소 경기도 강남구 어딘가", [],
               note="강남구는 서울 — 조합 거부"),
    SampleCase("FP-NEG", "부분 가명 (이미 가명화)",
               "박씨가 신고함", [],
               note="박씨 = 가명 표기 — PII 아님"),
    SampleCase("FP-NEG", "키워드 없는 의보 후보",
               "12345678901 같은 11자리", [],
               note="MEDICAL_INSURANCE 키워드 필요"),
    SampleCase("FP-NEG", "한자 인명",
               "참석자: 洪吉童", [],
               note="한자 검출 미통합 (정책)"),
]


STRATEGIES = ["tokenize", "redact", "asterisk", "partial", "hashed", "fpe"]


def _process_all_strategies(text: str) -> "OrderedDict[str, str]":
    """한 텍스트를 모든 전략으로 처리 → {strategy: result}."""
    results: OrderedDict[str, str] = OrderedDict()
    for strategy in STRATEGIES:
        # 매번 새 vault (showcase 목적)
        anon = Anonymizer(mode=ProcessingMode.STRICT, strategy=strategy)
        result = anon.process(text)
        results[strategy] = result.text
    return results


def _detect_summary(text: str) -> str:
    detected = list(detect_all(text))
    if not detected:
        return "(검출 없음)"
    return ", ".join(f"{d.label}:'{d.text[:25]}'" for d in detected[:5])


# ─────────────────────────────────────────────────────────────────────
# Terminal 출력
# ─────────────────────────────────────────────────────────────────────

def print_terminal():
    print("=" * 100)
    print("k-pii 전체 PII 카테고리 × 6 처리 전략 매트릭스")
    print("=" * 100)
    current_cat = None
    for case in SAMPLES:
        if case.label != current_cat:
            current_cat = case.label
            print(f"\n┌─[{current_cat}]")
        print(f"│  {case.description}")
        print(f"│  Before:    {case.text}")
        results = _process_all_strategies(case.text)
        for strategy, after in results.items():
            print(f"│  {strategy:10} {after}")
        detected = _detect_summary(case.text)
        print(f"│  검출:      {detected}")
        if case.note:
            print(f"│  (note)    {case.note}")
        print("│")


# ─────────────────────────────────────────────────────────────────────
# Markdown 출력 (GitHub 친화)
# ─────────────────────────────────────────────────────────────────────

def render_markdown() -> str:
    lines = []
    lines.append("# k-pii Before/After 종합 데모\n")
    lines.append(f"총 **{len(SAMPLES)}개** 케이스 (긍정 {sum(1 for c in SAMPLES if c.label != 'FP-NEG')} + "
                 f"부정 검증 {sum(1 for c in SAMPLES if c.label == 'FP-NEG')})\n")
    lines.append("각 입력에 6 처리 전략 (tokenize/redact/asterisk/partial/hashed/fpe) 적용 결과.\n")

    current_cat = None
    for case in SAMPLES:
        if case.label != current_cat:
            current_cat = case.label
            lines.append(f"\n## {current_cat}\n")
        lines.append(f"### {case.description}")
        if case.note:
            lines.append(f"> 💡 {case.note}\n")
        detected = _detect_summary(case.text)
        lines.append(f"- **입력**: `{case.text}`")
        lines.append(f"- **검출**: `{detected}`")
        lines.append("")
        lines.append("| 전략 | 결과 |")
        lines.append("|---|---|")
        results = _process_all_strategies(case.text)
        for strategy, after in results.items():
            after_md = after.replace("|", "\\|").replace("\n", "<br>")
            lines.append(f"| `{strategy}` | `{after_md}` |")
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# HTML 출력 (인터랙티브)
# ─────────────────────────────────────────────────────────────────────

_HTML_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>k-pii Before/After 데모</title>
<style>
body {{ font-family: -apple-system, "Noto Sans KR", sans-serif;
       background: #fafafa; color: #212121; margin: 0; padding: 20px; max-width: 1400px; }}
.header {{ background: #263238; color: #fff; padding: 16px 24px; border-radius: 6px; }}
.header h1 {{ margin: 0; font-size: 22px; }}
.header .meta {{ opacity: 0.8; font-size: 13px; margin-top: 6px; }}
.category {{ background: #fff; padding: 16px; border-radius: 6px;
            margin-top: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.06); }}
.category h2 {{ margin: 0 0 12px 0; color: #1976d2; }}
.case {{ border-left: 4px solid #90a4ae; padding: 10px 14px; margin: 10px 0;
        background: #f5f5f5; border-radius: 0 4px 4px 0; }}
.case.negative {{ border-left-color: #ef5350; }}
.case h3 {{ margin: 0 0 6px 0; font-size: 14px; }}
.case .note {{ background: #fff3cd; padding: 6px 10px; border-radius: 3px;
              font-size: 12px; margin: 6px 0; }}
.case .input {{ font-family: monospace; background: #263238; color: #b3e5fc;
               padding: 8px 10px; border-radius: 3px; margin: 6px 0; font-size: 13px; }}
.case .detected {{ font-size: 12px; color: #555; margin: 4px 0; }}
table.strategies {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
table.strategies th, table.strategies td {{ text-align: left; padding: 6px 10px;
       border-bottom: 1px solid #eee; font-size: 13px; }}
table.strategies th {{ width: 100px; background: #eceff1; font-weight: 500; }}
table.strategies td {{ font-family: monospace; background: #fff; }}
.tag {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px;
       background: #1976d2; color: #fff; margin-right: 4px; }}
.tag.negative {{ background: #ef5350; }}
</style>
</head>
<body>
<div class="header">
  <h1>k-pii Before/After 종합 데모</h1>
  <div class="meta">총 {n_cases}개 케이스 — 모든 PII 카테고리 × 6 처리 전략 매트릭스</div>
</div>
{body}
</body>
</html>"""


def render_html() -> str:
    sections = []
    current_cat = None
    cat_html = []

    def _flush_cat():
        if current_cat is not None:
            sections.append(
                f'<div class="category"><h2>{html.escape(current_cat)}</h2>'
                + "".join(cat_html) + '</div>'
            )

    for case in SAMPLES:
        if case.label != current_cat:
            _flush_cat()
            current_cat = case.label
            cat_html = []

        is_neg = case.label == "FP-NEG"
        tag_class = "tag negative" if is_neg else "tag"
        tag_text = "FP 거부 검증" if is_neg else case.label
        case_class = "case negative" if is_neg else "case"

        results = _process_all_strategies(case.text)
        rows = ""
        for strategy, after in results.items():
            rows += (f'<tr><th>{html.escape(strategy)}</th>'
                     f'<td>{html.escape(after) if after else "<em>(빈 결과)</em>"}</td></tr>')

        detected = _detect_summary(case.text)
        note_html = f'<div class="note">💡 {html.escape(case.note)}</div>' if case.note else ""

        cat_html.append(
            f'<div class="{case_class}">'
            f'<h3><span class="{tag_class}">{tag_text}</span> {html.escape(case.description)}</h3>'
            f'<div class="input">{html.escape(case.text)}</div>'
            f'<div class="detected">검출: {html.escape(detected)}</div>'
            f'{note_html}'
            f'<table class="strategies"><tbody>{rows}</tbody></table>'
            f'</div>'
        )
    _flush_cat()

    return _HTML_TEMPLATE.format(
        n_cases=len(SAMPLES),
        body="".join(sections),
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--html", help="HTML 리포트 저장 경로")
    p.add_argument("--md", help="Markdown 리포트 저장 경로")
    p.add_argument("--no-terminal", action="store_true",
                   help="터미널 출력 생략 (HTML/MD 만 생성)")
    args = p.parse_args()

    if not args.no_terminal:
        print_terminal()

    if args.html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(render_html())
        print(f"\n→ HTML 저장: {args.html}", file=sys.stderr)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(render_markdown())
        print(f"→ Markdown 저장: {args.md}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
