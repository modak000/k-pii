# CLAUDE.md — 프로젝트 컨텍스트 (Claude Code / AI 에이전트용)

> Claude Code가 자동으로 읽는 컨텍스트 파일. 사람이 읽어도 무방.
> 이 레포에 처음 합류한 에이전트는 **이 파일을 가장 먼저 읽고** 작업을 시작할 것.

## 1. 미션

한국 공공 부문 (공무원·정부기관) 문서에서 개인정보를 검출하고 가역적으로 가명화하는
Python 라이브러리. **외부 ML 라이브러리 없이** 정규식 + 사전 + 컨텍스트 규칙만으로
구현. 결과물은 한국 개인정보보호법 + 비식별 조치 가이드라인에 맞춰 법적 근거를
부착한 형태로 보고됨.

대상 문서: 공문서 본문(보고서·결재·회의록·기안), 민원 응대 문서, 인사 문서.

## 2. 절대 어기지 말아야 할 설계 원칙

1. **No ML / No external deps in core.** 코어는 Python 표준 라이브러리만 사용
   (`re`, `dataclasses`, `enum`, `datetime`, `hashlib`, `json`). HuggingFace,
   PyTorch, spaCy, transformers — 절대 금지. 이게 본 프로젝트의 차별점.
2. **한국 공공 부문 특화.** 공무원 직책/부처/공문서 양식이 우선. 일반 한국어 NER
   라이브러리들과의 차이는 도메인 fit.
3. **법적 근거를 매 검출 결과에 부착.** `DetectionResult.legal_basis`에 개인정보
   보호법 조항이 들어가야 함 (e.g., "개인정보보호법 제24조의2"). 감사 추적용.
4. **가역 가명화가 기본.** Vault 분리 보관으로 권한 있는 사용자만 복원. 비가역
   마스킹은 별도 모드.
5. **위험도 시스템 + 사용자 임계값.** CRITICAL/HIGH/MEDIUM/LOW/INFO. 사용자가
   PARANOID/STRICT/BALANCED/PERMISSIVE/AUDIT 모드로 차단 기준 선택.
6. **컨텍스트 누적 식별 (Phase 3 핵심).** 한 문서 내에서 강한 단서로 확정된 이름은
   다른 위치에서 약한 단서로 등장해도 인식.
7. **None of the deps in pyproject ever changes lightly.** 코어 deps는 `[]` (빈).
   dev에만 pytest 추가. 새 의존성 추가는 사용자 승인 필요.

## 3. 디렉토리 구조 + 모듈 작성 컨벤션

```
src/k_pii/
├── __init__.py
├── core/
│   ├── types.py            # DetectionResult, RiskLevel
│   └── (modes.py 등 Phase 6에서 추가)
├── checksum/               # 알고리즘 모듈 (재사용)
│   ├── rrn_checksum.py     # RRN/FRN 공용
│   ├── business_reg_checksum.py
│   ├── corp_reg_checksum.py
│   └── luhn.py             # 카드 + 일반 Luhn
└── patterns/               # 각 PII 카테고리 검출기
    ├── rrn.py / frn.py
    ├── business_reg.py / corp_reg.py
    ├── driver_license.py / passport.py / card.py
    ├── medical_insurance.py
    ├── phone.py / email.py / postal_code.py
    ├── ip.py / vehicle.py / url.py
    ├── address.py / account.py
    └── (이후 Phase 3+ 추가)

tests/
└── unit/
    ├── checksum/test_*.py
    └── patterns/test_*.py
```

### `patterns/*.py` 표준 모양

각 모듈은 아래 구조를 따른다 (`rrn.py` 가 레퍼런스):

```python
"""<카테고리 한글 이름> (English Name) detection.

상세 설명 — 포맷, 알고리즘, 제약, 법적 근거.
"""
from __future__ import annotations
import re
from typing import Iterator
from k_pii.core.types import DetectionResult, RiskLevel

LABEL = "RRN"                            # 카테고리 식별자 (대문자 snake)
LEGAL_BASIS = "개인정보보호법 제24조의2"   # 법 조항
CATEGORY = "고유식별정보"                 # 분류

_PATTERN = re.compile(r"...")  # lookarounds로 boundary 처리

def detect(text: str) -> Iterator[DetectionResult]:
    for m in _PATTERN.finditer(text):
        # ... 검증 + 매핑
        yield DetectionResult(...)
```

**`DetectionResult` 필드:**
- `label`, `text`, `start`, `end` (span)
- `risk_level`: `RiskLevel.{CRITICAL,HIGH,MEDIUM,LOW,INFO}`
- `confidence`: 0.0~1.0. 1.0 = 체크섬 통과 등 확정적, 낮을수록 휴리스틱
- `evidence`: list of strings — 어떤 규칙이 매칭됐는지 (감사 추적용)
- `legal_basis`: 법 조항
- `extra`: 추가 데이터 (카테고리, normalize된 값, 부분 그룹 등)

### `checksum/*.py` 표준 모양

```python
WEIGHTS = (...)

def compute_check_digit(payload: str) -> int:
    if len(payload) != N or not payload.isdigit():
        raise ValueError(...)
    # 알고리즘
    return check

def is_valid_checksum(full: str) -> bool:
    if len(full) != N+1 or not full.isdigit():
        return False
    return compute_check_digit(full[:-1]) == int(full[-1])
```

`is_valid_checksum`은 비숫자/길이 불일치 시 **False 반환** (raise 아님).
`compute_check_digit`은 입력이 명백히 잘못되면 **raise ValueError**.

### 테스트 컨벤션

- `tests/unit/<category>/test_<module>.py` (mirror src structure)
- 일반적인 구조:
  ```python
  class TestXXXPositive:    # 매칭되어야 하는 케이스
  class TestXXXNegative:    # 매칭되면 안 되는 케이스
  class TestXXXStructure:   # span 정확도, evidence 등 (선택)
  ```
- 각 모듈당 최소 10케이스. 체크섬 + 포맷 + 컨텍스트 + 경계.
- 합성 PII 값은 손계산으로 검증한 valid 예시를 사용 (commit log/docstring에 검증 기록 남김).

## 4. Git / 커밋 / 배포 컨벤션

- **원격 레포:** https://github.com/modak000/k-pii (main 브랜치 단일)
- **인증:** Windows 측에서는 Fine-grained PAT (Contents: read/write, 단일 레포)
  를 Git Credential Manager에 저장. `.git/config`에는 토큰 박지 않음.
  Marker-Inc-Korea 조직은 권한 범위 밖.
- **커밋 신원:** global config 건드리지 말고 per-commit으로 주입.
  ```bash
  git -c user.name="modak000" -c user.email="rlaehrud63@gmail.com" commit -m "..."
  ```
- **커밋 단위:** Day별/Phase별로 묶음. 한 커밋 = 한 개 논리 단위.
- **메시지 포맷:**
  ```
  <스코프>: <70자 이내 요약>

  - <변경 요점 1>
  - <변경 요점 2>
  - <테스트 카운트 + 시간>

  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  ```
- **푸시 전 항상 pytest 그린 확인.**
- **README/TODO 업데이트** 와 함께 커밋 (진행 상황이 GitHub에서 바로 보이도록).

## 5. 결정 기록 (Decision Log)

이 섹션은 **나중에 봤을 때 "왜 이렇게 했지?"** 가 생길 만한 비자명한 선택들을 기록.

### D-001. RRN 후-2020 무작위화 처리
**문제:** 행정안전부가 2020-10-05부터 RRN 7~13번째 자리를 무작위화. 따라서 신규
발급 RRN은 표준 체크섬을 통과하지 않을 수 있음.
**선택:** 패턴 + 날짜 유효 + 체크섬 통과 → confidence 1.0 / 패턴 + 날짜 유효 + 체크섬
실패 → confidence 0.7 (둘 다 CRITICAL). 체크섬 실패가 곧 "RRN 아님" 을 의미하지
않음.
**이유:** FN(놓침)이 FP(오탐)보다 훨씬 위험한 PII. PARANOID/STRICT 모드는 confidence
0.7도 차단, PERMISSIVE는 1.0만.

### D-002. RRN vs FRN 파티션
**문제:** RRN과 FRN은 동일 13자리 포맷. 7번째 자리(gender)가 1·2·3·4·9·0이면 RRN,
5·6·7·8이면 FRN.
**선택:** `rrn.py` 와 `frn.py` 각각 자기 gender 집합만 매칭. 겹치지 않게 파티션.
**이유:** 라벨이 다르면 법적 근거도 다름 (RRN=제24조의2, FRN=시행령 제19조 + 출입국
관리법 제31조). 분리해야 위험도/처리 규칙 분리 가능.

### D-003. 법인등록번호 vs RRN 시각적 충돌 해소
**문제:** 법인번호도 13자리 + 하이픈 6-7 사이. RRN과 동일 모양.
**선택:** `corp_reg.py` 에서 (a) 법인 체크섬 통과, AND (b) RRN 체크섬 *실패* 이거나
첫 6자리가 *유효 날짜 아님* 인 경우만 emit. RRN/FRN이 이미 우선 claim.
**이유:** 한전(191211-0006637) 같은 실제 법인번호는 첫 6자리가 날짜처럼 보이지만
RRN 체크섬은 실패함. 두 체크섬 동시 통과 + 날짜 유효는 매우 드물고, 그 경우 RRN
우선 (실제 RRN일 가능성이 높음).

### D-004. 운전면허번호 체크섬 미적용
**문제:** 도로교통공단의 12자리 운전면허번호 체크 알고리즘은 공개되지 않음.
**선택:** 패턴 매칭 + 지방경찰청 코드(11~28) 검증만. confidence 0.85.
**이유:** 잘못된 체크섬 알고리즘으로 FN 만드는 것보다 휴리스틱이 안전. 사용자가
공식 자료 확보하면 추가 검증 가능 (TODO.md).

### D-005. 건강보험증번호 키워드 anchor
**문제:** 11자리 평이한 숫자 = 휴대전화(010+8자리)와 충돌. 단독 11자리는 FP 폭증.
**선택:** "건강보험" / "의료보험" / "보험증" 키워드가 **25자 이내 앞에** 있을 때만
emit.
**이유:** 25자는 "건강보험증 번호: " 같은 라벨링부터 짧은 문구까지 커버하면서
문단 단위 키워드 멘션은 배제하는 trade-off 지점.

### D-006. 사업자번호/카드번호는 체크섬 필수
**문제:** 짧은 숫자열(10자리/16자리)은 FP가 많음.
**선택:** 사업자번호는 국세청 가중합 체크섬, 카드는 Luhn 모두 **통과해야 emit**.
체크섬 실패 = 그냥 숫자열 (대부분 진짜 PII 아님).
**이유:** RRN과 달리 이 두 카테고리는 후-2020 같은 무작위화 이슈 없음. 알고리즘
안정적. 통과 안 하면 PII로 볼 이유 없음.

### D-007. 도로명 주소는 anchor 필수
**문제:** "...로 123" 같은 도로명-숫자 패턴은 일반 문장에도 흔함 (예: "테헤란로
사람들"). 무조건 매칭하면 FP 폭증.
**선택:** (a) 시·도/시·군·구 토큰이 앞에 붙어 있거나 (b) "주소" 키워드가 20자
이내 앞에 있어야 emit.
**이유:** Phase 3에서 행정구역 사전 통합 시 정확도 끌어올릴 예정 (TODO.md).

### D-008. 계좌번호는 키워드 anchor
**문제:** 10~14자리 하이픈 패턴 = 전화번호와 충돌.
**선택:** "계좌" 키워드 즉시 앞에 있을 때만 매칭.
**이유:** Phase 2 베이스라인. 은행별 포맷 사전 추가 시 keyword 없이도 매칭 가능
하게 확장 예정 (TODO.md).

### D-009. URL은 INFO 수준
**문제:** URL 자체는 보통 PII 아님.
**선택:** 검출은 하되 `RiskLevel.INFO`. 차단/마스킹 대상 아님. 다만 path/query에
이메일/ID 등 임베드된 PII 있을 수 있어 emit해서 후속 룰이 스캔하게 함.
**이유:** 가독성. 사용자가 임계값 PERMISSIVE 이상이면 무시.

### D-010. 차량번호 신형만 지원
**문제:** 2004년 이전 차량번호 ("서울12가1234" — 지역명 prefix) 는 실무에서 거의
안 보임.
**선택:** 신형 (NN[가-힣]NNNN, NNN[가-힣]NNNN) 만 지원.
**이유:** YAGNI. 사용자가 실제 부딪히면 추가.

## 6. Phase 진행 현황 (2026-05-15 기준)

| Phase | 상태 | 결과물 | 비고 |
|-------|------|--------|------|
| 1. 결정적 PII (체크섬) | ✅ 완료 | 8 카테고리 + 4 체크섬 모듈 | Day 1~3 |
| 2. 비검증 PII (베이스라인) | ✅ 완료 | 8 카테고리 + FAX | IPv6/+82/지번 보강 |
| 3. 컨텍스트 기반 이름 탐지 | ✅ 베이스라인 완료 | 사전 5종 + context + person.py | 사전 큐레이션은 사용자 입력 |
| 4. 도메인 특화 (공문서·민원·인사) | ✅ 베이스라인 완료 | DOC_ID + PETITION_ID + EMPLOYEE_ID | medical은 사용자 입력 대기 |
| 5. Vault + 모드 + 일반화 | ✅ 완료 | vault + 3 modes + 4 generalizations | JSON schema v1 |
| 6. 법적 매핑 + 위험도 + 리포팅 | ✅ 완료 | Anonymizer + 5 modes + reporting + CLI | `k-pii` 엔트리포인트 |
| 7. 평가 + 문서화 | ✅ 베이스라인 완료 | 합성기 + 메트릭 + 벤치마크 + docs/ | 합성 50×4seed F1=1.000 |

**누적 수치:**
- PII 카테고리 21종 (Phase 1·2 17종 + PERSON + DOC_ID + PETITION_ID + EMPLOYEE_ID)
- 테스트 427개, ~0.4초 (Python 3.13)
- 코어 dependencies 0개
- 합성 코퍼스 6템플릿×60×5seed (300문서) 에서 **micro F1 = 1.000**
- 사전 데이터: 성씨 286, 부처/청 100+, 직급 200+, 행정구역 250+

## 7. 어디서 멈췄나 / 다음에 할 일

**마지막 큰 작업:** Phase 7 (평가 인프라) + Phase 4 (도메인 룰) + Phase 3.1 사전
확장 + docs/ 일괄 구현. 테스트 394 passed, 합성 50×4seed F1=1.000.

**남은 후보 (모두 사용자 도메인 입력 필요):**

A) **실데이터 벤치마크** — 익명화된 실제 공문서로 합성 코퍼스의 점수가
   유지되는지 확인. 현재 F1=1.0 은 합성 템플릿이 좁아서 나온 수치이므로
   실제 분포에서는 더 낮을 가능성.

B) **사전 큐레이션 (Phase 3.1 / 4.1)** — 사용자 실무 입력 기반:
   - 부처·직급별 직책 사전 세분화
   - 공문서 필드 라벨 — 실무 양식 샘플 필요
   - 의료 도메인 (KCD/EDI) 포함 여부 결정

C) **계좌·사업자 분기** — 은행별 포맷 / 법인 vs 개인사업자 위험도 분기.

D) **k-익명성·l-다양성 일반화** — `generalization/` 에 추가 알고리즘.

**권장 순서:** A (실데이터 검증) → B (사전 확장) → C·D. 평가 인프라는 이미
있으니 사용자 샘플만 들어오면 즉시 측정 가능.

## 8. 도메인 판단 대기 중인 항목 (사용자 입력 필요)

`TODO.md` 의 "도메인 판단이 필요한 보류 항목" 섹션 참고. 요약:
- 운전면허 체크섬 알고리즘 확보
- 사업자번호 위험도를 법인/개인사업자별로 분기할지
- 법인번호 위험도 기준 (현재 MEDIUM)
- 공문서 필드 라벨 사전 — 본인 실무 샘플 필요
- 공무원 직책 사전 세분화 수준 (부처별 어디까지)
- 의료 도메인 (KCD/EDI) 포함 여부

## 9. 새 환경 셋업 (모바일 / 다른 머신 / claude.ai/code)

```bash
git clone https://github.com/modak000/k-pii
cd k-pii
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv/Scripts/activate
pip install -e ".[dev]"
pytest
# 394 passed in ~0.4s 가 정상
# CLI 사용: k-pii input.txt --mode STRICT --strategy tokenize --vault vault.json
# 벤치마크: python -m k_pii.eval.benchmark -n 50 --seed 0
```

**필요한 도구:** Python 3.10 이상. 코어는 표준 라이브러리만, dev는 pytest.

**Git push 시 인증:**
- 새 머신에서는 GitHub Fine-grained PAT를 새로 발급 (modak000/k-pii 단독 권한,
  Contents: write).
- `gh auth login --with-token < token.txt` 또는 `git credential approve`로 저장.
- Marker-Inc-Korea 조직 권한은 항상 제외.

## 10. 법령 참고 (모든 검출 결과 매핑 출처)

본 라이브러리는 다음 한국 법령/가이드라인을 근거로 함:

- **개인정보보호법**
  - 제2조: 개인정보·가명정보 정의
  - 제23조: 민감정보 처리 제한 (건강·정치 성향·노조 등)
  - 제24조: 고유식별정보 처리 제한 일반
  - 제24조의2: 주민등록번호 처리 제한
  - 제28조의2~5: 가명정보 처리 특례
  - 제29조: 안전조치의무
- **개인정보보호법 시행령**
  - 제18조: 민감정보 범위
  - 제19조: 고유식별정보 범위 (RRN, 여권, 운전면허, FRN)
- **개인정보보호위원회**
  - 「가명정보 처리 가이드라인」
  - 「개인정보 비식별 조치 가이드라인」
- **상법 제40조**: 법인등기/법인등록번호
- **출입국관리법 제31조**: 외국인등록
- **국민건강보험법 제96조**: 자료의 보호
- **금융실명거래 및 비밀보장에 관한 법률**: 계좌 관련

## 11. 어떤 의문이 들면

1. 모듈 동작 → 해당 `patterns/*.py` 의 docstring + 해당 `tests/.../test_*.py` 케이스
2. 알고리즘 정확성 → `checksum/*.py` 의 docstring + 손계산으로 검증 가능
3. 왜 이렇게 설계? → 이 파일의 Section 5 (Decision Log)
4. 다음 뭐 하나? → 이 파일의 Section 7 + `TODO.md`
5. 법조항 어디? → 각 모듈의 `LEGAL_BASIS` + Section 10

## 12. 사용자 컨텍스트 (modak000)

- 한국 공공 부문 도메인 지식 보유 (이 프로젝트의 도메인 전문가)
- 외부 ML 의존성 회피를 명시적으로 요구 (Section 2 #1의 근거)
- 작업 스타일: 단계별 빌드 + 본인 리뷰. AI 에이전트가 구현하고 본인은 도메인
  판단 + 시니어 리뷰
- 커뮤니케이션: 간결한 한국어 선호. 긴 요약 X, 핵심만.
- 보안: Marker-Inc-Korea 조직 권한은 절대 부여하지 않음 (개인 계정 modak000
  단독 사용)
