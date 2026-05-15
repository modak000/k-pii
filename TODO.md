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
- [ ] **IPv6** — IPv4 이후 추가
- [ ] **PHONE 국제 형식** — +82 / 0082 prefix 지원
- [ ] **ADDRESS 지번** — 동·읍·면·리 + 번지 형식
- [ ] **ADDRESS 행정구역 사전 통합** — 행안부 표준 데이터로 정확도 향상
- [ ] **ACCOUNT 은행별 포맷 검증** — KB/우리/신한/농협/하나/카카오/토스 등
- [ ] **FAX** — 팩스번호 (전화와 분리)

## Phase 3 — 컨텍스트 기반 이름 탐지 (핵심)

- [ ] 사전 구축
  - [ ] 한국 성씨 286개
  - [ ] 일반 직책·호칭 (100+)
  - [ ] 공무원 직책 (200+)
  - [ ] 부처·기관·청 (500+)
  - [ ] 공문서 필드 라벨 ("성명:", "신청인", "기안" 등 50+)
  - [ ] 행정구역 (시·도·구·군·동)
  - [ ] 일반 단어 사전 — FP 방지 (1000+)
  - [ ] 지명 사전 — FP 방지
- [ ] 한국어 조사 처리 (이/가/은/는/을/를/에/에게/한테/께서/의)
- [ ] 이름 후보 추출 (한국어 2~4글자 + 성씨 매칭)
- [ ] 컨텍스트 점수 시스템 — 직책 인접, 필드 라벨, 결정적 PII 인접, 조사 단서, FP 부정 단서 등
- [ ] 누적 사전 `NameDictionary` — 문서 내 첫 확정 → 이후 등장 부스트
- [ ] 통합 처리 흐름: 결정적 PII → 컨텍스트 시드 → 본문 스캔 → 사전 재스캔

## Phase 4 — 도메인 특화 룰

- [ ] `domain/government.py` — 결재서, 보고서, 회의록, 협조 공문 패턴
- [ ] `domain/civil_petition.py` — 민원 신청·답변·정보공개 양식
- [ ] `domain/hr.py` — 이력서, 인사 평가서, 인사 카드
- [ ] `domain/medical.py` (선택) — KCD 진단코드, EDI 약품코드 사전

## Phase 5 — Vault + 처리 모드 + 일반화

- [ ] `vault/reversible.py` — `ReversibleVault`, `VaultEntry` (JSON 스키마 v1)
- [ ] `modes/tokenize.py` — 가역 가명화 (`<PERSON_1>`, `<RRN_1>` 등 토큰)
- [ ] `modes/redact.py` — 비가역 마스킹 (`[성명]`, `***`)
- [ ] `modes/hashed.py` — 단방향 해시 (salt + 일관성 유지)
- [ ] `generalization/` — 연령(10대→30대), 날짜(연 단위), 주소(시 단위), 직업(범주)

## Phase 6 — 법적 매핑 + 위험도 + 리포팅

- [ ] `legal/mapping.py` — PII 카테고리 ↔ 개인정보보호법 조항 매핑 표 일원화
- [ ] `core/modes.py` — `ProcessingMode` (PARANOID/STRICT/BALANCED/PERMISSIVE/AUDIT)
- [ ] 통합 `Anonymizer` 클래스 — 임계값 + 차단/검토 결정 + 처리 모드 적용
- [ ] `reporting/summary.py` — by_risk, by_action, by_legal_basis 요약
- [ ] `reporting/certificate.py` — 처리 증명서 생성 (감사용)
- [ ] CLI (`k_pii/cli.py`) — `k-pii input.txt --mode strict --vault vault.json`

## Phase 7 — 평가 & 문서화

- [ ] 합성 공문서 생성기 (Faker ko_KR + 템플릿)
- [ ] 정확도 벤치마크 — 카테고리별 Precision / Recall / F1
- [ ] `docs/legal_mapping.md` — 모든 PII × 법조항 표
- [ ] `docs/risk_levels.md` — 위험도 정의 및 사례
- [ ] `docs/coverage.md` — 어떤 문서 유형 / PII 어디까지 커버하는지

## 도메인 판단이 필요한 보류 항목

- [ ] **운전면허 체크섬 알고리즘** — 도로교통공단 공식 비공개. 사내 자료/실측으로 확보 시 추가.
- [ ] **사업자번호 위험도 분기** — 법인은 LOW, 개인사업자는 HIGH로 자동 분기할지 (사업자 유형 판단 로직 필요)
- [ ] **법인번호 처리 기준** — 비식별 가이드라인상 법인 정보 보호 수준 명확화 필요
- [ ] **공문서 필드 라벨 사전 큐레이션** — 본인 실무 데이터 샘플 필요
- [ ] **공무원 직책 사전 세분화 수준** — 부처별로 어디까지 나눌지
- [ ] **의료 도메인 포함 여부** — Phase 1 마무리 후 별도 결정
