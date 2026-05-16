# OpenAI Privacy Filter 연계 가이드

[OpenAI Privacy Filter](https://huggingface.co/openai/privacy-filter)
(Apache-2.0, 2026-04-22) 는 1.5B params 의 다국어 PII 검출 ML 모델이다.
**k-pii 와 보완성이 강함** — 두 도구를 함께 쓰면 한국 공공 PII 검출의 *룰
기반 한계* 를 ML 자연어 강점으로 보강할 수 있다.

## 빠른 시작

### 설치

```bash
# k-pii 기본 (룰만, ML 없음)
pip install k-pii

# Privacy Filter 어댑터 추가 — ML 의존성 옵션
pip install k-pii[ml]
```

`[ml]` extras 는 `transformers>=4.40`, `torch>=2.0` 을 설치한다. 코어 k-pii 는
여전히 의존성 0개. GPU 없이도 CPU 추론 가능 (작은 배치 권장).

### 가장 간단한 사용

```python
from k_pii import Anonymizer, ProcessingMode, get_privacy_filter_adapter

# Privacy Filter 어댑터 — 첫 호출 시 모델 다운로드 (~3GB)
pf = get_privacy_filter_adapter(device="cpu")  # 또는 "cuda" / "mps"

# Hybrid Anonymizer — k-pii (룰) + Privacy Filter (ML)
anon = Anonymizer(
    mode=ProcessingMode.STRICT,
    strategy="tokenize",
    secondary_detector=pf,
    merge_mode="union",  # 두 결과 합산
)

text = "신청인 홍길동(880101-1234568) 연락처 010-1234-5678, " \
       "민원 내용: 김기덕 감독님께서 제출한 자료에 오류가 있다고 봅니다."

result = anon.process(text)
print(result.text)
# 신청인 <PERSON_1>(<RRN_1>) 연락처 <PHONE_1>, 민원 내용: <PERSON_2> ...
```

## 4가지 병합 모드

### 1. `union` (기본)
양쪽 검출 결과를 *합산*. overlap 시 위험도 높은 쪽 우선. 가장 일반적.

```python
anon = Anonymizer(secondary_detector=pf, merge_mode="union")
```

**장점:** Recall ↑ (한 쪽이 놓친 것도 catch)
**적합:** 표준 운영 환경

### 2. `intersection`
양쪽 *모두* 잡은 것만 인정. high-confidence detection.

```python
anon = Anonymizer(secondary_detector=pf, merge_mode="intersection")
```

**장점:** Precision ↑↑ (FP 거의 0)
**적합:** 엄격한 컴플라이언스 환경 (의료·금융 등)

### 3. `cross_validation`
양쪽 합산하되, *한 쪽만 잡은 것* 은 신뢰도 페널티.

```python
anon = Anonymizer(secondary_detector=pf, merge_mode="cross_validation")
```

**장점:** Recall + 신뢰도 등급 분리
**적합:** 검토 큐 워크플로우 (사람이 한 쪽만 검출된 것 우선 검토)

### 4. `enrich_primary`
k-pii 결과 우선, Privacy Filter 는 *놓친 영역만* 보강.

```python
anon = Anonymizer(secondary_detector=pf, merge_mode="enrich_primary")
```

**장점:** k-pii 의 *법적 매핑·도메인 컨텍스트* 보존
**적합:** k-pii 가 잘하는 부분 (RRN·결정적 PII) 위주 + 자연어 보강

## 시나리오별 권장

### 시나리오 A: 공공기관 내부 — *컴플라이언스 우선*
```python
anon = Anonymizer(
    mode=ProcessingMode.STRICT,
    strategy="tokenize",
    secondary_detector=pf,
    merge_mode="cross_validation",
)
```
- 양쪽 합의된 검출 → 자동 가명화
- 한 쪽만 → REVIEW 큐 (사람 검토)
- 감사 추적·법적 근거 모두 보존

### 시나리오 B: LLM 호출 전 안전 필터 — *recall 우선*
```python
anon = Anonymizer(
    mode=ProcessingMode.PARANOID,  # 낮은 위험도도 차단
    strategy="redact",
    secondary_detector=pf,
    merge_mode="union",
)
clean_text = anon.process(user_input).text
# clean_text → GPT-4 / Claude / Gemini API 안전 전송
```

### 시나리오 C: 빅데이터 일괄 처리 — *속도 vs 정확도*
```python
# 1차: k-pii (빠름, 결정적) 만으로 처리
fast = Anonymizer(strategy="tokenize")

# 2차: REVIEW 큐의 항목만 PF 로 재평가 (느림, 정확)
slow = Anonymizer(secondary_detector=pf, merge_mode="enrich_primary")
```

## 한국어 성능 예상

Privacy Filter 모델 카드에 따르면:
- 영어: F1 96.5% (PII-Masking-300k)
- 일본어: F1 88.1% (multilingual eval)
- 한국어: *정확한 수치 미공개* — 일본어와 비슷한 수준 추정

k-pii 단독 KLUE-NER Korean-only F1 = 0.331. 두 도구 union 시 예상:
- **F1 0.7-0.8 수준 도달 가능** (검증은 GPU 환경 필요)
- 결정적 PII (체크섬) 는 k-pii 가 압도적
- 자연어 인명은 Privacy Filter 가 압도적

## ⚠️ 주의사항

1. **모델 라이센스 확인** — Apache-2.0 (상용 OK). 다만 OpenAI 데이터셋 약관도 확인.
2. **로컬 실행** — 모델 호출은 *외부 API 가 아님*. 데이터 외부 유출 없음.
3. **첫 다운로드 ~3GB** — 인터넷 연결 필요. 이후 캐시.
4. **GPU 없으면 느림** — CPU 추론 시 문서 한 건당 수 초. 대량 처리 시 GPU 권장.
5. **법적 근거 자동 부여 X** — Privacy Filter 출력은 *PII 라벨* 만. k-pii 가
   결합 처리에서 법적 근거를 부여.
6. **결정성 차이** — k-pii 룰은 결정성 보장, ML 모델은 모델 버전·환경에 따라
   미세 차이. 감사 추적 시 모델 버전 기록 필요.

## 평가 비교 (벤치마크)

```bash
# k-pii 단독
python -m k_pii.eval.klue_benchmark klue-ner-v1.1_dev.tsv --korean-only

# k-pii + Privacy Filter 합산 (사용자가 직접 코드로 실행)
# (CLI 옵션은 향후 추가 예정)
```

## 데이터 출처

- [openai/privacy-filter (Hugging Face)](https://huggingface.co/openai/privacy-filter)
- [OpenAI Privacy Filter Model Card](https://cdn.openai.com/pdf/c66281ed-b638-456a-8ce1-97e9f5264a90/OpenAI-Privacy-Filter-Model-Card.pdf)
- [GitHub: openai/privacy-filter](https://github.com/openai/privacy-filter)
