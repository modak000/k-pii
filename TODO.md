# Roadmap

> Phase별 진행 현황. ✅ = main 머지 완료, ☐ = 미착수, 🟡 = 부분 진행.

## Phase 1 — 결정적 PII (체크섬 기반)

- [x] **RRN** — 주민등록번호 + 체크섬, 한국인 전용 (gender 1·2·3·4·9·0). 후-2020 무작위화 대응 (confidence 0.7)
- [x] **FRN** — 외국인등록번호 (gender 5·6·7·8), RRN과 동일 체크섬
- [x] **BUSINESS_REG** — 사업자번호 (10자리) + 국세청 가중합 체크섬
- [x] **CORP_REG** — 법인번호 (13자리) + Luhn-like 체크섬, RRN과 충돌 시 RRN 우선
- [x] **DRIVER_LICENSE** — 운전면허번호 (12자리) + 지방청 코드(11~28) 검증 (체크섬 미공개)
- [x] **PASSPORT** — 여권번호 (1-2자 prefix + 8자리, 체크섬 미공개; confidence 0.9)
- [x] **CARD** — 신용카드 번호 + Luhn (13~19자리, 하이픈/스페이스 분리자 지원)
- [x] **MEDICAL_INSURANCE** — 건강보험증 번호 (11자리, 키워드 25자 윈도우 컨텍스트)

## Phase 2 — 비검증 PII (정규식 + 컨텍스트)

- [x] **PHONE** — 휴대(010~019) + 일반(02/031~064) + 070 VoIP, 4가지 분리자
- [x] **EMAIL** — RFC 5322 실용 부분집합 (연속 점 거부 등)
- [x] **POSTAL_CODE** — 5자리(키워드 필수) + 6자리(레거시 하이픈)
- [x] **IP** — IPv4 (옥텟 0~255)
- [x] **VEHICLE** — 신형 NN(N)[가-힣]NNNN
- [x] **URL** — http(s) (INFO 수준)
- [x] **ADDRESS** — 도로명 (시·도/구·군 prefix 또는 "주소" anchor) 베이스라인
- [x] **ACCOUNT** — "계좌" 키워드 anchor (10~16자리) 베이스라인
- [x] **IPv6** — RFC 4291 (단축/IPv4-mapped 포함, ipaddress 표준 라이브러리 검증)
- [x] **PHONE 국제 형식** — +82 / 0082 prefix 지원
- [x] **ADDRESS 지번** — 동·읍·면·리 + 번지 형식
- [ ] **ADDRESS 행정구역 사전 통합** — 행안부 표준 데이터로 정확도 향상
- [ ] **ACCOUNT 은행별 포맷 검증** — KB/우리/신한/농협/하나/카카오/토스 등
- [x] **FAX** — 팩스번호 (키워드 anchor: 팩스/FAX/전송)

## Phase 3 — 컨텍스트 기반 이름 탐지 (핵심) — ✅ 베이스라인 완료

- [x] 사전 구축 (시드 — 사용자 도메인 큐레이션 필요)
  - [x] 한국 성씨 140+ (합성성씨 포함)
  - [x] 일반 직책·호칭 + 공무원 직책 (`titles.py`, `titles_gov`)
  - [x] 부처·기관·청·지자체 (`agencies.py`)
  - [x] 공문서 필드 라벨 (`field_labels.py`)
  - [x] 일반 단어 사전 — FP 방지 (`common_words.py` 시드)
- [x] 한국어 조사 처리 (`context/particles.py`)
- [x] 이름 후보 추출 (한국어 2~4글자 + 성씨 매칭)
- [x] 컨텍스트 점수 시스템 — 직책 인접/필드 라벨/결정적 PII 인접/조사 단서/FP 부정 단서/누적 사전 부스트
- [x] 누적 사전 `NameDictionary` — 문서 내 첫 확정 → 이후 등장 부스트
- [x] 통합 처리 흐름: 결정적 PII 위치 마커 → 점수 계산 → Pass A 시드 → Pass B 재스캔

**보강 TODO (Phase 3.1):**
- [x] 성씨 사전 286개 풀로 확장 (통계청 인구주택총조사 기준)
- [x] 공무원 직책 사전 — 일반직 1~9급 + 경찰·소방·군·외무·검사·법관 모두 수록
- [x] 부처/청/처/위원회 사전 — 정부조직법 19부6처18청6위원회 + 2026 개편 + 약칭
- [x] 행정구역 사전 — 17광역 + 226기초자치단체 (자치시·군·구 전체)
- [x] 공문서 필드 라벨 — 행정/수사/소방/인사 도메인 확장
- [ ] 점수표 가중치 평가셋 기반 튜닝 (실데이터 확보 후)

## Phase 4 — 도메인 특화 룰 — ✅ 베이스라인 완료

- [x] `domain/government.py` — 정부 문서번호 (DOC_ID)
- [x] `domain/civil_petition.py` — 민원/정보공개 번호 (PETITION_ID)
- [x] `domain/hr.py` — 사번/공무원번호/교번 (EMPLOYEE_ID, 키워드 anchor)
- [ ] `domain/medical.py` (선택) — KCD 진단코드, EDI 약품코드 사전 (사용자 도메인 입력 대기)

**보강 TODO (Phase 4.1):**
- [ ] 결재라인 (기안/검토/협조/결재) 라벨링 — person.py 점수 부스트 룰
- [ ] 민원 양식 구조화 표 파싱 — 현재 평문 가정
- [ ] 이력서 자유 텍스트의 재직기간/학교명 — 사용자 도메인 입력 필요

## Phase 5 — Vault + 처리 모드 + 일반화 ✅

- [x] `vault/reversible.py` — `ReversibleVault`, `VaultEntry` (JSON 스키마 v1)
- [x] `modes/tokenize.py` — 가역 가명화 (`<PERSON_1>`, `<RRN_1>` 등 토큰)
- [x] `modes/redact.py` — 비가역 마스킹 (`[성명]`, `***`) + asterisk/fixed 스타일
- [x] `modes/hashed.py` — 단방향 해시 (salt + SHA-256, digest_len 조절)
- [x] `generalization/` — 연령(10대→30대), 날짜(year/month/decade), 주소(시·도/시·군·구), 직업(범주)

## Phase 6 — 법적 매핑 + 위험도 + 리포팅 ✅

- [x] `legal/mapping.py` — PII 카테고리 ↔ 개인정보보호법 조항 매핑 표 일원화
- [x] `core/modes.py` — `ProcessingMode` (PARANOID/STRICT/BALANCED/PERMISSIVE/AUDIT) + Action
- [x] 통합 `Anonymizer` 클래스 — 임계값 + 차단/검토 결정 + 처리 모드 적용
- [x] `reporting/summary.py` — by_risk, by_action, by_legal_basis 요약 + 텍스트/JSON 포맷
- [x] `reporting/certificate.py` — 처리 증명서 생성 (감사용)
- [x] CLI (`k_pii/cli.py`) — `k-pii input.txt --mode strict --vault vault.json --strategy tokenize`

## Phase 7 — 평가 & 문서화 — ✅ 베이스라인 완료

- [x] 합성 공문서 생성기 — `eval/synth.py` (Faker 불사용, 표준 라이브러리 random)
  - 템플릿 4종: gov_decree, civil_petition, hr_review, meeting_minutes
- [x] 정확도 벤치마크 — `eval/metrics.py` (Precision/Recall/F1, partial/strict 매칭)
  - 50문서 × 4 seed 코퍼스에서 **micro F1 = 1.000** 달성
  - CLI: `python -m k_pii.eval.benchmark -n 50 --seed 0`
- [x] `docs/legal_mapping.md` — 모든 PII × 법조항 표
- [x] `docs/risk_levels.md` — 위험도 정의 및 사례
- [x] `docs/coverage.md` — 어떤 문서 유형 / PII 어디까지 커버하는지

**보강 TODO (Phase 7.1):**
- [ ] 실제 익명화된 공공 문서로 벤치마크 (사용자 샘플 필요)
- [ ] 합성 템플릿 다양화 (보고서·협조공문·이력서 자유 텍스트)
- [ ] 점수 임계값 튜닝 자동화 (grid search)

## 도메인 판단이 필요한 보류 항목

- [ ] **운전면허 체크섬 알고리즘** — 도로교통공단 공식 비공개. 사내 자료/실측으로 확보 시 추가.
- [ ] **사업자번호 위험도 분기** — 법인은 LOW, 개인사업자는 HIGH로 자동 분기할지 (사업자 유형 판단 로직 필요)
- [ ] **법인번호 처리 기준** — 비식별 가이드라인상 법인 정보 보호 수준 명확화 필요
- [ ] **공문서 필드 라벨 사전 큐레이션** — 본인 실무 데이터 샘플 필요
- [ ] **공무원 직책 사전 세분화 수준** — 부처별로 어디까지 나눌지
- [ ] **의료 도메인 포함 여부** — Phase 1 마무리 후 별도 결정
