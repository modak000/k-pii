# k-pii

[![Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-699%20passed-brightgreen.svg)](#)
[![Korean PII](https://img.shields.io/badge/도메인-한국%20공공-red.svg)](#)

한국 공공 부문 문서를 위한 규칙 기반 개인정보(PII) 비식별 라이브러리. **외부 ML 없이** 룰만으로 production-ready.

> **상태:** v1.0.0 release-ready — **한국 공공 PII 솔루션**.
> 31 PII (KDPII 표준 준식별자 포함) + 6 처리 전략 + HWP/PDF/표 입력 + Vault 암호화 + 감사 로그 + 배치 + 검토 큐 + HTML 리포트 + 한자/로마자 + **OpenAI Privacy Filter / Presidio / MCP 옵셔널 연계**.
>
> **정확도** (실데이터):
> - KDPII 53,778 문서 micro **F1 = 0.650** ([Li Fei et al., IEEE Access 2024](https://ieeexplore.ieee.org/document/10681073))
> - KLUE-NER 5,000 신문기사 PERSON only **F1 = 0.322**
> - 합성 코퍼스 F1 = 1.000 (회귀 감지 sanity check 용도 — *실제 정확도 아님*)
>
> **코어 deps 0개**. 입력·보안·ML·Presidio·MCP 기능은 모두 extras 로 분리.

## 설치

```bash
pip install k-pii                       # 코어만 — deps 0
pip install k-pii[file]                 # + HWP/PDF 입력
pip install k-pii[security]             # + Vault AES-GCM 암호화
pip install k-pii[ml]                   # + OpenAI Privacy Filter
pip install k-pii[presidio]             # + Microsoft Presidio plugin
pip install k-pii[mcp]                  # + Claude Desktop MCP 서버
pip install k-pii[all]                  # 모든 옵션
```
>
> **AI 에이전트가 처음 이 레포에 합류한다면:** [CLAUDE.md](CLAUDE.md) 먼저 읽어주세요. 미션·설계 원칙·결정 기록·다음에 할 일이 모두 들어있습니다.

## 개요

`k-pii`는 한국 공무원/정부기관이 작성·처리하는 문서(공문서, 민원 응대, 인사 문서 등)에서
개인정보를 검출하고 가역적으로 가명화하는 Python 라이브러리입니다. **외부 ML 라이브러리 없이**
정규식 + 사전 + 컨텍스트 규칙만으로 동작하도록 설계되었습니다.

### 설계 원칙

1. **모델 없음, 의존성 없음** — 코어는 Python 표준 라이브러리만 사용. CPU에서 동작.
2. **한국 공공 부문 특화** — 공무원 직책, 부처명, 공문서 양식, 한국 개인정보보호법에 맞춤.
3. **위험도 시스템** — `CRITICAL / HIGH / MEDIUM / LOW / INFO` 분류 + 사용자가 임계값 선택.
4. **가역 가명화** — vault 분리 보관으로 권한 있는 사용자만 복원 가능.
5. **법적 근거 매핑** — 각 탐지 결과에 개인정보보호법 조항 부착(감사 추적용).
6. **컨텍스트 누적 식별** — 문서 내에서 강한 단서로 확정된 이름을 약한 단서에서도 인식.

## 용어 — 이게 무슨 뜻?

> 본 라이브러리를 처음 보는 사람을 위한 핵심 용어 5가지.

**체크섬 (Checksum)** — 번호 자체에 *수학적 검증 숫자* 가 들어있는 것.
예: 주민등록번호 마지막 자리는 앞 12자리로부터 계산되는 검증 숫자. 임의의
13자리 숫자가 우연히 통과할 확률은 1/11 (약 9%). 카드 번호의 Luhn, 사업자
번호의 국세청 알고리즘, RRN 알고리즘 등이 있음. **체크섬 실패 = 그냥 숫자열,
실제 PII 아님** 으로 거의 확정 가능.

**후-2020 RRN 무작위화** — 행정안전부가 2020-10-05부터 RRN 의 7~13번째 자리
를 무작위로 발급. 따라서 신규 RRN 은 기존 표준 체크섬을 통과하지 못할 수 있음.
k-pii 정책: 패턴 + 날짜 유효 + 체크섬 통과 = confidence 1.0, 체크섬 실패 =
confidence 0.7 (둘 다 CRITICAL). FN(놓침) 이 FP(오탐) 보다 훨씬 위험한 PII
이므로 보수적으로 emit. PARANOID/STRICT 모드는 0.7도 차단, PERMISSIVE 는 1.0만.

**Placeholder (자리 채움 번호)** — 양식·예시·테스트용으로 자리만 채워 넣은
*명백히 가짜인* 번호. 예: 신청서 양식에 "000-00-00000" 으로 사업자번호 칸을
비워두거나, 안내문에 "M00000000" 으로 여권 번호 자리 표시. 이런 패턴은 *체크섬
계산상* 수학적으로 valid 일 수 있지만 (예: `0000000000` 의 체크섬은 0), 실제
사용된 적 없으므로 PII 가 아님 → 별도 거부.

| 카테고리 | 거부하는 자리 채움 패턴 | 이유 |
|---|---|---|
| BUSINESS_REG | `000-00-00000` (전체 0) | 양식 예시 |
| PASSPORT | `M00000000` (모두 0 일련번호) | 미발급 |
| VEHICLE | `12가0000` (뒷자리 0000) | 시범 번호 |
| PNU | 본번 `0000` | 실제 토지는 본번 1 이상 |
| COURT_CASE | 일련번호 `0` | 사건 일련번호 1부터 |
| CARD | BIN 첫자리 `0` 또는 `1` | 카드 BIN 표준 (2-6, 9) |

이게 없으면 "사업자등록번호 칸: 000-00-00000" 같은 빈 양식이 PII 로 잘못
잡힘.

**키워드 anchor — 3중 검증, "키워드만 있으면 다 잡는" 게 아님**

| 단계 | 검증 | 예시 (건강보험증) |
|---|---|---|
| 1 | **형식 정확 일치** | 정확히 11자리 숫자, 앞뒤에 다른 숫자 X |
| 2 | **키워드 존재** | "건강보험/의료보험/보험증" 정규식 매칭 |
| 3 | **윈도우 거리** | 키워드와 숫자 사이 25자 이내 |
| 4 | **순서** | 키워드가 숫자 *앞에* 와야 함 (뒤에 오면 X) |

예시 거부 사례:
- "그 건강보험 회사 좋더라" — 숫자 자체 없음 → emit X
- "건강보험은 중요합니다. ... (60자 후) ... 12345678901" — 윈도우 초과
- "12345678901 건강보험증" — 순서 거꾸로
- "건강보험증 010-1234-5678" — 휴대전화 (010 prefix) 가 11자리 정규식
  통과해도 별도 PHONE 검출기가 우선 claim

카테고리별 anchor 정책:
| 카테고리 | 키워드 | 윈도우 | 위치 |
|---|---|---|---|
| MEDICAL_INSURANCE | 건강보험/의료보험/보험증 | 25자 | 앞 |
| ACCOUNT | 계좌/은행명 (국민·신한·우리·하나 등) | 직전 | 앞 또는 뒤 |
| FAX | 팩스/FAX | 12자 | 앞 |
| EMPLOYEE_ID | 사번/공무원번호/직원번호/임용번호 | 직전 (tight) | 앞 |
| PETITION_ID | 민원/청구/정보공개/행정심판 | 직전 | 앞 |
| POSITION | 직급/직책/직위/보직 또는 "...님" | 12자 | 앞 |
| DT_BIRTH | 생년월일/생일/출생/태어남 | 25자 | 앞 또는 뒤 |

**ProcessingMode (사용자가 고르는 단계)** — *얼마나 엄격하게 차단할지* 선택.
| 모드 | 차단 기준 | 용도 |
|---|---|---|
| `PARANOID` | LOW 이상 모두 차단 | 외부 공개·LLM 전송 전 |
| `STRICT` | MEDIUM 이상 차단 | 실무 표준 |
| `BALANCED` | HIGH 이상 차단 | 내부 협업 |
| `PERMISSIVE` | CRITICAL 만 차단 | 분석가 작업 |
| `AUDIT` | 차단 없음, 검출만 보고 | 감사·통계 |

**전략 (Strategy)** — 차단된 값을 *어떻게 바꿀지* 선택.
| 전략 | `880101-1234568` → | 가역 |
|---|---|---|
| `tokenize` | `<RRN_1>` | ✓ Vault 로 복원 |
| `redact` | `[주민등록번호]` | ✗ |
| `asterisk` | `**************` | ✗ |
| `partial` | `880101-1******` | ✗ (실무 양식) |
| `hashed` | `<RRN:abc123>` | ✗ |
| `fpe` | `771202-2345671` | ✗ (형식 유지) |

**Phase (개발 단계 — 사용자와 무관)** — 라이브러리 개발 history. v1 출시 후
모든 phase 가 완료된 상태라 일반 사용자는 신경 쓸 필요 없음. [CHANGELOG.md](CHANGELOG.md)
에서 발전 과정 확인 가능.

## 지원 PII 카테고리 (31종)

### 결정적 (체크섬·화이트리스트 검증)
| 카테고리 | 검증 방식 | 위험도 |
|---|---|---|
| 주민등록번호 (RRN) | 날짜 + 한국 RRN 체크섬 | CRITICAL |
| 외국인등록번호 (FRN) | 날짜 + gender 5-8 + 체크섬 | CRITICAL |
| 사업자등록번호 | 국세청 가중합 체크섬 (10자리) | LOW |
| 법인등록번호 | 법인 체크섬 (13자리, RRN 우선) | MEDIUM |
| 운전면허번호 | 지방청 코드 11-28 화이트리스트 | HIGH |
| 여권번호 | prefix 화이트리스트 + 8자리 | CRITICAL |
| 신용카드 | BIN 화이트리스트 + Luhn | CRITICAL |
| 필지고유번호 (PNU) | 시·도 코드 + 본번 placeholder 거부 | LOW |

### 키워드 anchor (키워드 + 형식 모두 필요)
| 카테고리 | 키워드 | 위험도 |
|---|---|---|
| 건강보험증번호 | "건강보험/의료보험/보험증" (25자 윈도우) | HIGH |
| 처방번호 | "처방번호/처방전/Rx/교부번호" | HIGH |
| 의약품 코드 (EDI_DRUG) | "약품코드/주성분코드/KD코드" + 한국 국가코드 | LOW |
| 팩스번호 | "팩스/FAX/fax/Fax" (12자 윈도우) | LOW |
| 계좌번호 | "계좌" | HIGH |
| 사번 (EMPLOYEE_ID) | "사번/공무원번호/직원번호/임용번호" + tight anchor | MEDIUM |
| 민원번호 (PETITION_ID) | "민원/청구/정보공개/행정심판" | LOW |
| 사건번호 (COURT_CASE) | 사건유형 (가합/고합/구합/헌가 등 한글) | MEDIUM |

### 형식 (prefix/사전 매핑)
| 카테고리 | 검증 | 위험도 |
|---|---|---|
| 전화번호 | 통신사·지역번호 prefix (010-019 모바일 / 02 / 031-064 지방 / 070 VoIP / `+82`,`0082` 국제) | HIGH (모바일) / MEDIUM (유선) |
| 이메일 | RFC 5322 실용 부분집합 | MEDIUM |
| IP 주소 | IPv4 옥텟 0-255 / IPv6 RFC 4291 | MEDIUM |
| URL | http(s)/ftp 표준 형식 | INFO |
| 우편번호 | 시·도 첫자리 매핑 (5자리 신/6자리 레거시) | LOW |
| 차량번호 | 신형 NN(N)[가-힣]NNNN + 용도 한글 화이트리스트 | MEDIUM |
| 공문서번호 (DOC_ID) | 부처명 + 형식 | LOW |

### 사전·휴리스틱
| 카테고리 | 검증 | 위험도 |
|---|---|---|
| 인명 (PERSON) | 성씨 286 + 직책 인접 + 호칭 거부 + 행정구역 거부 + 3중 매크로 (기관+이름+직급) | HIGH |
| 주소 (ADDRESS) | 도로명/지번 + (광역+시·군·구) 조합 검증 | MEDIUM |
| 학력 (EDUCATION) | 대학교/전문대 사전 ~330개 + 약칭 매핑 | MEDIUM |
| 전공 (MAJOR) | KEDI 학과 분류 ~250개 + 접미사 정규화 (학과/학부/전공/학) | LOW |
| 직책 (POSITION) | titles 사전 200+ (정부·경찰·소방·군·외무·검사·법관) + 키워드 anchor | LOW |

### 인적 속성 (KDPII 표준 준식별자 — 결합 시 식별 위험)
| 카테고리 | 검증 | 위험도 |
|---|---|---|
| 생년월일 (DT_BIRTH) | 날짜 유효성 + 키워드 anchor ("생년월일/생일/출생/년생") | HIGH |
| 나이 (AGE) | "32세/32살" 0-150 범위 | INFO |
| 신장 (HEIGHT) | "175cm/175센티/1.75m" 50-250cm | INFO |
| 체중 (WEIGHT) | "70kg/70킬로" 1-300kg | INFO |

> **준식별자 (Quasi-Identifier)** — 단독으로는 식별 불가지만 다른 정보와
> 결합 시 재식별 위험. k-pii 의 `analytics/combined_risk.py` + `k_anonymity`
> 가 quasi-identifier 조합 자동 평가.
> 분류 출처: 「개인정보 비식별 조치 가이드라인」 + KDPII 분류 (Li Fei et al.,
> IEEE Access 2024).

> **사전 (Dictionaries)** — 외부 ML 없이 한국 도메인 fit:
> - 성씨 286개 (통계청 「인구주택총조사」)
> - 부처 19부 6처 18청 6위원회 (정부조직법 2026 개편 반영) + 한글/영문 약칭
> - 직책 — 일반직 1-9급 + 경찰 11계급 + 소방 11계급 + 군 19계급 + 검사·법관·외무
> - 행정구역 — 17 광역 + 226 기초자치단체 (75 자치시 + 82 자치군 + 69 자치구)
> - 필드 라벨 (성명/신청인/피의자/수사관 등)

## 기능 한눈에

**처리 모드 × 전략 매트릭스** — `Anonymizer(mode=PARANOID, strategy="partial")`
처럼 조합. 5 모드 × 6 전략 = 30 조합.

**입력 호환성** — `.hwp` / `.hwpx` / `.docx` / `.xlsx` / `.csv` / `.pdf` / `.txt`
자동 디스패처. CSV/XLSX 는 헤더 자동 매핑 (성명→PERSON, 주민번호→RRN 등 80+ 변형).

**보안** (개인정보보호법 제29조 안전조치의무)
- Vault AES-256-GCM 암호화 + PBKDF2 (480k iter) — `[security]` extras
- 모든 `vault.reveal()` / `store()` 호출 감사 로그 (JSONL)

**배치·검토 워크플로우**
- 디렉토리·glob 일괄: `k-pii ./docs/ --batch --workers 4`
- REVIEW 큐 — 사람이 OK/FP/FN 마킹 → FP 누적 시 `common_words` 자동 추천
- 단일 파일 HTML 리포트 (색상 코딩 + 인터랙티브 마킹)

**결합 위험도 + k-익명성** — 「비식별 조치 가이드라인」 직접 대응
- `analytics/combined_risk.py` — 식별자/준식별자/민감속성 분류 + 조합 자동 평가
- `analytics/k_anonymity.py` — k-익명성 평가 (threshold 기본 5) + 일반화 제안

**표기 변형 매칭**
- 한자 → 한글 (`hanja_to_hangul("洪吉童")` → `"홍길동"`)
- Revised Romanization (`romanize_name("홍길동")` → `"Hong Gildong"`)

**외부 통합** (모두 옵셔널, 코어와 분리)
- OpenAI Privacy Filter — `[ml]` extras
- Microsoft Presidio plugin — `[presidio]` extras
- MCP 서버 (Claude Desktop) — `[mcp]` extras

자세한 가이드:
- [`docs/integration_openai_privacy_filter.md`](docs/integration_openai_privacy_filter.md)
- [`docs/integration_presidio.md`](docs/integration_presidio.md)
- [`docs/integration_mcp.md`](docs/integration_mcp.md)

**평가**

| 벤치마크 | 데이터 | 문서 수 | micro F1 | 용도 |
|---|---|---:|---:|---|
| [KDPII](https://ieeexplore.ieee.org/document/10681073) (메인) | 한국어 대화체 PII | 53,778 | **0.650** | 실제 정확도 |
| [KLUE-NER](https://github.com/KLUE-benchmark/KLUE) | 신문기사 PS (인명) | 5,000 | 0.322 | 자연어 PERSON 어림짐작 |
| 합성 코퍼스 | 6 템플릿 공문서 | 60×5 | 1.000 | **회귀 감지 sanity check** |

⚠ **합성 F1=1.0 은 실제 정확도가 아니다.** 좁은 템플릿 (성명: / 주소: 라벨 anchor)
에 검출기가 과적합되어 가능한 상한. CI/CD 통과 기준 (≥0.95) 으로만 활용.

### 카테고리별 Tier (KDPII 기준)

| Tier | F1 | 카테고리 | 운영 적합도 |
|---|---|---|---|
| **S** | ≥0.95 | EMAIL (0.999), VEHICLE, FRN, RRN, IP, PHONE, URL | Production 즉시 가능 |
| **A** | 0.80-0.95 | WEIGHT (0.916), HEIGHT, DRIVER_LICENSE, ACCOUNT, AGE | 운영 가능 |
| **B** | 0.50-0.80 | PASSPORT, MAJOR (0.705), DT_BIRTH, EDUCATION, POSITION | 사람 검토 권장 |
| **C** | 0.20-0.50 | ADDRESS (0.403) | recall 보강 필요 |
| **D** | <0.20 | PERSON (0.170), CARD (0.130) | 본질적 한계 — 아래 설명 |

**PERSON F1 0.170 — 본질적 어려움.** 한국어 단성 성씨 (김/이/박) 가 매우 흔한 일반어
prefix 라서 (민원/회신/시정 등), 대화체에서 anchor 없이 단독 등장하는 이름을 잡으면
FP 폭증 trade-off. STRICT 모드로 운영 시 BLOCK 비율 충분.

**CARD F1 0.130 — 정책상 정상.** KDPII 카드 gold 의 88.3% 가 Luhn 체크섬 invalid
(저자 의도적 fake). k-pii Decision D-006 (Luhn 통과만 emit) 정책 유지 — 실제
production 에서는 더 정확.

상세 보고서: [`docs/real_data_benchmark.md`](docs/real_data_benchmark.md) ·
[`docs/kdpii_session_report.md`](docs/kdpii_session_report.md)

재현:
```bash
python -m k_pii.eval.kdpii kdpii.jsonl       # 메인 벤치마크
python -m k_pii.eval.klue_benchmark klue.tsv # 자연어 PERSON
python -m k_pii.eval.benchmark -n 60 --seed 0 # 회귀 감지
```

```python
from k_pii import Anonymizer, ProcessingMode, k_anonymity

result = Anonymizer(mode=ProcessingMode.STRICT).process(text)
print(result.combined_risk.combined_risk)       # → RiskLevel.CRITICAL
print(result.combined_risk.rationale)            # → ["식별자 RRN 등장 → 즉시 식별 가능"]
```

## 검출 샘플 — 무엇이 잡히고 무엇이 안 잡히는가

각 카테고리는 **단순 형식 매칭이 아니라** 체크섬·화이트리스트·키워드 anchor·사전
검증 등 multi-gate 검증을 거칩니다. 임의의 숫자 패턴이 우연히 PII 로 잡히지
않도록 설계됨. ✓ 는 검출, ✗ 는 거부 (이유 표시).

### 식별번호 (체크섬 검증)

**RRN (주민등록번호)** — 13자리 + 날짜 유효성 + 체크섬
```
✓ 880101-1234568                  (정상)
✓ 8801011234568                   (하이픈 없음)
✓ 880101 1234568                  (공백)
✓ 880101-1999999                  (후-2020 무작위화 — 체크섬 실패해도 PII)
✗ 881301-1000004                  (13월 = 무효 날짜)
✗ 880132-1000003                  (32일 = 무효)
```

**FRN (외국인등록번호)** — gender 자리 5/6/7/8 (RRN 과 자동 분리)
```
✓ 850315-5345676
✗ 850315-1234562                  (gender=1 → RRN 으로 분류)
```

**BUSINESS_REG (사업자등록번호)** — 10자리 + 국세청 가중합 체크섬
```
✓ 120-81-47521                    (체크섬 통과)
✓ 1208147521                      (하이픈 없음)
✗ 120-81-47520                    (체크섬 실패)
✗ 000-00-00000                    (placeholder)
```

**CORP_REG (법인등록번호)** — 13자리 + 법인 체크섬 (RRN 과 충돌 시 RRN 우선)
```
✓ 191211-0006637                  (한전 — 법인 체크섬 통과)
```

**CARD (신용카드)** — BIN 화이트리스트 (2/3/4/5/6/9) + Luhn
```
✓ 4242-4242-4242-4242             (Visa 테스트, Luhn OK)
✓ 5555 5555 5555 4444             (Mastercard 테스트)
✗ 1234-1234-1234-1234             (BIN 첫자리 1 거부)
✗ 0000-0000-0000-0000             (BIN 거부)
✗ 8888-8888-8888-8888             (BIN 거부)
✗ 5555-5555-5555-5555             (BIN OK, Luhn 실패)
```

**DRIVER_LICENSE (운전면허)** — 지방청 코드 11-28 화이트리스트
```
✓ 11-90-123456-78                 (서울청 11)
✓ 운전면허 119012345678            (키워드 + 하이픈 없음)
✗ 99-90-123456-78                 (지방청 99 = 미존재)
```

**PASSPORT (여권)** — prefix 화이트리스트 (M/S/O/D/R/T/PP/PD/PO/PS/PT)
```
✓ M12345678                       (일반)
✓ PP12345678                      (2024.12 신형)
✗ A12345678                       (A = 한국 여권 prefix 아님)
✗ M1234567                        (8자리 = 자릿수 부족)
✗ m12345678                       (소문자 = 한국 여권은 대문자)
```

### 통신 정보

**PHONE** — 통신사·지역번호 prefix 화이트리스트
```
✓ 010-2847-3915                   (모바일, HIGH)
✓ 010.8624.1759                   (점 구분)
✓ 02-3479-6128                    (서울, MEDIUM)
✓ +82-10-9617-8253                (국제)
✓ 1588-7264                       (전국 대표)
✗ 020-1234-5678                   (020 = 미할당 지역번호)
```

**FAX** — PHONE 형식 + "팩스/FAX/fax/Fax" 키워드 anchor
```
✓ 팩스: 02-123-4567
✓ FAX 031-555-6677
✗ 02-123-4567                     (단독 — 키워드 없으면 PHONE)
✗ 전송 02-123-4567                (전송 = FP 위험으로 키워드 제외됨)
✗ F. 02-123-4567                  (F. = FP 위험으로 키워드 제외됨)
```

**EMAIL** — RFC 5322 실용 부분집합
```
✓ user@example.com
✓ user.name+filter@gmail.com
✓ kim@gov.go.kr
✗ user@한국.kr                    (한글 도메인 미지원)
```

### 위치·주소

**ADDRESS** — (광역 + 시·군·구) **조합 검증** (사전 매핑)
```
✓ 서울특별시 종로구 세종대로 209
✓ 경기도 성남시 분당구 정자로 1
✓ 부산광역시 해운대구 우동로 123
✓ 주소: 서울 강남구 테헤란로 152   (약칭 광역)
✗ 경기도 강남구 어딘가             (강남구는 서울, 조합 실패)
✗ 바티스타밤이라도 나왔으면 1      (가짜 광역 — 17 광역 사전 거부)
```

**POSTAL_CODE** — 시·도 첫자리 매핑
```
✓ 우편번호 03187                  (서울 01-08)
✓ 우편번호 13520                  (경기 10-18)
✗ 우편번호 09999                  (09 = 시·도 미할당)
✗ 우편번호 99000                  (99 = 미할당)
```

**IP** — IPv4 옥텟 0-255 검증, IPv6 RFC 4291
```
✓ 192.168.1.100                   (IPv4 사설)
✓ 2001:db8::1                     (IPv6 단축)
✓ ::1                             (IPv6 loopback)
✗ 256.256.256.256                 (옥텟 범위 초과)
✗ ::                              (한글 강조 충돌 — 단독 거부)
```

**VEHICLE (차량번호)** — 용도 한글 화이트리스트 + 한국어 단위 거부
```
✓ 12가3456                        (자가용)
✓ 87바1234                        (영업용 — 택배)
✓ 99하1234                        (렌터카)
✗ 12장 3456                       (장 = 차량 용도 코드 아님)
✗ 291조 9000                      (한국어 단위 — 차량 아님)
✗ 120원 3000                      (원 = 화폐 단위)
```

**URL** — 표준 URL 형식 (위험도 INFO)
```
✓ https://example.com/page
✓ ftp://example.com/file.zip
```

### 인적 정보

**PERSON** — 성씨 사전 (286개) + 직책 인접 + 호칭 거부 + 행정구역 거부
```
✓ 성명: 김도윤                    (필드 라벨)
✓ 박지훈 과장님께                  (직책 인접)
✓ 부장 박지훈 면담                 (직급 + 풀네임)
✓ 기획재정부 김도윤 장관           (3중 매크로 — 기관+이름+직급)
✓ 정유진 검사 수사                 (직책 인접)
✓ 신청인: 박지훈                  (필드 라벨)
✗ 김부장이 협조 안 함             (성씨 1자 + 직급 = 호칭, PII 아님)
✗ 박과장도 마찬가지               (호칭)
✗ 이차장님이 회의                 (호칭)
✗ 보건복지부는 검토 후             (부처명 자체)
✗ 검토 결과 모두 적정             (일반 단어)
✗ 박씨가 신고                     (이미 가명화된 표기)
✗ 서울에서 발표                   (지역명)
```

**ACCOUNT (계좌번호)** — "계좌" 키워드 anchor
```
✓ 계좌: 1234567890
✓ 계좌 110-1234-567890
✗ 1234567890                      (키워드 없음)
```

### 행정·법조 도메인

**DOC_ID (공문서 번호)** — 부처명 + 형식
```
✓ 문서번호: 기재부-인사-2024-00123
✓ 행안부-총무과-2025-00567
✓ 보훈부-인사-2024-99999          (2023 신설 부처)
```

**PETITION_ID (민원/청구 번호)** — 키워드 + 형식
```
✓ 민원번호 2024-민원-00123
✓ 청구번호 2025-정보공개-00567
✓ 행정심판-2024-00890
```

**EMPLOYEE_ID (사번)** — tight anchor (키워드가 숫자 직전에 와야 함)
```
✓ 사번: 20240001                  (콜론 + 공백)
✓ 사번:20240001                   (콜론만)
✓ 사번 20240001                   (공백만)
✓ 사번20240001                    (붙임)
✓ 공무원번호 123456
✓ 직원번호: 456789
✓ 임용번호 78901234
✗ 교번 789012                     (수학 "교차" 의미 충돌로 키워드 제외)
✗ 이것은 사번이 다르다 ... 20240001  (anchor 안 됨 — 일반 문장)
```

**COURT_CASE (법원 사건번호)** — 사건유형 한글 화이트리스트
```
✓ 2024가합12345                   (민사 합의)
✓ 2023고합567                     (형사 합의)
✓ 2024차10001                     (지급명령)
✓ 2024헌가1                       (헌법 본안)
```

**PNU (필지고유번호)** — 19자리 + 시·도 코드 화이트리스트
```
✓ 1111011600100010000             (서울 종로 11)
✓ 4129010200200500015             (경기 안양 — 산번지)
✗ 1111011600000000000             (본번 0000 = placeholder)
```

### 인적 속성 (KDPII 표준 준식별자)

**DT_BIRTH (생년월일)** — 날짜 유효성 + 키워드 anchor
```
✓ 생년월일: 1988년 1월 1일
✓ 생일은 88.01.01
✓ 88년생
✓ DOB: 1988-01-01
✗ 회의는 2024년 4월 15일       (키워드 없음 — 단순 날짜)
✗ 생일 1988년 13월 1일         (13월 = 무효)
✗ 생일 1987년 2월 29일         (1987 비윤년)
```

**EDUCATION (학력)** — 대학교 사전 + 약칭
```
✓ 서울대학교 졸업
✓ 카이스트 출신                (약칭 → 한국과학기술원으로 정규화)
✓ POSTECH 학부
✗ 뽀로로대학교 다님              (사전 화이트리스트 외)
```

**MAJOR (전공)** — KEDI 학과 분류 + 접미사 정규화
```
✓ 컴퓨터공학과               (→ canonical: 컴퓨터공학)
✓ 경영학부
✓ 법학 전공
✓ 의예과
✗ 뽀로로공학과                 (사전 외)
```

**POSITION (직책)** — titles 사전 + 키워드 anchor
```
✓ 직급: 사무관
✓ 직책 부장
✗ 사무관이 결재               (키워드 없음 — PERSON 컨텍스트로만 사용)
```

**AGE / HEIGHT / WEIGHT** — 범위 검증 (위험도 INFO)
```
✓ 32세 / 32살                            (0-150)
✓ 175cm / 175센티 / 1.75m                 (50-250cm)
✓ 70kg / 70킬로 / 70킬로그램               (1-300kg)
✗ 200세 / 500kg                          (범위 초과)
```

### 의료 정보

**MEDICAL_INSURANCE (건강보험증)** — 11자리 + 키워드 25자 윈도우
```
✓ 건강보험증번호: 12345678901
✓ 의료보험 11122334455
✗ 12345678901                     (키워드 없음 — 휴대전화와 충돌 방지)
```

**PRESCRIPTION_ID (처방번호)** — 12자리 (YYYYMMDD+seq) + 키워드 + 날짜 유효성
```
✓ 처방번호 202412010001
✓ Rx 202401150042
✓ 요양기관기호: 12345678          (8자리 HIRA)
✗ 202412010001                    (키워드 없음 — 다른 12자리와 충돌)
```

**EDI_DRUG (의약품 코드)** — 키워드 + 한국 국가코드 (880/881)
```
✓ 약품코드 123456789              (9자리 EDI)
✓ KD코드: 8801234567890           (13자리 한국 GTIN)
✗ KD코드: 1234567890123           (한국 국가코드 아님)
✗ 123456789                       (키워드 없음)
```

> **참고:** KCD (한국표준질병사인분류 — `K29.0`, `E11.9` 등 진단코드) 는
> 의료 문서 양식이 표준화되지 않아 정확도 보장이 어려워 검출기에서 제외됨.
> 실제 의료 문서 샘플 기반 fine-tune 가능 시 재추가 검토.

### 위험도 분기 예시

같은 카테고리라도 sub-type 에 따라 위험도가 갈립니다:

| 입력 | 라벨 | 위험도 | 사유 |
|---|---|---|---|
| `010-2847-3915` | PHONE | **HIGH** | 모바일 = 개인 직통 |
| `02-3479-6128` | PHONE | MEDIUM | 유선 = 사업장·대표번호 포함 가능 |
| `070-7864-3920` | PHONE | MEDIUM | VoIP |
| `1588-7264` | PHONE | MEDIUM | 전국 대표 |
| `https://example.com` | URL | INFO | 단독 URL = PII 아님 (path 안의 PII 만 위험) |

전체 위험도·법조항 매핑: [`docs/legal_mapping.md`](docs/legal_mapping.md)
검출 정책 (왜 잡고 왜 안 잡는가): [`docs/annotation_policy.md`](docs/annotation_policy.md)

## 예제 모음 (`examples/`)

레포에 18개 실행 가능한 예제가 있습니다. 시나리오별로 그대로 실행:

| # | 파일 | 시나리오 |
|---|---|---|
| 01 | `01_basic_anonymize.py` | 가장 단순한 가명화 — 텍스트 → 토큰 |
| 02 | `02_vault_reveal.py` | Vault 로 토큰 복원 |
| 03 | `03_processing_modes.py` | 5 모드 (PARANOID~AUDIT) 차이 |
| 04 | `04_strategies_compared.py` | 6 전략 비교 (tokenize/redact/partial/...) |
| 05 | `05_combined_risk_k_anonymity.py` | 결합 위험도 + k-익명성 평가 |
| 06 | `06_file_inputs.py` | HWP/PDF/DOCX 입력 |
| 07 | `07_tabular_csv.py` | CSV/XLSX 헤더 자동 매핑 |
| 08 | `08_batch_processing.py` | 디렉토리 일괄 처리 + 병렬 |
| 09 | `09_review_workflow.py` | REVIEW 큐 + 피드백 누적 |
| 10 | `10_html_report.py` | HTML 시각화 보고서 |
| 11 | `11_audit_log.py` | Vault 접근 감사 로그 |
| 12 | `12_encrypted_vault.py` | AES-256-GCM Vault 암호화 |
| 13 | `13_llm_safe_filter.py` | LLM 전송 전 안전 필터 |
| 14 | `14_hybrid_with_privacy_filter.py` | OpenAI Privacy Filter 하이브리드 |
| 15 | `15_presidio_integration.py` | Microsoft Presidio 통합 |
| 16 | `16_all_pii_showcase.py` | 모든 PII 카테고리 한눈에 |
| 17 | `17_realistic_document.py` | 실제 공문서 시나리오 |
| 18 | `18_user_megademo.py` | 488 unit + 15 시나리오 종합 데모 |

```bash
python examples/01_basic_anonymize.py
python examples/18_user_megademo.py --html demo.html
```

## 추가 문서 (`docs/`)

| 문서 | 내용 |
|---|---|
| [`real_data_benchmark.md`](docs/real_data_benchmark.md) | **정식 통합 벤치마크 보고서** (KDPII / KLUE-NER / 합성) |
| [`kdpii_session_report.md`](docs/kdpii_session_report.md) | KDPII 평가 세션 + Decision Log |
| [`sample_redaction.md`](docs/sample_redaction.md) | 종로구 민원 회신문 가명화 샘플 |
| [`synthetic_corpus_samples.md`](docs/synthetic_corpus_samples.md) | 합성 평가 코퍼스 6 템플릿 샘플 |
| [`legal_mapping.md`](docs/legal_mapping.md) | 카테고리별 법조항 매핑 |
| [`annotation_policy.md`](docs/annotation_policy.md) | 검출 정책 (왜 잡고/왜 거부) |
| [`risk_levels.md`](docs/risk_levels.md) | 위험도 정책 + 모드별 차단 기준 |
| [`pattern_analysis.md`](docs/pattern_analysis.md) | 패턴별 FP/FN 분석 |
| [`coverage.md`](docs/coverage.md) | 카테고리별 검증 cover 매트릭스 |
| [`integration_openai_privacy_filter.md`](docs/integration_openai_privacy_filter.md) | OpenAI Privacy Filter 통합 |
| [`integration_presidio.md`](docs/integration_presidio.md) | Microsoft Presidio 통합 |
| [`integration_mcp.md`](docs/integration_mcp.md) | Claude Desktop MCP 서버 |

HTML 보고서:
- [`sample_redaction.html`](docs/sample_redaction.html) — 실제 가명화 결과
- [`synthetic_sample.html`](docs/synthetic_sample.html) — 합성 코퍼스 샘플
- [`user_megademo.html`](docs/user_megademo.html) — 15 시나리오 종합

## 빠른 시작

### 통합 API

```python
from k_pii import Anonymizer, ProcessingMode

anon = Anonymizer(mode=ProcessingMode.STRICT, strategy="tokenize")
result = anon.process("신청인 홍길동(880101-1234568) 연락처 010-1234-5678")

print(result.text)
# 신청인 <PERSON_1>(<RRN_1>) 연락처 <PHONE_1>

print(result.vault.reveal("<RRN_1>"))      # → 880101-1234568
print(result.summary["by_label"])          # → {'RRN': 1, 'PHONE': 1, 'PERSON': 1}
```

### CLI

```bash
k-pii input.txt --mode STRICT --strategy tokenize --vault vault.json -o out.txt --report cert.txt
```

### 개별 검출기

```python
from k_pii.patterns.rrn import detect

for result in detect("신청인 880101-1234568"):
    print(result.label, result.text, result.confidence, result.legal_basis)
# RRN 880101-1234568 1.0 개인정보보호법 제24조의2
```

### CSV/XLSX 표 자동 처리 (`examples/07_tabular_csv.py`)

```python
from k_pii.tabular import anonymize_records
import csv

with open("employees.csv") as f:
    rows = list(csv.DictReader(f))
# 헤더 "성명/주민번호/연락처" → 자동으로 PERSON/RRN/PHONE 라벨 매핑
result = anonymize_records(rows, strategy="tokenize")
print(result.rows[0])  # 각 셀이 가명화된 dict
```

80+ 헤더 변형 인식: 성명/이름/Name → PERSON, 주민/주민번호/RRN → RRN, etc.

### 결합 위험도 + k-익명성 (`examples/05_combined_risk_k_anonymity.py`)

```python
from k_pii.analytics import k_anonymity

records = [
    {"age": 32, "city": "서울", "job": "교사"},
    {"age": 33, "city": "서울", "job": "교사"},
    # ...
]
report = k_anonymity(records, quasi_identifiers=["age", "city", "job"], k=5)
print(report.satisfies_k)        # → True/False
print(report.violations)         # → 위반 그룹 list
print(report.generalization_suggestions)  # → ["age: 30-39", ...]
```

### 검토 큐 워크플로우 (`examples/09_review_workflow.py`)

```python
from k_pii import Anonymizer, ProcessingMode

# REVIEW 모드 — confidence 임계 미달 detection 을 큐로 보냄
anon = Anonymizer(mode=ProcessingMode.STRICT)
result = anon.process(text)

# 사람이 REVIEW 큐 검토
for item in result.review_queue:
    print(item.text, item.confidence, item.evidence)
    # 사용자 결정: OK / FP / FN

# 피드백 누적 시 common_words 자동 추천
# (반복 FP 어휘 → 자동 거부 list 후보)
```

### Vault 암호화 + 감사 로그 (`examples/11`, `12`)

```bash
# AES-256-GCM 암호화 vault + 모든 reveal() 호출 감사
KPII_VAULT_PASSWORD=secret k-pii input.txt \
    --strategy tokenize \
    --vault vault.kvault \
    --audit-log audit.jsonl
```

```python
from k_pii.vault import ReversibleVault, AuditLog

vault = ReversibleVault.load("vault.kvault", password="secret")
audit = AuditLog("audit.jsonl")

# 권한 있는 사용자만 복원 — 모든 호출 로깅
with audit.track(user="admin@org.kr", reason="민원 회신"):
    original = vault.reveal("<RRN_1>")
```

## 개발

```bash
python -m venv .venv
.venv/Scripts/activate    # Windows
pip install -e ".[dev,file,security]"
pytest -v
# 659 passed in 2초
python -m k_pii.eval.benchmark -n 60 --seed 0
# 합성 코퍼스에서 라벨별 P/R/F1 출력 (현재 모든 라벨 F1=1.000)

# 단일 파일 (HWPX/HWP/PDF/DOCX/XLSX/CSV/TXT 자동 처리)
k-pii input.hwpx --mode STRICT --strategy partial -o anon.txt
k-pii data.csv --strategy fpe --vault vault.json
k-pii report.docx --strategy tokenize --report cert.txt

# 배치 처리 (디렉토리 일괄)
k-pii ./incoming/ --batch --workers 4 --output-dir ./anon/

# 암호화 vault + 감사 로그
KPII_VAULT_PASSWORD=secret \
  k-pii input.hwp --vault vault.kvault --audit-log audit.jsonl
```

## 전체 작동 요약

### 잘 잡는 것 (Tier S/A — 운영 가능)

| 카테고리 | 핵심 메커니즘 | KDPII F1 | 한계 |
|---|---|---:|---|
| **EMAIL** | RFC 5322 정규식 | 0.999 | 한글 도메인 미지원 |
| **PHONE** | 통신사·지역 prefix + 대표번호 (15xx-18xx) | 0.989 | 비표준 prefix (1247/1040) 거부 |
| **VEHICLE** | 신형 NN[가-힣]NNNN + 용도 한글 화이트리스트 | 0.996 | 2004 이전 (지역명 prefix) 미지원 |
| **RRN** | 13자리 + 날짜 + 한국 체크섬 | 0.995 | 후-2020 무작위화는 체크섬 fail (confidence 0.7로 emit) |
| **FRN** | gender 자리 5-8 + 체크섬 | 0.997 | RRN과 자동 분리 |
| **IP** | IPv4 옥텟 0-255 / IPv6 RFC 4291 | 0.992 | IPv4 사설/공용 구분 안 함 |
| **URL** | http(s)/ftp 표준 | 0.997 | path 내부 PII 별도 검출 |
| **WEIGHT** | "70kg/70킬로" 1-300 | 0.916 | INFO 수준 (단독 PII 아님) |
| **HEIGHT** | "175cm/1.75m" 50-250 | 0.875 | INFO 수준 |
| **DRIVER_LICENSE** | 지방청 코드 11-28 + 12자리 | 0.873 | 체크섬 미적용 (도교공단 미공개) |
| **ACCOUNT** | "계좌" 키워드 + 10-14자리 | 0.843 | 은행별 포맷 사전 미통합 |
| **AGE** | "32세/32살" 0-150 | 0.821 | 한글 음역 ("서른두 살") 지원 |

### 중간 (Tier B — 사람 검토 권장)

| 카테고리 | 핵심 메커니즘 | KDPII F1 | 약점 원인 |
|---|---|---:|---|
| **MAJOR** | KEDI 학과 사전 + 학과/학부/전공 suffix + 단과대 약칭 (의대/공대) | 0.705 | "실용음악과/예술학과" 등 사전 누락 |
| **PASSPORT** | prefix (M/S/O/D/R/T/PP/PD) + 8자리 | 0.795 | 키워드 anchor 모호한 케이스 |
| **DT_BIRTH** | 날짜 + 키워드/풀네임/생 marker anchor | 0.666 | 대화체 "내 생일이 03년 5월 1일이라서" 일부 누락 |
| **EDUCATION** | 대학교 ~330개 사전 + 약칭 매핑 | 0.596 | 고등학교/중학교/초등학교 (KDPII 빈출) 사전 미수록 |
| **POSITION** | titles ~250개 사전 + "직급:" anchor + "님" 호칭 | 0.551 | 인명 인접 "김 대리" 단독 매칭 안 함 (합성 회귀 방지) |

### 약함 (Tier C/D — 본질적 한계)

| 카테고리 | KDPII F1 | 왜 어려운가 |
|---|---:|---|
| **ADDRESS** | 0.403 | KDPII LC_ADDRESS gold 의 동 단위 (화곡동/회기동) 가 anchor 없이 단독 등장. anchor 정책 완화 시 일반 문장 FP 폭증 (예: "강남구 영등포구 등 25개 자치구"). trade-off 결정. |
| **PERSON** | 0.170 | 한국어 단성 성씨 (김/이/박/최) 가 매우 흔한 일반어 prefix. 대화체에서 anchor 없이 단독 등장하는 이름 (수민/지호/은하) 을 잡으면 FP 폭증. PARANOID/STRICT 모드에서 BLOCK 비율은 충분. |
| **CARD** | 0.130 | KDPII 카드 gold 의 **88.3% 가 Luhn invalid** (저자 의도적 fake 데이터). Decision D-006 (Luhn 통과만 emit) 정책 유지 — 실제 production 에서는 정확. |

### 절대 안 잡는 것 (스코프 밖)

| 미지원 | 대신 사용 |
|---|---|
| **이름 단독 (anchor 없음)** | 인접 직책·기관·필드 라벨이 없으면 PERSON 거부 |
| **별명 (PS_NICKNAME)** | KDPII 라벨이지만 가명·PII 모호로 별도 카테고리 미구현 |
| **회사·부서명 (OG_WORKPLACE/OG_DEPARTMENT)** | k-pii 스코프 밖 — 별도 NER 도구 사용 권장 |
| **종교 (OGG_RELIGION) / 혈액형 (TM_BLOOD_TYPE) / 성별 (CV_SEX)** | 카테고리 자체 미구현 |
| **2004 이전 차량번호** (지역명 prefix) | 신형만 cover |
| **외국 여권** | 한국 여권 prefix 만 |
| **소문자 여권 번호** | 한국 여권은 대문자 |
| **이미 가명화된 표기 (박씨/홍씨)** | 의도적 거부 |
| **KCD 진단코드** | 의료 양식 비표준 → 검출기 제외 |

### 위험도 분기 — 같은 카테고리라도 sub-type 별

| 입력 | 라벨 | 위험도 | 사유 |
|---|---|---|---|
| `010-2847-3915` | PHONE | **HIGH** | 모바일 = 개인 직통 |
| `02-3479-6128` | PHONE | MEDIUM | 유선 = 사업장·대표번호 포함 |
| `1588-7264` | PHONE | MEDIUM | 전국 대표 |
| `880101-2123456` | RRN | **CRITICAL** | 단독 식별자 |
| `https://example.com` | URL | INFO | 단독 URL 은 PII 아님 |
| `서울` | ADDRESS | LOW | 단독 행정구역 + anchor 있을 때만 |

### 결합 위험도 자동 평가

`Anonymizer.process()` 가 자동으로 결합 위험도 산정:

```python
result.combined_risk.combined_risk     # → RiskLevel.CRITICAL
result.combined_risk.rationale         # → ["식별자 RRN 등장 → 즉시 식별 가능"]
result.combined_risk.identifiers       # → {"RRN"}
result.combined_risk.quasi_identifiers # → {"ADDRESS", "DT_BIRTH", "PHONE"}
```

「개인정보 비식별 조치 가이드라인」 기반 분류 + k-익명성 평가 (threshold 5).

## 라이선스

Apache License 2.0.

## 인용

본 라이브러리의 KDPII 벤치마크 점수를 보고서·논문에 인용하는 경우:

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

## 법적 참고 문서

- 개인정보보호법 (특히 제23조 민감정보, 제24조 고유식별정보, 제28조의2-5 가명정보 특례)
- 개인정보보호위원회 「가명정보 처리 가이드라인」
- 개인정보보호위원회 「개인정보 비식별 조치 가이드라인」
