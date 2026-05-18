# k-pii

[![Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-659%20passed-brightgreen.svg)](#)
[![Korean PII](https://img.shields.io/badge/도메인-한국%20공공-red.svg)](#)

한국 공공 부문 문서를 위한 규칙 기반 개인정보(PII) 비식별 라이브러리. **외부 ML 없이** 룰만으로 production-ready.

> **상태:** v1.0.0 release-ready — **한국 공공 PII 솔루션**.
> 24 PII + 6 처리 전략 + HWP/PDF/표 입력 + Vault 암호화 + 감사 로그 + 배치 + 검토 큐 + HTML 리포트 + 한자/로마자 + **OpenAI Privacy Filter / Presidio / MCP 옵셔널 연계**.
> 합성 코퍼스 480문서 micro F1 = 1.000 / KLUE-NER Korean-only F1 = 0.338.
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

## 현재 구현 상태

### Phase 1 — 결정적 PII (체크섬 기반) ✅

| 항목 | 비고 |
|------|------|
| 주민등록번호 (RRN) + 체크섬 | 한국인 전용 (gender 1·2·3·4·9·0); 후-2020 무작위화 신뢰도 0.7 반영 |
| 외국인등록번호 (FRN) | 외국인 전용 (gender 5·6·7·8); RRN과 동일 체크섬 |
| 사업자등록번호 + 체크섬 | 국세청 알고리즘 (10자리) |
| 법인등록번호 + 체크섬 | Luhn-like (13자리); RRN과 동시 일치 시 RRN 우선 |
| 운전면허번호 | 12자리 포맷 + 지방청 코드 11~28 검증 |
| 여권번호 | 1-2자 prefix + 8자리 |
| 카드번호 + Luhn | 13~19자리, Luhn mod-10 검증 |
| 의료보험증번호 | 11자리, "건강보험/의료보험/보험증" 키워드 25자 윈도우 |

### Phase 2 — 비검증 PII ✅

| 항목 | 비고 |
|------|------|
| 전화번호 (휴대/일반/070/국제) | 010~019 / 02 / 031~064 / 070; `+82` / `0082` 지원 |
| 팩스번호 | "팩스/FAX/전송" 키워드 anchor |
| 이메일 | RFC 5322 실용 부분집합 |
| 우편번호 | 5자리(키워드 필수) + 6자리(레거시 하이픈) |
| IP 주소 | IPv4 (옥텟 0~255 검증) + **IPv6** (RFC 4291, 단축/IPv4-mapped 포함) |
| 차량번호 | 신형 NN(N)[가-힣]NNNN |
| URL | http(s) — INFO 수준 |
| 주소 | 도로명(로/길/대로) + **지번(동/읍/면/리 + 번지)** |
| 은행 계좌번호 | "계좌" 키워드 anchor |

### Phase 3 — 컨텍스트 기반 이름 탐지 ✅

종합 사전 (공개데이터 출처):
- **성씨** 286개 (통계청 「인구주택총조사」 기준 + 복성)
- **직책 사전** — 일반직 1~9급 (관리관/이사관/사무관/주사 등) + 특정직 전직군
  - 경찰 11계급 (치안총감~순경)
  - 소방 11계급 (소방총감~소방사)
  - 군 19계급 (원수~이병)
  - 검사·법관·외무공무원
- **부처 사전** — 정부조직법 기준 19부 6처 18청 6위원회 + 2026 개편 신설/개명
  - 약칭 매핑 (한글: 기재부/행안부, 영문: MOEF/MOIS, KASA, OKA 등)
- **행정구역 사전** — 17 광역 + 226 기초자치단체 (75자치시·82자치군·69자치구)
- **필드 라벨** — 공문서 양식 (성명/신청인/피의자/수사관/신고자 등)
- **조사 처리** + **누적 사전** (한 문서 내 이름 재인식)

### Phase 5 — Vault + 처리 모드 ✅

- `ReversibleVault` — 가역 가명화 저장소 (JSON schema v1, salted SHA-256 fingerprint)
- `tokenize` / `redact` / `hashed` — 3가지 치환 전략
- `generalization/{age,date,address,occupation}` — 일반화 (구간화·상위 행정구역·범주)

### Phase 6 — 통합 API + 정책 + 리포팅 + CLI ✅

- `ProcessingMode` — PARANOID / STRICT / BALANCED / PERMISSIVE / AUDIT
- `Anonymizer` 통합 클래스 — 검출 → 정책 결정 → 처리 (BLOCK / REVIEW / ALLOW)
- `legal/mapping.py` — 카테고리 ↔ 법조항 단일 매핑
- `reporting/{summary,certificate}.py` — 처리 요약 + 감사 증명서
- `k-pii` CLI — `k-pii input.txt --mode STRICT --strategy tokenize --vault vault.json`

### Phase 4 — 도메인 특화 룰 ✅ 베이스라인

- `domain/government.py` — 정부 문서번호 (DOC_ID)
- `domain/civil_petition.py` — 민원·정보공개 번호 (PETITION_ID)
- `domain/hr.py` — 사번·공무원번호·직원번호·임용번호 (EMPLOYEE_ID, tight anchor)

### Phase 7 — 평가 + 문서화 ✅ 베이스라인

- `eval/synth.py` — 합성 공문서 생성기 (6 템플릿, Faker 불사용)
- `eval/metrics.py` — Precision/Recall/F1 (partial/strict 매칭)
- `eval/benchmark.py` — `python -m k_pii.eval.benchmark -n 60` 으로 즉시 평가
- `docs/{legal_mapping,risk_levels,coverage}.md` — 법조항·위험도·커버리지 문서

### Phase 11 — 외부 통합 ✅ (옵셔널)

**OpenAI Privacy Filter** + **Microsoft Presidio** + **MCP 서버** — 모두 optional:

```python
# 1) OpenAI Privacy Filter (hybrid, [ml] extras)
from k_pii import Anonymizer, get_privacy_filter_adapter
pf = get_privacy_filter_adapter(device="cpu")
anon = Anonymizer(secondary_detector=pf, merge_mode="union")

# 2) Microsoft Presidio plugin ([presidio] extras)
from presidio_analyzer import AnalyzerEngine
from k_pii.integrations.presidio_plugin import KPiiRecognizer
analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(KPiiRecognizer())  # 22개 한국 라벨 자동 추가

# 3) MCP 서버 — Claude Desktop 등 LLM 도구로 노출 ([mcp] extras)
# claude_desktop_config.json:
# {"mcpServers": {"k-pii": {"command": "k-pii-mcp-server"}}}
```

가이드:
- [`docs/integration_openai_privacy_filter.md`](docs/integration_openai_privacy_filter.md)
- [`docs/integration_presidio.md`](docs/integration_presidio.md)
- [`docs/integration_mcp.md`](docs/integration_mcp.md)

### 빠른 시작 / 예제

`examples/` 디렉토리 — 15개 실행 가능 스크립트:

| | |
|---|---|
| `01_basic_anonymize.py` | 기본 가명화 |
| `13_llm_safe_filter.py` | **LLM 호출 전 PII 필터** (가장 핫한 use case) |
| `14_hybrid_with_privacy_filter.py` | OpenAI Privacy Filter 연계 |
| `15_presidio_integration.py` | Microsoft Presidio plugin |

전체 목록: [`examples/README.md`](examples/README.md)

### Phase 10 — 솔루션 인프라 ✅

**입력 호환성:**
- `.hwp` (한컴 5.x OLE — `olefile` 외부 deps) + 기존 `.hwpx`
- `.pdf` (텍스트 레이어 — `pypdf` 외부 deps)
- **표 컬럼-단위 처리** — `k_pii.tabular.anonymize_records()` — CSV/XLSX 헤더
  자동 매핑 (성명→PERSON, 주민번호→RRN 등 80+ 헤더 변형)

**보안 (개인정보보호법 제29조 안전조치의무):**
- **Vault 암호화** — AES-256-GCM + PBKDF2 (480k iter). `cryptography` 외부 deps
- **감사 로그** — 모든 `vault.reveal()` / `store()` 호출 JSONL 기록
- CLI: `--vault-password` 또는 환경변수 `$KPII_VAULT_PASSWORD`, `--audit-log`

**배치 처리:**
- 디렉토리·glob 일괄 처리 (`k-pii ./docs/ --batch --workers 4`)
- 진행률·실패 보고 + 부분 성공 처리

**사람 검토 워크플로우:**
- **검토 큐** (`k_pii.review`) — REVIEW 항목 영구 저장 + OK/FP/FN 마킹
- **피드백 학습** — FP 마킹 누적 → `common_words` 자동 추천 (수동 반영)
- **HTML 리포트** — 단일 파일, 색상 코딩 + 인터랙티브 마킹 다운로드

**표기 변형 매칭:**
- 한자 → 한글 (`hanja_to_hangul("洪吉童")` → `"홍길동"`)
- Revised Romanization (`romanize_name("홍길동")` → `"Hong Gildong"`)
- 변형 후보 8종 자동 생성 (성-이름 분리, 하이픈, 대소문자 등)

### Phase 9 — 파일 입력 + 부분 마스킹/FPE + 식의약·법조 도메인 ✅

**파일 입력 (io_/ — 표준 라이브러리만):**
- `.hwpx` (한컴 OWPML), `.docx`, `.xlsx`, `.csv`/`.tsv`, `.txt`/`.md`
- 확장자 자동 디스패처: `from k_pii.io_ import read_text`

**처리 전략 확장 (6종):**
- `tokenize` — `<RRN_1>` 가역 토큰
- `redact` — `[주민등록번호]` 비가역 라벨
- `asterisk` — `**************` 길이 보존
- `hashed` — `<RRN:abc123>` 단방향 해시
- **`partial`** — `880101-1******` / `홍OO` / `010-****-5678` 등 부분 마스킹 (실무 공문서 양식)
- **`fpe`** — `880101-1234568` → `771202-2345671` 형식 보존 (자릿수·하이픈·체크섬 일관성)

**식의약·법조 도메인 추가 PII:**
- `EDI_DRUG` — 식약처 의약품 표준코드 (9/13자리, 키워드 anchor)
- `COURT_CASE` — 법원 사건번호 (`2024가합12345`)

### Phase 8 — 결합 위험도 + k-익명성 ✅

「개인정보 비식별 조치 가이드라인」 직접 대응:

- `analytics/combined_risk.py` — 식별자/준식별자/민감속성 분류 + 조합 위험도
  자동 계산. ``Anonymizer`` 결과의 `combined_risk` 에 자동 부착.
- `analytics/k_anonymity.py` — k-익명성 평가 + 일반화 제안 (threshold 기본 5)
- 추가 PII: **PNU** (필지고유번호 19자리, 결정적)

```python
from k_pii import Anonymizer, ProcessingMode, k_anonymity

result = Anonymizer(mode=ProcessingMode.STRICT).process(text)
print(result.combined_risk.combined_risk)       # → RiskLevel.CRITICAL
print(result.combined_risk.rationale)            # → ["식별자 RRN 등장 → 즉시 식별 가능"]

# 데이터셋 단위 k-익명성 평가
records = [{"PERSON": "<PERSON_1>", "ADDRESS": "<ADDRESS_1>"} for _ in range(7)]
report = k_anonymity(records, threshold=5)
print(report.k, report.satisfies_threshold)      # → 7, True
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

**DRIVER_LICENSE (운전면허)** — 지방청 코드 11~28 화이트리스트
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
✓ 우편번호 03187                  (서울 01~08)
✓ 우편번호 13520                  (경기 10~18)
✗ 우편번호 09999                  (09 = 시·도 미할당)
✗ 우편번호 99000                  (99 = 미할당)
```

**IP** — IPv4 옥텟 0~255 검증, IPv6 RFC 4291
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

## 개발

```bash
python -m venv .venv
.venv/Scripts/activate    # Windows
pip install -e ".[dev,file,security]"
pytest -v
# 597 passed in ~1.8s
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

## 라이선스

Apache License 2.0.

## 법적 참고 문서

- 개인정보보호법 (특히 제23조 민감정보, 제24조 고유식별정보, 제28조의2~5 가명정보 특례)
- 개인정보보호위원회 「가명정보 처리 가이드라인」
- 개인정보보호위원회 「개인정보 비식별 조치 가이드라인」
