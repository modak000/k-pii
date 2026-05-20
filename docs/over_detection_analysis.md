# 과탐 분석 보고서 — PERSON FP 가 왜 많은가

> 사용자 지적: *"같은데 [PERSON/FP] 이건 왜 잡힌거지?"*, *"금오동 [PERSON/FP]"*, *"과탐이자나"*.
> KDPII 시각 비교 HTML (`docs/kdpii_visual_compare.html`) 검토 후 PERSON precision 0.145 의
> 원인 분석 + 단계별 개선 결과.

## 1. 출발점 — 과탐 (Over-detection) 진단

```
KDPII 53,778 문서 PERSON 카테고리:
  TP = 437    잡았고 gold 도 있음 (정답)
  FP = 2,871  잡았는데 gold 없음  ← 과탐
  FN = 1,606  gold 있는데 못 잡음

  Precision = 0.145  ← 100건 잡으면 14건만 정답
  Recall    = 0.214
  F1        = 0.170
```

→ **PERSON 으로 잡은 것 중 86% 가 잘못된 검출 (FP).** 시각화에서 빨강이 많이 보이는 이유.

## 2. 원인 분석 — 점수 누적 정책의 약점

PERSON 검출은 **score-based emit** — 여러 약한 신호가 누적되면 임계값 통과.

```python
score = 0
+ surname(이) = 0.15           # 단성 성씨 prefix
+ particle(에) = 0.35          # 조사 부착
+ deterministic_pii_nearby = 0.40  # RRN/PHONE 인접 ← 너무 강한 부스트
+ name_likelihood(0.05) = 0.05
= 0.95 ≥ threshold 0.50 → emit
```

KDPII 대화체에 RRN/PHONE 이 *흔하게* 등장하고, 일반 명사 ("같은데/전화했어/마실거") 가
주변에 있으면 `deterministic_pii_nearby` 부스트 +0.40 으로 끌어올려 PERSON 으로 잡힘.

### FP top 6 evidence 분포 (10k 문서)

| 회수 | Evidence | 예 |
|---:|---|---|
| 293 | `name_likelihood(0.05)` | 너무·없어·마실거 (likelihood 매우 낮은데 emit) |
| 112 | `name_final_syllable` | 순정·하시든지·배민 |
|  96 | `name_likelihood(0.10)` | 분이길래·직구해·경영대 |
|  63 | `particle(는)` | 어릴때·나빠지 |
|  50 | `particle(에)` | 차장때문·우주선 |
|  43 | `deterministic_pii_nearby` | 전화했어·분이길래·하시든지 |
|  32 | `threshold:strict_short` | 이해·치고·인형 |

→ 약한 신호들이 *과도하게 누적* 됨. 한 가지가 강한 게 아니라 여러 0.05~0.10 단서가 합쳐서
임계 통과.

## 3. 단계별 개선 (이번 세션)

### 단계 1 — 동 사전 +85개 (사용자: "금오동")

```
docs/kdpii_visual_compare.html 에서 "금오동 [PERSON/FP]" 발견.
원인: COMMON_DONGS 사전에 "금오동" 누락.
"금" 단성 성씨 + "오동" 조사 매칭으로 PERSON 검출.
```

해결: KDPII LC_ADDRESS gold 직접 분포 분석 → 132개 동 누락 식별 → 85개 사전 추가.
PERSON 의 admin_unit 거부 check 가 즉시 작동.

### 단계 2 — 한국어 어말 사전 (사용자: "같은데")

```
"같은데 [PERSON/FP]" 발견.
원인: "같" 은 성씨 아니지만 결정적 PII 옆 부스트로 임계 통과.
```

해결: 체계적 어말 사전 신규:

```python
_COMMON_KOREAN_ENDINGS = (
    # 연결어미
    "은데", "는데", "라서", "어서", "면서", "다가",
    "지만", "거나", "더라", "더라도", "이라도",
    "도록", "토록", "거든",
    # 종결어미
    "이에요", "예요", "이고", "이며", "이니", "이라",
    "입니다", "이지요",
    # 조사 결합
    "에서", "에게", "한테", "보다", "처럼", "마다", "조차",
    "마저", "부터", "까지", "라고", "이라고",
)
```

3자+ 토큰이 이 어말로 끝나면 PERSON 거부. common_words 누적 아닌 *형태소 사전*.

### 단계 3 — `deterministic_pii_nearby` 부스트 차등

```python
# 기존: 모든 토큰에 +0.40
# 신규: 길이 차등
if deterministic_nearby:
    token_len = cand.end - cand.start
    boost = 0.40 if token_len >= 3 else 0.20  # 2자만 약화
    score += boost
```

**근거:**
- 3자+ 풀네임 ("이순신") + RRN 인접 = 거의 확실한 인명 → 부스트 유지
- 2자 단명 ("같은/마실/전화") + RRN 인접 = 일반 어휘 충돌 잦음 → 부스트 약화

## 4. 결과 누적

| 단계 | PERSON FP | PERSON F1 | micro F1 |
|---|---:|---:|---:|
| 시작 (이전 세션 끝) | 2,871 | 0.170 | 0.650 |
| 동 사전 +85개 | 2,571 | 0.173 | 0.654 |
| 어말 사전 | 2,571 | 0.173 | 0.654 (동시 적용) |
| 부스트 차등 | **2,503** | **0.175** | **0.655** |

**누적: PERSON FP -368 (-12.8%)**, 합성 0.877 유지, 테스트 699 통과.

## 5. 본질적 한계

PERSON F1 이 여전히 0.175 인 이유:

1. **한국어 단성 성씨 = 일반어 prefix** — "김/이/박/최/정" 이 동시에 흔한 한자어
   prefix (김치·이번·박물관·최선·정성). 사전적 분리 불가.

2. **대화체 PII 인식의 본질** — KDPII 같은 일상 대화 도메인은 anchor 가 모호.
   "야 그 김민지 알지?" 같은 텍스트는 PII 인지 모호 (실명? 별명?).
   합성 코퍼스의 "성명: 김민지" 같은 명확한 anchor 와 다른 도메인.

3. **Recall vs Precision trade-off** — recall 올리면 (광범위 매칭) FP 폭증,
   precision 올리면 (보수적) recall 손상. k-pii 는 **PARANOID 모드** 가 광범위
   매칭으로 운영하고 **STRICT 모드** 가 보수.

## 6. 사용자가 *직접* 더 줄이는 방법

```python
from k_pii import Anonymizer, ProcessingMode

# 옵션 A: 더 보수적 모드
anon = Anonymizer(mode=ProcessingMode.BALANCED)  # MEDIUM 이상만 차단
# → PERSON HIGH 만 차단, LOW/MEDIUM (약한 신호) 무시

# 옵션 B: 커스텀 common_words 추가
from k_pii.dictionaries import common_words
common_words.COMMON_WORDS = common_words.COMMON_WORDS | {
    "마실거", "전화했어", "차장때문",  # 도메인 특화 FP
}

# 옵션 C: 검토 큐 워크플로우 (REVIEW 모드)
result = anon.process(text)
for item in result.review_queue:  # confidence 낮은 후보
    print(item.text, item.confidence, item.evidence)
    # 사람이 OK/FP 마킹 → 피드백 누적 → 자동 추천
```

## 7. 향후 작업 후보

1. **`name_likelihood` 임계값 상향** — 현재 0.05 까지 emit. 0.10 미만은 거부 검토.
2. **`particle` 부스트 차등** — `에/는/이/가/야` 같은 흔한 조사는 약하게.
3. **사용자 도메인 사전 외부 입력 API** — 사용자가 직접 도메인 FP 추가하기.
4. **LLM hybrid 모드** — confidence 낮은 경우만 LLM 에 확인 위임 (`[ml]` extras).

## 8. 시각 검증

`docs/kdpii_visual_compare.html` 갱신 — 본 세션 개선 결과 확인 가능 (빨강 FP 감소).

100 문서 샘플 F1 변화: 0.726 → **0.737** (전체 0.650 → 0.655 와 비례).
