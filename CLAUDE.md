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

### D-011. KDPII 라벨 매핑 정정
**문제:** 초기 평가에서 `AC_*` prefix 가정으로 매핑 → TP 0건. KDPII 실제 라벨은
`TMI_EMAIL / QT_PHONE / QT_RESIDENT_NUMBER / TMI_SITE` 등 다른 prefix.
**선택:** 분포 직접 조사 후 매핑 정정. `eval/kdpii.py::KDPII_LABEL_MAP` 참조.
**효과:** EMAIL F1=0.999 등 진짜 정확도 드러남. PHONE F1=0.989, RRN F1=0.995.

### D-012. ADDRESS 단독 행정구역 + 국가명 anchor 차등
**문제:** KDPII LC_ADDRESS gold 의 30% 가 "서울/화곡동/한국" 같은 단독 행정구역.
**선택:** dict 통과 + 대화체 anchor 필수. 단 country (한국/미국/일본) 만 anchor
면제 (KDPII LCP_COUNTRY 86% 가 anchor 없음).
**효과:** ADDRESS F1 0.18 → 0.52, 일반 문장 ("강남구 영등포구 등 25개 자치구") FP 회피.

### D-013. PERSON 평가는 풀네임 (3자+) 만
**문제:** KDPII PERSON gold 의 50% 가 1-2자 별명·단성 ("재명/미선/주").
**선택:** 평가 시 `person_min_length=3` 기본. 1-2자 단독은 PII 아니라고 봄
(개인정보보호법 제2조: 그 자체로 식별 불가).
**이유:** 공공 문서 도메인 = 풀네임 위주. KDPII 의 일상 대화 라벨 정책과 도메인 차이.

### D-014. PERSON 다중 거부 룰 (호칭/접미사/행정구역/학교/은행/어말)
**문제:** 한국어 단성 성씨 (김/이/박/최/정) = 매우 흔한 일반어 prefix → PERSON FP 폭증.
**선택:** 10+ 거부 룰 + 한국어 형태소 사전 (`_COMMON_KOREAN_ENDINGS`) — 어말
"은데/는데/라서/면서/까지/라고" 등 16종.
**효과:** PERSON 오탐 5,202 → 2,120 (-59% 누적).

### D-015. POSITION = 준식별자, 검출 후 결합 위험도 평가
**문제:** "선생/교수/기사" 단독 호칭 — KDPII gold 가 PII 라벨 X.
**선택:** POSITION 카테고리 별도 검출 + `analytics/combined_risk` 의 quasi_identifiers
집합에 추가. PERSON + POSITION + AGE 결합 시 CRITICAL.
**이유:** 「개인정보 비식별 조치 가이드라인」 의 *직업·직책 = 준식별자* 정의 부합.
KDPII 와 정책 다름 (KDPII = 단독 라벨 X, k-pii = 검출 + 결합 평가).

### D-016. 합성 코퍼스 풍부화 + 회귀 감지 sanity 용도
**문제:** 6 템플릿 단순 양식에 검출기 과적합 → 합성 F1=1.000 (조작된 느낌).
**선택:** (1) 13 템플릿 다단락 본문 (보도자료/감사보고/계약서/판결문/세무/인사발령/
행정처분 등 추가), (2) 합성 점수를 *회귀 감지 sanity check* 으로 격하.
**효과:** 합성 F1 1.000 → 0.85 (정직). 실제 정확도는 KDPII (0.699) + 공공 문서
본문 산문 측정 (~0.83).

### D-017. 부스트 길이 차등 (`deterministic_pii_nearby`)
**문제:** RRN/PHONE 인접 부스트 +0.40 이 일반어 (전화했어/마실거) 까지 PERSON 으로 끌어올림.
**선택:** 3자+ 풀네임 +0.40 유지, 2자 단명 +0.20 약화.

### D-018. 직책 + 연결어미 prefix 매칭 ("주임이며" → "주임")
**문제:** "박철수 주임이며" 같은 본문에서 `strip_trailing_particle("주임이며")` 가
"이며" 못 strip → title 인식 실패.
**선택:** `_has_title_adjacent` 의 `_resolve_title` 함수 — title dict 의 prefix 매칭.
**효과:** 공공 문서 본문 산문 PERSON F1 ~0.83 달성.

### D-019. EDUCATION 정규식 outer named-group 분리
**문제:** outer `full` group 이 모든 alternation 흡수 → 약칭 (고대/홍대) 매칭 실패.
**선택:** non-capturing outer `(?:...)` + 분리된 named groups + 짧은 X초/X중/X고
약칭은 학교 anchor (졸업/다녀/출신/모교) 필수.

### D-020. ADDRESS 국적 접미사 자동 strip
**문제:** "한국인/미국인/일본인" 같은 국적 표현 검출 실패.
**선택:** `_PATTERN_ADMIN_TOKEN` 매칭 후 token.endswith("인") + is_country(token[:-1])
통과 시 "인" strip. "확인" 같은 일반어는 strip 후 1자라 dict 매칭 X → 영향 없음.
**효과:** ADDRESS 정탐 +153.

### D-021. DT_BIRTH 비-생일 키워드 거부
**문제:** 합성 본문의 "선고일자/시행일자/배포일자" 같은 일반 일자가 DT_BIRTH 로 잡힘.
**선택:** `_NON_BIRTH_KEYWORDS` 30+ 사전 — 직전에 있으면 DT_BIRTH 거부.

### D-022. 자동 과탐 어휘 수집 도구
**문제:** common_words 무한 누적은 비효율.
**선택:** `eval/fp_collector.py` 신규 — 비식별된 텍스트 (판결서/뉴스 등) 받으면
PERSON 과탐 어휘 자동 수집 → 일반어 사전 후보 추출.
**사용:** `python -m k_pii.eval.fp_collector text.txt --min-freq 2`

### D-023. Wikipedia API 를 로컬 부트스트랩 코퍼스로 사용
**문제:** 한국 정부 사이트 (data.go.kr / aihub.or.kr / scourt.go.kr) 는 클라우드
호스트에서 막혀 있고, 실데이터 평가 진입 장벽이 큼.
**선택:** `data/fetch_corpus.py` — `ko.wikipedia.org/w/api.php` 의 `extracts`
endpoint 로 행정/법령 추상 토픽 11편 (≈25K chars) 자동 수집. User-Agent 필수.
**이유:** Wikipedia 행정 토픽은 (a) 공무원 도메인 어휘가 풍부하고 (b) 개인 PII
가 거의 없으면서 (실명 등장도 박근혜·박정희 같은 공인) (c) 어디서든 접근 가능.
판결서·AI Hub 등 본 데이터가 들어오기 전 부트스트랩 용도.

### D-024. fp_collector → common_words 사이클 가이드라인
**관찰 (2026-05-21 로컬 세션):** Wikipedia 코퍼스에서 자동 수집한 46개 freq 2+
PERSON 후보 중 *3개* 만 실제 인물 (박근혜·박정희·김철용=법학자) — 사람 검토
시 ~93% 가 일반어. 자동 수집 → 사람 검토 → 사전 추가 루프가 효율적.
**부작용 (트레이드오프):** 사전 확장이 NameDictionary 부스트 인접 토큰을 약화
시켜 일부 *진짜 인명* 의 검출도 떨어질 수 있음. 박근혜 4건 → 0건 (모두 "박근혜
정부" 형태). 합성 벤치 F1 = 0.852 유지 → 도메인 목표 (공식 공문서) 에는 영향
없음이 확인됨. 일상 대화 코퍼스 (KDPII 등) 에는 부정적 영향 가능 — 별도 평가
필요 시 확인.
**원칙:** "도메인 핏" 우선. 본 라이브러리는 공공 문서 대상 → 약한 컨텍스트의
인명 검출보다 일반어 FP 제거가 우선.

### D-025. 실제 정부 텍스트 (korea.kr) — Wikipedia 보다 우수한 부트스트랩
**문제:** Wikipedia 추상 토픽은 어휘가 좁고 (행정/법령 추상 용어 위주) 박근혜
처럼 anchorless 인용이 잘 검출되어 사전 확장 부작용이 큼.
**관찰 (2026-05-21 commit de5ddf2):** korea.kr 정책브리핑 20편 (42KB) 추가
크롤링 → fp_collector → 49 freq-3+ 후보 중 47개 일반어 + 2개 실인 (이재명
대통령 + 이억원 금융위원장).
**핵심 차이:** 실제 정부 보도자료에서는 인명에 *강한 직책 anchor* 가 즉시 인접
("이재명 대통령", "이억원 금융위원장") → 사전 확장해도 NameDictionary 우회 가능,
부작용 0. 이재명 7/7, 이억원 4/4 검출 유지. Wikipedia 의 "박근혜 정부" 패턴과 대비.
**원칙:** fp_collector 부트스트랩은 가급적 *실제 정부 텍스트* 로 (Wikipedia 는
보조 용도). korea.kr 외에도 casenote.kr/law.go.kr/data.go.kr 가 로컬에서 접근
가능 (TLS 협상 차이로 PowerShell 또는 Python urllib 필요, Git Bash curl 은 일부
사이트에서 000 실패).

### D-027. AI Hub 데이터셋 = 안심존 벽 (확인 완료)
**조사 (2026-05-21):** 사용자 요청으로 AI Hub 71844 (`민간 민원 상담 LLM 사전학습
및 Instruction Tuning 데이터`) 와 569 (`행정 문서 대상 기계독해 데이터`) 페이지
직접 probe. 두 데이터셋 모두 "안심존" 분류:
  - AI Hub 계정 가입 (개인/기관)
  - 활용 신청서 + 보안서약서 (security_pledge.hwp)
  - IRB 심의신청서 (헬스케어 안심존은 필수, 일반 안심존은 일부 생략)
  - K-ICT 빅데이터센터 등 지정 시설 *물리적 방문*
  - 외부 반출 불가 — 안심존 내에서만 가공/사용
**다운로드 endpoint 결과:** `/file/down.do?fileSn=...` 일부는 인증 없이 zip 다운로드
가능했지만 내용은 *AI 모델 설치 매뉴얼* 같은 부속 문서. 실제 학습 데이터는 안심존.
**casenote.kr / law.go.kr 도 막힘 (commit 다음번):**
  - casenote.kr: pro 계정 paywall, 무료 tier 는 메타데이터만
  - law.go.kr: JavaScript 렌더링 — 초기 HTML 에 본문 없음, AJAX 로 iframe 로드
**결론:** 본 라이브러리 부트스트랩에 활용 가능한 *대용량 라벨링된 한국 공공
데이터* 직접 접근 경로는 사실상 닫혀 있음. 다음 권장 순서:
  1. korea.kr 정책브리핑 추가 크롤링 (현재 20편 → 100편+ 가능)
  2. Korean Wikisource 위키문헌 (`ko.wikisource.org`) — 법령 본문 plain Wikitext
  3. 사용자가 안심존 방문 후 비식별된 sample 만 USB 로 추출 → fp_collector 처리
  4. 국가법령정보 OPEN API (open.law.go.kr) — 키 등록 후 사용

### D-026. Windows 호환 — encoding 명시 & cryptography sentinel
**문제 (commit eb1f2bc, 로컬 Windows 첫 실행):** 클라우드 Linux 에서는 안 보이던
3건의 호환 문제 발견.
**선택:**
1. `tests/unit/test_batch.py`, `tests/unit/review/test_feedback.py` 의 `read_text()`
/ `write_text()` 호출에 `encoding="utf-8"` 명시 (Windows 기본 cp949 → 한글
UTF-8 파일 읽기 실패).
2. `tests/unit/vault/test_encrypted.py` 의 `HAS_CRYPTO` sentinel — 모듈 import
만 확인하던 것을 `import cryptography` 까지 시도하도록 변경 (모듈은 항상 import
되지만 실제 cryptography 패키지가 없으면 함수 호출 시점에 ImportError 발생 →
skipif 가 안 먹었음).
**효과:** Windows 에서도 클린 패스 (694 passed, 5 skipped). 이후 모든 신규
테스트는 path I/O 시 `encoding="utf-8"` 강제 권장.

## 6. Phase 진행 현황 (2026-05-21 기준)

| Phase | 상태 | 결과물 | 비고 |
|-------|------|--------|------|
| 1. 결정적 PII (체크섬) | ✅ 완료 | 8 카테고리 + 4 체크섬 모듈 | Tier S, F1 0.95+ |
| 2. 비검증 PII (베이스라인) | ✅ 완료 | 8 카테고리 + FAX | IPv6/+82/지번 보강 |
| 3. 컨텍스트 기반 이름 탐지 | ✅ 베이스라인 완료 | 사전 5종 + context + person.py | 사전 큐레이션은 사용자 입력 |
| 4. 도메인 특화 (공문서·민원·인사) | ✅ 베이스라인 완료 | DOC_ID + PETITION_ID + EMPLOYEE_ID | medical은 사용자 입력 대기 |
| 5. Vault + 모드 + 일반화 | ✅ 완료 | vault + 3 modes + 4 generalizations | JSON schema v1 |
| 6. 법적 매핑 + 위험도 + 리포팅 | ✅ 완료 | Anonymizer + 5 modes + reporting + CLI | `k-pii` 엔트리포인트 |
| 7. 평가 + 문서화 | ✅ 완료 | 합성기 + 메트릭 + 벤치마크 + docs/ | 합성 8 → 13 템플릿 확장 |
| 8. 결합위험도 + k-익명성 | ✅ 완료 | analytics/ + PNU 추가 | 「비식별 조치 가이드라인」 대응 |
| **9. 실데이터 평가 + 룰 정제** | ✅ **본 세션** | KDPII + KLUE-NER + fp_collector | F1 0.412 → **0.699** |

**누적 수치 (2026-05-21):**
- PII 카테고리 22종
- 테스트 **699개**, ~2초 (Python 3.13)
- 코어 dependencies **0개**
- 합성 코퍼스 **13 템플릿** (이전 6→ 풍부화) F1 ~0.85 (회귀 감지)
- **KDPII 53,778 문서 micro F1 = 0.699** (PERSON 풀네임만 기준)
- **공공 문서 본문 산문 (메인 도메인) F1 ≈ 0.83**
- 사전 데이터: 성씨 286, 부처 32, 직급 ~250, 행정구역 ~500 (동 사전 +85),
  학교 사전 ~330 + 약칭 ~60, 전공 ~400, 회사명 ~25, 부서명 ~40,
  국가명 70+, 한국어 어말 형태소 16

## 7. 어디서 멈췄나 / 다음에 할 일 (2026-05-21)

**마지막 큰 작업 (claude/understand-work-status-S4kXM):**
Phase 9 = 실데이터 (KDPII) 평가 + 룰 정제 + 자동 과탐 수집 도구.
모든 변경 GitHub push 완료. 테스트 699 passed.

### 핵심 평가 결과

| 벤치마크 | F1 | 비고 |
|---|---:|---|
| 공공 문서 본문 산문 (메인) | **~0.83** | 12 케이스 직접 측정 |
| 합성 코퍼스 13 템플릿 | 0.85 | 회귀 감지 sanity check |
| KDPII 53,778 (풀네임만) | **0.699** | 일상 대화, 1-2자 별명 제외 |
| KLUE-NER PERSON (풀네임만) | 0.376 | 자연어 신문기사 (PII 데이터셋 아님) |

### 신규 평가 도구
- `src/k_pii/eval/kdpii.py` — KDPII 평가 모듈 (`--person-min-length=3` 기본)
- `src/k_pii/eval/fp_collector.py` — 자동 과탐 어휘 수집 (비식별 텍스트 → common_words 후보)

### 남은 작업 후보

A) **한국 공공 데이터 추가 평가** — *사용자 로컬* 에서만 가능 (클라우드 환경
   호스트 차단). 사용자 Claude Code CLI 로 작업 권장:
   - 판결서 인터넷열람 (scourt.go.kr) — 비식별 후 공개 → 우리 검출 = 모두 과탐 → 일반어 수집
   - 행안부 정부 공문서 AI 학습데이터 (data.go.kr 15125451) — KOGL 라이선스
   - AI Hub 569 행정문서 기계독해 — 60만 건 라벨링됨
   - AI Hub 71694 한국어 SNS (alphagyuu 가 사용한 원본)

   사용법: `python -m k_pii.eval.fp_collector data/verdict.txt --min-freq 2`

   **2026-05-21 로컬 부트스트랩:**
   - Cycle 1 (e02f135): Wikipedia 11편 ≈25K → fp_collector → 46 후보 →
     common_words +50. 같은 코퍼스 freq 2+ 46 → 3 (-93%). 박근혜 4→0 손실.
   - Cycle 2 (de5ddf2): korea.kr 정책브리핑 20편 ≈42K + Wikipedia 결합 →
     49 freq-3+ 후보 → common_words +47. 같은 코퍼스 49 → 2 (-96%). 실인
     이재명(7/7)·이억원(4/4) 보존. 두 단계 합쳐 common_words 누적 +97.

   **사이트별 접근 상태 (참고용):**
   ✓ ko.wikipedia.org, korea.kr — Python urllib 직접
   ✓ casenote.kr / law.go.kr — 도달 가능, HTML 추출기 미완성 (TODO)
   ✓ data.go.kr / 부처 .go.kr — PowerShell 또는 Python urllib (curl 000)
   ✗ aihub.or.kr — WAF 403 (브라우저 세션 필요할 듯)
   ✗ glaw.scourt.go.kr — DNS 미해석

B) **PERSON 룰 추가 정제 (marginal)** — 현재 0.19 → 0.25 가 룰 한계 추정.
   더 올리려면 LLM hybrid (`[ml]` extras) 필수. 권장 안 함 (공공 도메인은 이미 0.83).

C) **POSITION 단독 호칭 정책 옵션** — KDPII 따라 "선생/교수" 단독 거부할 수
   있는 옵션 `position_standalone=False` 추가. 현재는 정책 유지가 가이드라인 부합.

D) **모델 학습 + LLM hybrid 디플로이** — 사용자 도메인 확장 시:
   - KLUEBERT-CRF 같은 BERT 학습 (KDPII 데이터로)
   - [ml] / [presidio] extras 통합 (이미 인프라 있음)

E) **사용자 직접 평가 셋 (수기 라벨링)** — 공공 문서 50~100건. 사용자 시간 필요.

### 본 세션 산출물

- 보고서: `docs/EVALUATION_REPORT.md`, `docs/kdpii_evaluation_report.md`,
  `docs/domain_fit_report.md`
- 시각화: `docs/kdpii_visual_compare.html` (100 문서 정탐/과탐/미탐 시각)
- 코드 추가: `eval/kdpii.py`, `eval/fp_collector.py`,
  `dictionaries/districts.py` (동 사전 +85 / COUNTRIES 70+),
  `dictionaries/majors.py` (학과 +70), `patterns/person.py` (한국어 어말 사전)
- 합성 코퍼스 8 → 13 템플릿 + 풀 100+ 이름

### 환경 제약 메모
- 본 세션은 클라우드 컨테이너 (claude.ai/code) 에서 작동
- 모든 한국 정부 사이트 (data.go.kr / scourt.go.kr / aihub.or.kr / law.go.kr 등)
  HTTP 403 (host_not_in_allowlist)
- HuggingFace / arxiv pdf 도 차단
- 데이터 다운로드는 *사용자 로컬 Claude Code* 또는 *채팅 첨부* 로만 가능

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
