# k-pii

한국 공공 부문 문서를 위한 규칙 기반 개인정보(PII) 비식별 라이브러리.

> **상태:** Phase 1~7 베이스라인 완료 (PII 21종 + Vault + Anonymizer + 도메인 룰 + 평가·문서화).
> 합성 코퍼스 6 템플릿 × 60문서 × 5 seed = **300문서에서 micro F1 = 1.000**.
> 공개 데이터 기반 사전 (정부조직 약칭 규칙, 행정구역 표준코드, 공무원 직급 체계) 통합.
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
- `domain/hr.py` — 사번·공무원번호·교번 (EMPLOYEE_ID, 키워드 anchor)

### Phase 7 — 평가 + 문서화 ✅ 베이스라인

- `eval/synth.py` — 합성 공문서 생성기 (4 템플릿, Faker 불사용)
- `eval/metrics.py` — Precision/Recall/F1 (partial/strict 매칭)
- `eval/benchmark.py` — `python -m k_pii.eval.benchmark -n 50` 으로 즉시 평가
- `docs/{legal_mapping,risk_levels,coverage}.md` — 법조항·위험도·커버리지 문서

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
pip install -e ".[dev]"
pytest -v
# 427 passed in ~0.4s
python -m k_pii.eval.benchmark -n 60 --seed 0
# 합성 코퍼스에서 라벨별 P/R/F1 출력 (현재 모든 라벨 F1=1.000)
```

## 라이선스

Apache License 2.0.

## 법적 참고 문서

- 개인정보보호법 (특히 제23조 민감정보, 제24조 고유식별정보, 제28조의2~5 가명정보 특례)
- 개인정보보호위원회 「가명정보 처리 가이드라인」
- 개인정보보호위원회 「개인정보 비식별 조치 가이드라인」
