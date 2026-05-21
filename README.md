# k-pii

[![Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-699%20passed-brightgreen.svg)](#)
[![Korean PII](https://img.shields.io/badge/도메인-한국%20공공-red.svg)](#)

**한국 공공 부문 문서 (공문서·민원·인사 자료) 의 개인정보를 검출하고 가역적으로 가명화하는
Python 라이브러리. 외부 ML 의존성 없이 룰 + 사전 + 체크섬만으로 동작.**

- 한국 공무원·정부기관·공공기관 실무 도메인 최적화
- **32 PII 카테고리** — 주민등록번호·외국인등록번호·여권·사업자번호·카드·계좌·전화·이메일·주소·차량·인명·직책 등
- **개인정보보호법 + 비식별 조치 가이드라인** 직접 대응 (각 검출에 법조항 자동 부착)
- **Vault 분리 보관** — 권한 있는 사용자만 토큰 → 원본 복원
- **결합 위험도 + k-익명성** 자동 평가

```python
from k_pii import Anonymizer, ProcessingMode

result = Anonymizer(mode=ProcessingMode.STRICT, strategy="tokenize").process(
    "신청인 홍길동 (880101-1234568) 연락처 010-1234-5678"
)
print(result.text)
# 신청인 <PERSON_1> (<RRN_1>) 연락처 <PHONE_1>

print(result.vault.reveal("<RRN_1>"))  # 880101-1234568
print(result.combined_risk.combined_risk)  # RiskLevel.CRITICAL
```

---

## 설치

```bash
pip install k-pii                  # 코어 (deps 0)
pip install k-pii[file]            # + HWP/HWPX/DOCX/PDF 파서
pip install k-pii[security]        # + Vault AES-256-GCM 암호화
pip install k-pii[ml]              # + OpenAI Privacy Filter (LLM hybrid)
pip install k-pii[presidio]        # + Microsoft Presidio 통합
pip install k-pii[mcp]             # + Claude Desktop MCP 서버
pip install k-pii[all]             # 모든 기능
```

**Python 3.10 이상.** 코어는 Python 표준 라이브러리만 사용.

---

## 정확도

| 평가 도메인 | 데이터 | 문서 수 | F1 |
|---|---|---:|---:|
| **공공 문서 본문 산문** (메인) | 가공 공문서 12 케이스 (`docs/EVALUATION_REPORT.md` §4) | 12 | **0.83** |
| 합성 공문서 코퍼스 | 13 템플릿 다단락 (회귀 감지용) | 60×5 | 0.85 |
| KDPII (참고) | 한국어 일상 대화 PII — Li Fei et al. 2024 | 53,778 | 0.699 |
| KLUE-NER PERSON (참고) | 신문기사 풀네임만 | 5,000 | 0.376 |

KDPII / KLUE 점수는 *대화체·자연어 도메인 참고용* 으로, 사용자 도메인 (공공 문서) 의 실질 성능은 본문 산문 측정 기준 **F1 ≈ 0.83**. 상세: [`docs/EVALUATION_REPORT.md`](docs/EVALUATION_REPORT.md), [`docs/domain_fit_report.md`](docs/domain_fit_report.md).

### 카테고리별 Tier

| Tier | F1 | 카테고리 | 운영 적합도 |
|---|---|---|---|
| **S** | ≥0.95 | EMAIL · VEHICLE · FRN · RRN · IP · PHONE · URL | Production 즉시 |
| **A** | 0.80–0.95 | WEIGHT · HEIGHT · DRIVER_LICENSE · ACCOUNT · AGE | 운영 가능 |
| **B** | 0.50–0.80 | PASSPORT · MAJOR · DT_BIRTH · EDUCATION · POSITION | 사람 검토 권장 |
| **C** | 0.20–0.50 | ADDRESS | 도메인 보강 필요 |
| **D** | <0.20 | PERSON · CARD | 도메인 한계 (해설 참조) |

PERSON / CARD 의 낮은 점수는 *데이터셋 특성* (KDPII 의 1-2자 별명 50%, KDPII 카드의 88% Luhn invalid) 이지 *시스템 결함이 아님*. 공공 문서 도메인에서는 풀네임 PERSON F1 ≈ 0.83.

---

## 32 PII 카테고리

### 결정적 검증 (체크섬·화이트리스트)
| 카테고리 | 검증 | 위험도 |
|---|---|---|
| RRN (주민등록번호) | 13자리 + 날짜 + 한국 체크섬 | CRITICAL |
| FRN (외국인등록번호) | gender 5-8 + 체크섬 | CRITICAL |
| 사업자등록번호 | 국세청 가중합 체크섬 | LOW |
| 법인등록번호 | 법인 체크섬 (RRN 우선) | MEDIUM |
| 운전면허번호 | 지방청 코드 11-28 화이트리스트 | HIGH |
| 여권번호 | prefix (M/S/PP/PD 등) + 8자리 | CRITICAL |
| 신용카드 | BIN 화이트리스트 + Luhn | CRITICAL |
| 필지고유번호 (PNU) | 19자리 + 시·도 코드 | LOW |

### 키워드 anchor (키워드 + 형식 모두 필요)
| 카테고리 | 키워드 |
|---|---|
| 건강보험증 | 건강보험 / 의료보험 / 보험증 |
| 처방번호 | 처방번호 / Rx / 교부번호 |
| 의약품 코드 | 약품코드 / KD코드 + 한국 GS1 |
| 팩스번호 | 팩스 / FAX |
| 계좌번호 | 계좌 / 은행명 (국민·신한·우리·하나·MG·BNK 등 60+) |
| 사번 | 사번 / 공무원번호 / 직원번호 / 임용번호 |
| 민원번호 | 민원 / 청구 / 정보공개 / 행정심판 |
| 사건번호 | 사건유형 (가합/고합/구합/헌가 등) |

### 형식 검증
| 카테고리 | 검증 |
|---|---|
| 전화번호 | 모바일 010-019 / 서울 02 / 지방 031-064 / VoIP 070 / 대표 15xx-18xx / +82 국제 |
| 이메일 | RFC 5322 |
| IP | IPv4 옥텟 + IPv6 RFC 4291 |
| URL | http(s) / ftp |
| 우편번호 | 시·도 첫자리 매핑 |
| 차량번호 | 신형 NN[가-힣]NNNN + 용도 한글 화이트리스트 |
| 공문서번호 | 부처명 + 형식 |

### 사전·휴리스틱
| 카테고리 | 사전 규모 |
|---|---|
| 인명 (PERSON) | 성씨 286 + 직책 인접 + 17 거부 룰 |
| 주소 (ADDRESS) | 광역 17 + 기초 226 + 빈출 동 150 + 국가 70 |
| 학력 (EDUCATION) | 대학 ~330 + 약칭 |
| 전공 (MAJOR) | 학과 ~400 (KEDI 분류) |
| 직책 (POSITION) | titles 250+ (정부·경찰·소방·군·검사·법관·민간) |

### 인적 속성 (준식별자 — 결합 시 식별 위험)
| 카테고리 | 검증 | 위험도 |
|---|---|---|
| 생년월일 | 날짜 + 키워드/풀네임/생 marker | HIGH |
| 나이 | "32세 / 32살 / 환갑 / 12개월 아기 / 30대" | INFO |
| 신장 | "175cm / 1.75m" 50–250 | INFO |
| 체중 | "70kg / 70킬로" 1–300 | INFO |

> **준식별자 (Quasi-Identifier)** 단독으로는 식별 불가지만 다른 정보와 결합 시 재식별 위험. `analytics/combined_risk` 가 자동 평가.

---

## 처리 모드 (사용자가 선택)

| 모드 | 차단 기준 | 용도 |
|---|---|---|
| `PARANOID` | LOW 이상 모두 차단 | 외부 공개·LLM 전송 전 |
| `STRICT` | MEDIUM 이상 차단 | 실무 표준 (기본값) |
| `BALANCED` | HIGH 이상 차단 | 내부 협업 |
| `PERMISSIVE` | CRITICAL 만 차단 | 분석가 작업 |
| `AUDIT` | 차단 없음, 검출만 보고 | 감사·통계 |

## 치환 전략

| 전략 | `880101-1234568` → | 가역 |
|---|---|---|
| `tokenize` | `<RRN_1>` | ✓ Vault 로 복원 |
| `redact` | `[주민등록번호]` | ✗ |
| `asterisk` | `**************` | ✗ |
| `partial` | `880101-1******` | ✗ (실무 양식) |
| `hashed` | `<RRN:abc123>` | ✗ |
| `fpe` | `771202-2345671` | ✗ (형식 유지) |

---

## 부가 기능

| 기능 | 설명 | 설치 |
|---|---|---|
| HWP/HWPX/DOCX/PDF 파서 | 본문·표·머리말·메타데이터 (작성자/수정자) 추출 | `[file]` |
| Vault AES-256-GCM 암호화 | 토큰화된 원본을 암호화 저장 (PBKDF2 480k iter) | `[security]` |
| 감사 로그 (JSONL) | 모든 `reveal()` 호출 기록 | 코어 |
| 배치 처리 | 디렉토리 일괄 + 병렬 워커 | 코어 |
| 검토 큐 | confidence 낮은 후보 → 사람이 OK/오탐 마킹 | 코어 |
| HTML 리포트 | 색상 코딩 + 인터랙티브 시각화 | 코어 |
| 한자/로마자 변형 | `洪吉童` → `홍길동`, `Hong Gildong` → `홍길동` | 코어 |
| OpenAI Privacy Filter | LLM hybrid (약한 케이스만 LLM 위임) | `[ml]` |
| Microsoft Presidio | Presidio 영어 PII 검출 통합 | `[presidio]` |
| Claude Desktop MCP | AI 에이전트가 PII 처리 직접 호출 | `[mcp]` |

---

## 사용 가이드

### CLI

```bash
k-pii input.txt --mode STRICT --strategy tokenize \
       --vault vault.json -o output.txt --report report.html

# 배치 (디렉토리 일괄)
k-pii ./incoming/ --batch --workers 4 --output-dir ./anonymized/

# Vault 암호화 + 감사 로그
KPII_VAULT_PASSWORD=secret k-pii doc.hwp \
    --vault vault.kvault --audit-log audit.jsonl
```

### Python API — 기본

```python
from k_pii import Anonymizer, ProcessingMode

anon = Anonymizer(mode=ProcessingMode.STRICT, strategy="tokenize")
result = anon.process(text)

print(result.text)                    # 가명화된 텍스트
print(result.vault.reveal("<RRN_1>"))  # 원본 복원 (권한 있는 사용자)
print(result.summary["by_label"])     # {"RRN": 1, "PHONE": 1, "PERSON": 1}
```

### 결합 위험도 + k-익명성

```python
# 검출 결과의 결합 위험도 자동 평가
print(result.combined_risk.combined_risk)        # RiskLevel.CRITICAL
print(result.combined_risk.identifiers)          # {"RRN"}
print(result.combined_risk.quasi_identifiers)    # {"PERSON", "ADDRESS", "DT_BIRTH"}

# k-익명성 평가
from k_pii.analytics import k_anonymity
report = k_anonymity(records, quasi_identifiers=["age", "city", "job"], k=5)
print(report.satisfies_k)            # True/False
print(report.generalization_suggestions)  # ["age: 30-39", ...]
```

### CSV/XLSX 표 자동 처리

```python
from k_pii.tabular import anonymize_records
import csv

rows = list(csv.DictReader(open("employees.csv")))
# 헤더 "성명/주민번호/연락처/주소" → 자동으로 PERSON/RRN/PHONE/ADDRESS 매핑
result = anonymize_records(rows, strategy="tokenize")
print(result.rows[0])  # 각 셀이 가명화된 dict
```

### 검토 큐 워크플로우

```python
result = anon.process(text)
for item in result.review_queue:
    print(item.text, item.confidence, item.evidence)
    # 사용자가 OK / 오탐 / 미탐 마킹
    # 반복 오탐 → common_words 자동 추천
```

### 개별 검출기

```python
from k_pii.patterns.rrn import detect

for r in detect("신청인 880101-1234568"):
    print(r.label, r.text, r.confidence, r.legal_basis)
# RRN 880101-1234568 1.0 개인정보보호법 제24조의2
```

---

## 검출 사례

각 검출은 **multi-gate 검증** (체크섬 + 화이트리스트 + 키워드 anchor + 사전) 으로 *임의의 숫자 패턴이 우연히 PII 로 잡히지 않게* 설계됨.

```
✓ 880101-1234568            (RRN — 날짜 유효 + 체크섬)
✓ 880101-1999999            (RRN 후-2020 — 체크섬 실패도 confidence 0.7 emit)
✓ 850315-5345676            (FRN — gender 5)
✓ 120-81-47521              (사업자등록 — 국세청 체크섬)
✓ 191211-0006637            (법인등록 — 한국전력)
✓ 4242-4242-4242-4242       (카드 — Visa BIN + Luhn)
✓ M12345678                 (여권 — prefix M)
✓ 010-2847-3915             (모바일 PHONE, HIGH)
✓ 1588-1234                 (대표번호 PHONE, MEDIUM)
✓ 12가3456                  (차량 — 신형 + 용도 한글)
✓ kim@gov.go.kr             (이메일)

✗ 881301-1000004            (RRN — 13월 무효)
✗ 1234-1234-1234-1234       (카드 — BIN 첫자리 1 거부)
✗ 000-00-00000              (사업자 — placeholder)
✗ A12345678                 (여권 — A prefix 거부)
✗ 020-1234-5678             (PHONE — 020 미할당 지역)
```

PERSON 검출 예시:
```
✓ 성명: 김도윤                       (필드 라벨)
✓ 박지훈 과장님께                    (직책 인접)
✓ 기획재정부 김도윤 장관              (3중 매크로 — 기관+이름+직급)

✗ 김부장이 협조 안 함                (1자 성씨 + 직급 = 호칭, PII 아님)
✗ 박씨가 신고                        (이미 가명화된 표기)
✗ 보건복지부는 검토 후                (부처명 자체)
✗ 서울에서 발표                       (지역명)
```

상세 정책: [`docs/annotation_policy.md`](docs/annotation_policy.md), [`docs/pattern_analysis.md`](docs/pattern_analysis.md).

---

## 예제 모음 (18개, `examples/`)

| # | 시나리오 |
|---:|---|
| 01 | 가장 단순한 가명화 |
| 02 | Vault 로 토큰 복원 |
| 03 | 5 모드 (PARANOID~AUDIT) 차이 |
| 04 | 6 전략 비교 |
| 05 | 결합 위험도 + k-익명성 |
| 06 | HWP/PDF/DOCX 입력 |
| 07 | CSV/XLSX 헤더 자동 매핑 |
| 08 | 디렉토리 일괄 + 병렬 |
| 09 | 검토 큐 워크플로우 |
| 10 | HTML 시각화 보고서 |
| 11 | 감사 로그 |
| 12 | AES-256-GCM Vault 암호화 |
| 13 | LLM 전송 전 안전 필터 |
| 14 | OpenAI Privacy Filter hybrid |
| 15 | Microsoft Presidio 통합 |
| 16 | 모든 PII 카테고리 시연 |
| 17 | 실제 공문서 시나리오 |
| 18 | 종합 데모 (488 unit + 15 시나리오) |

```bash
python examples/01_basic_anonymize.py
python examples/18_user_megademo.py --html demo.html
```

---

## 문서 (`docs/`)

| 문서 | 내용 |
|---|---|
| [`EVALUATION_REPORT.md`](docs/EVALUATION_REPORT.md) | 통합 평가 보고서 (정탐/오탐/미탐 + Tier + 도메인 분석) |
| [`domain_fit_report.md`](docs/domain_fit_report.md) | 도메인 적합도 (KDPII 점수 한계 + 공공 문서 실질 성능) |
| [`kdpii_evaluation_report.md`](docs/kdpii_evaluation_report.md) | KDPII 53,778 문서 평가 결과 |
| [`legal_mapping.md`](docs/legal_mapping.md) | 카테고리별 법조항 매핑 |
| [`annotation_policy.md`](docs/annotation_policy.md) | 검출 정책 (왜 잡고 / 왜 거부) |
| [`risk_levels.md`](docs/risk_levels.md) | 위험도 + 모드별 차단 기준 |
| [`pattern_analysis.md`](docs/pattern_analysis.md) | 패턴별 정탐/오탐 분석 |
| [`coverage.md`](docs/coverage.md) | 카테고리별 검증 매트릭스 |
| [`integration_openai_privacy_filter.md`](docs/integration_openai_privacy_filter.md) | OpenAI 통합 가이드 |
| [`integration_presidio.md`](docs/integration_presidio.md) | Presidio 통합 가이드 |
| [`integration_mcp.md`](docs/integration_mcp.md) | MCP 서버 가이드 |
| [`sample_redaction.md`](docs/sample_redaction.md) · `.html` | 가명화 샘플 (Before/After) |
| [`kdpii_visual_compare.html`](docs/kdpii_visual_compare.html) | KDPII 100 문서 정탐/오탐/미탐 시각 비교 |

---

## 개발

```bash
git clone https://github.com/modak000/k-pii
cd k-pii
python -m venv .venv
source .venv/bin/activate              # Linux/macOS
# .venv\Scripts\activate               # Windows
pip install -e ".[dev]"
pytest                                  # 699 passed
python -m k_pii.eval.benchmark -n 60   # 합성 회귀 감지
python -m k_pii.eval.kdpii kdpii.jsonl # KDPII 평가 (별도 다운로드 필요)
```

---

## 라이선스

Apache License 2.0 — 자유 사용·상업 사용 가능. 한국 공공 부문·민간 기업 모두.

## 인용

본 라이브러리의 KDPII 벤치마크 점수를 인용 시 원논문도 같이:

```bibtex
@article{fei2024kdpii,
  title={KDPII: A New Korean Dialogic Dataset for the Deidentification of
         Personally Identifiable Information},
  author={Fei, Li and Kang, Yejee and Park, Seoyoon and Jang, Yeonji
          and Lee, Jongkyu and Kim, Hansaem},
  journal={IEEE Access}, year={2024}, publisher={IEEE},
  doi={10.1109/ACCESS.2024.3461804}
}
```

## 법적 참고

- 개인정보보호법 (제2조, 제23조 민감정보, 제24조 고유식별정보, 제24조의2 RRN, 제28조의2-5 가명정보, 제29조 안전조치의무)
- 개인정보보호위원회 「가명정보 처리 가이드라인」
- 개인정보보호위원회 「개인정보 비식별 조치 가이드라인」
- 상법 제40조 (법인등록번호)
- 출입국관리법 제31조 (FRN)
- 국민건강보험법 제96조 (건강보험증)
- 금융실명거래 및 비밀보장에 관한 법률 (계좌)
