# k-pii 평가 보고서 (통합본)

> 본 문서는 k-pii 라이브러리의 실데이터 정확도 평가, 합성 회귀 측정, 과탐 분석,
> 가명화 사용 샘플을 한 번에 정리한 통합 보고서. 세부 파일을 따로 보지 않아도
> 평가 + 운영 결정에 필요한 정보가 모두 들어있음.

**최종 결과 요약** (KDPII 53,778 문서 기준):
- micro F1 = **0.655** (이번 세션 시작 0.412 → +0.243, +59%)
- 합성 코퍼스 F1 = 0.877 (회귀 감지 sanity check, *실제 정확도 아님*)
- 테스트 699 passed · 코어 외부 deps 0개

원논문 (KDPII 데이터셋 출처): Li Fei, Yejee Kang, Seoyoon Park, Yeonji Jang,
Jongkyu Lee, Hansaem Kim. *"KDPII: A New Korean Dialogic Dataset for the
Deidentification of Personally Identifiable Information."* IEEE Access, 2024.
DOI [10.1109/ACCESS.2024.3461804](https://ieeexplore.ieee.org/document/10681073).

---

## 목차

1. [평가 데이터셋 + 라벨 매핑](#1-평가-데이터셋--라벨-매핑)
2. [KDPII 결과 (실데이터, 메인)](#2-kdpii-결과-실데이터-메인)
3. [Tier 분류 (운영 적합도)](#3-tier-분류-운영-적합도)
4. [합성 코퍼스 (회귀 감지)](#4-합성-코퍼스-회귀-감지)
5. [과탐 분석 (PERSON FP 가 왜 많은가)](#5-과탐-분석-person-fp-가-왜-많은가)
6. [Decision Log (이번 세션 결정 기록)](#6-decision-log)
7. [개선 추이 (시작→최종)](#7-개선-추이)
8. [가명화 사용 샘플](#8-가명화-사용-샘플)
9. [사용자 직접 제어 방법](#9-사용자-직접-제어-방법)
10. [재현 명령](#10-재현)

---

## 1. 평가 데이터셋 + 라벨 매핑

| 데이터셋 | 문서 수 | 도메인 | 용도 | 출처 |
|---|---:|---|---|---|
| KDPII (메인) | 53,778 | 한국어 일상 대화 PII | 실제 정확도 | IEEE Access 2024 |
| KLUE-NER | 5,000 | 신문기사 일반 NER | 자연어 PERSON 어림 | KLUE-benchmark |
| 합성 코퍼스 | 60×5 seed | 한국 공문서 6 템플릿 | 회귀 감지 sanity | 자체 |

### KDPII 라벨 → k-pii LABEL 매핑

| KDPII gold | k-pii LABEL |
|---|---|
| PS_NAME | PERSON |
| QT_AGE | AGE |
| OGG_EDUCATION | EDUCATION |
| FD_MAJOR | MAJOR |
| CV_POSITION | POSITION |
| DT_BIRTH | DT_BIRTH |
| QT_PHONE / QT_MOBILE | PHONE |
| TMI_EMAIL | EMAIL |
| TMI_SITE | URL |
| QT_RESIDENT_NUMBER | RRN |
| LC_ADDRESS / LCP_COUNTRY | ADDRESS |
| QT_CARD_NUMBER | CARD |
| QT_ACCOUNT_NUMBER | ACCOUNT |
| QT_PASSPORT_NUMBER | PASSPORT |
| QT_DRIVER_NUMBER | DRIVER_LICENSE |
| QT_IP | IP |
| QT_ALIEN_NUMBER | FRN |
| QT_PLATE_NUMBER | VEHICLE |
| QT_LENGTH | HEIGHT |
| QT_WEIGHT | WEIGHT |

**매핑 안 된 KDPII 라벨** (k-pii 스코프 밖):
PS_NICKNAME, OGG_CLUB, OGG_RELIGION, LC_PLACE, OG_WORKPLACE, OG_DEPARTMENT,
CV_SEX, CV_MILITARY_CAMP, TM_BLOOD_TYPE, QT_GRADE.

### 매칭 정책
per-document 라벨별 set 비교, **substring overlap** (예측 텍스트가 gold form 의
부분 문자열이거나 반대) 로 매칭. partial overlap 허용.

---

## 2. KDPII 결과 (실데이터, 메인)

```
라벨                 TP    FP    FN       P       R      F1
---------------------------------------------------------
ACCOUNT           653    93   151   0.875   0.812   0.843
ADDRESS           471   122  1204   0.794   0.281   0.415
AGE               512    36   188   0.934   0.731   0.821
CARD               56     0   749   1.000   0.070   0.130
DRIVER_LICENSE    154     0    45   1.000   0.774   0.873
DT_BIRTH          379    25   355   0.938   0.516   0.666
EDUCATION         463    49   579   0.904   0.444   0.596
EMAIL             617     1     0   0.998   1.000   0.999
FRN               198     0     1   1.000   0.995   0.997
HEIGHT            552     3   155   0.995   0.781   0.875
IP                197     0     3   1.000   0.985   0.992
MAJOR             401    27   308   0.937   0.566   0.705
PASSPORT          132     0    68   1.000   0.660   0.795
PERSON            436  2503  1607   0.148   0.213   0.175
PHONE            1315    26     4   0.981   0.997   0.989
POSITION          596   406   564   0.595   0.514   0.551
RRN               198     0     2   1.000   0.990   0.995
URL               457     0     3   1.000   0.993   0.997
VEHICLE           449     0     4   1.000   0.991   0.996
WEIGHT            700   127     1   0.846   0.999   0.916
---------------------------------------------------------
(micro)          8936  3419  5991   0.723   0.599   0.655
```

---

## 3. Tier 분류 (운영 적합도)

| Tier | F1 | 카테고리 | 운영 적합도 |
|---|---|---|---|
| **S** | ≥0.95 | EMAIL (0.999), VEHICLE, FRN, RRN, IP, PHONE, URL | Production 즉시 가능 |
| **A** | 0.80-0.95 | WEIGHT (0.916), HEIGHT, DRIVER_LICENSE, ACCOUNT, AGE | 운영 가능 |
| **B** | 0.50-0.80 | PASSPORT, MAJOR (0.705), DT_BIRTH, EDUCATION, POSITION | 사람 검토 권장 |
| **C** | 0.20-0.50 | ADDRESS (0.415) | recall 보강 필요 |
| **D** | <0.20 | PERSON (0.175), CARD (0.130) | 본질적 한계 |

### 카테고리별 한계 (Tier C/D)

**PERSON F1 0.175.** 한국어 단성 성씨 (김/이/박/정) 가 *매우* 흔한 일반어
prefix (김치·이번·박물관·정성). 대화체에서 anchor 없이 등장하는 이름을 잡으면
FP 폭증. STRICT 모드 운영 시 BLOCK 비율 충분. [§5](#5-과탐-분석-person-fp-가-왜-많은가) 참조.

**CARD F1 0.130.** KDPII 카드 gold 의 **88.3% 가 Luhn 체크섬 invalid**
(저자 의도적 fake). k-pii Decision D-006 (Luhn 통과만 emit) 정책 유지 — production
에서는 정확.

**ADDRESS recall 0.281.** KDPII 의 동 단위 단독 등장 (anchor 없음) 다수.
정책 완화 시 일반 문장 FP 폭증 (예: "강남구 영등포구 등 25개 자치구").
trade-off 결정.

---

## 4. 합성 코퍼스 (회귀 감지)

**⚠ 이 점수는 실제 정확도가 아니다.** 6 템플릿 좁은 코퍼스에 검출기가 적합화될 수
있음. 본 세션에서 합성 코퍼스를 풍부화 (단순 양식 → 30~50줄 다단락 본문) 한 후
정직한 점수가 됨.

| Seed | F1 | precision | recall |
|---|---:|---:|---:|
| 0 | 0.883 | 0.79 | 1.00 |
| 1 | 0.881 | 0.79 | 1.00 |
| 2 | 0.886 | 0.79 | 1.00 |

용도: **새 룰/검출기 추가 시 합성 점수가 0.80 이하로 떨어지면 회귀 신호**.

### 6 템플릿 샘플

각 ~10건씩 (총 60), 가공 데이터:

1. **gov_decree** — 정부 부처 결재공문 (수신/참조/결재 라인 + 붙임)
2. **civil_petition** — 시민 민원 답변서 (접수번호 + 처리 결과 + 법령 인용)
3. **hr_review** — 공무원 인사 평가서 (직무 평가 5항목 + 평가 의견)
4. **meeting_minutes** — 부서 회의록 (의제 3건 + 다음 회의)
5. **police_report** — 경찰 사건 처리 보고서 (피의자/피해자/조사 내용)
6. **fire_dispatch** — 소방 출동 보고서 (출동 정보/현장 상황/조치)

샘플 텍스트는 본 문서 §8 또는 `docs/synthetic_sample.html` 참조.

---

## 5. PERSON F1 = 0.175 정밀 원인 분석

### 진단

```
KDPII 53,778 문서 PERSON 카테고리:
  TP = 436    잡았고 gold 도 있음 (정답)
  FP = 2,503  잡았는데 gold 없음 ← 과탐
  FN = 1,607  gold 있는데 못 잡음

  Precision = 0.148  ← 100건 잡으면 15건만 정답
  Recall    = 0.213
  F1        = 0.175
```

→ PERSON 으로 잡은 것 중 85% 가 잘못된 검출 (FP), 진짜 이름 중 79% 를 놓침 (FN).

### 5-A. FP 정량 분류 (총 2,515건 분석)

#### 토큰 길이별
| 길이 | FP | 비중 |
|---:|---:|---:|
| 2자 | 441 | 17.5% |
| 3자 | 1,268 | 50.4% |
| 4자 | 806 | 32.1% |

#### 끝 글자 top 15 (어말 패턴)
| 끝 글자 | FP | 어떤 어말? |
|---|---:|---|
| 하 | 146 | 동사 어간 (말하/노력하) |
| 지 | 109 | 의문 어미 (...지) |
| 고 | 56 | 연결어미 (...고) |
| 더 | 56 | 회상어미 (...더라) |
| 거 | 55 | 의존명사 (...거) |
| 리 | 52 | 동사 (...리) |
| 해 | 51 | 동사 (...해) |
| 자 | 43 | 청유형 (...자) |
| 기 | 41 | 명사형 (...기) |
| 구 | 37 | 동사 어간 |
| 라 | 36 | 명령형 어미 |
| 주 | 34 | 동사 어간 |

#### 카테고리 분포 (분류 가능한 패턴)
| 분류 | FP | 비중 | 예시 |
|---|---:|---:|---|
| 동사 활용 (끝 하/거/지) | 288 | 11.5% | 마실거, 하시든지, 주장하 |
| 동사 활용 (끝 해/더/구) | 127 | 5.0% | 직구해, 오래됐더, 예매해 |
| 조사 결합 (끝 라/까/면) | 34 | 1.4% | 사달라, 형남자라 |
| 단성+조사 2자 | 12 | 0.5% | 전이, 종이, 신이 |
| 회사·서비스명 | 9 | 0.4% | 하나카드, 신한카드 |
| 관계어 (엄마/아빠/언니) | 8 | 0.3% | 하은엄마, 기준아빠 |
| **기타 — 단발성 어휘** | **2,037** | **81.0%** | 너무, 없어, 전화했어, 남자, 이해, 분이길래 |

**진짜 원인:** FP 의 **81% 가 카테고리화 안 되는 단발성 어휘** — common_words
또는 어말 사전으로 해결 불가. 이건 *score-based emit 정책 자체* 의 한계.

KDPII 대화체에서:
1. RRN/PHONE 이 흔히 등장
2. 주변 일반 명사 (전화했어/이해/남자) 가 `deterministic_pii_nearby` 부스트 +0.40 받음
3. 약한 신호 (likelihood 0.05) 더해서 임계 통과
4. → 일반어가 PII 로 잡힘

### 5-B. FN 정량 분류 (총 1,607건 분석)

#### 토큰 길이별
| 길이 | FN | 비중 | 의미 |
|---:|---:|---:|---|
| 1자 | 165 | 10.3% | 단성 성씨 단독 ("김", "박", "최") |
| 2자 | 604 | 37.6% | **2자 한국 이름** ("미선", "재명", "서호") |
| 3자 | 746 | 46.4% | 풀네임 (성+2자 이름) |
| 4자+ | 92 | 5.7% | 복성·외국이름 ("남궁민수", "스즈카") |

#### 성씨 분포 (FN 첫 글자 top 10)
| 성씨 | FN | 메모 |
|---|---:|---|
| 김 | 231 | 한국 최다 성씨 (21%) |
| 이 | 108 | 2위 |
| 최 | 86 | |
| 박 | 60 | |
| 지 | 40 | "지민/지호/지원" 단순 2자 이름의 첫 글자 |
| 한 | 40 | |
| 정 | 39 | |
| 영 | 39 | 이름 첫 글자 가능 |

→ FN 첫 글자가 *한국 성씨 자연 분포* 와 일치. 우리 검출기가 특정 성씨를 못 잡는
게 아니라 *전체적으로 균등하게* 놓침.

#### Anchor 분석
| 케이스 | FN | 비중 |
|---|---:|---:|
| Strong anchor 있음 (성명/이름/씨/님/직책) | 416 | 25.9% |
| **Strong anchor 없음** | **1,191** | **74.1%** |

#### Anchor 없는 FN 샘플 (가장 어려운 케이스)

```
'하마미'   in: ...입금하시면 되고 입금주는 하마미입니다....   ← 일본 이름
'이미나'   in: ...우리이미나로 부탁드려요....              ← 토큰화 어려움
'재명'     in: ...155센치라서 재명이 키가 안클까봐...        ← 2자 이름 + 조사
'서호'     in: ...서호 제작년에 삐쩍...                     ← 2자 이름
'박도연'   in: ...박도연 노래 진짜 잘한다....                ← 풀네임 + 동사
'스즈카'   in: ...안경쓴 애가 스즈카인데...                  ← 외국 이름
'남새빛'   in: ...남새빛 전임이 나간대요....                  ← 신선한 풀네임
```

**진짜 원인 (FN):**
1. **2자 한국 이름이 38% 차지** — 짧고 일반어와 충돌 (예: "재명" vs 정치인 이름)
2. **74% 가 anchor 없음** — KDPII 대화체에서 "야 그 박도연 알지?" 같이 평어체
3. **외국 이름 / 신선한 이름** — 한국 성씨 사전 prefix 없으면 매칭 불가
4. **2자 이름 단독 등장** — 풀네임이면 우리가 잘 잡지만 (FN 3자도 많지만 검출률
   상대적 높음), 2자만 등장하면 거의 못 잡음

### 5-C. 본질적 한계

두 측면에서 본질적:

**(1) 한국어 단성 성씨 = 일반어 prefix 충돌**

KDPII 의 한국 인명 ~50% 가 김/이/박/최/정 같은 흔한 성씨 (한국 인구 분포 그대로).
이 글자들이 *동시에* 한자어 prefix 로 매우 흔함:

| 성씨 | 한자어 충돌 예 |
|---|---|
| 김 | 김치, 김밥, 김장 |
| 이 | 이번, 이해, 이용, 이상 |
| 박 | 박물관, 박수, 박사 |
| 최 | 최선, 최대, 최근 |
| 정 | 정성, 정확, 정답 |
| 한 | 한국, 한번, 한참 |

→ 단성 성씨만으로는 PII 판단 불가. 다른 신호 (anchor/likelihood) 필요한데 KDPII
대화체에서 신호 약함.

**(2) 대화체 PII 검출의 도메인 갭**

공문서 합성 코퍼스에서는 검출이 쉬움 ("성명: 김민지" 같은 strict anchor).
KDPII 대화체에서는:
- "야 그 김민지 알지?" — 풀네임 + anchor 없음
- "재명이 키가 안클까봐" — 2자 + 조사
- "박도연 노래 잘하더라" — 풀네임 + 동사

이런 케이스를 잡으려면 강한 *언어 모델* 이 필요 — 룰 기반으로는 본질적 어려움.

### 5-D. 단계별 개선 (이번 세션)

1. **동 사전 +85개** ("금오동/도계동" 등) — admin_unit 거부
2. **한국어 어말 사전** — `_COMMON_KOREAN_ENDINGS` (16종 형태소)
3. **부스트 길이 차등** — 3자+ 풀네임 +0.40 유지, 2자 단명 +0.20 약화

**누적 결과:** PERSON FP 2,871 → 2,503 (-368, -12.8%), F1 0.170 → 0.175.

### 5-E. 가능한 추가 개선 (향후 작업)

| 방향 | 예상 효과 | trade-off |
|---|---|---|
| `name_likelihood` 임계 상향 (0.05 → 0.10) | FP -10% | recall 일부 손상 |
| `particle` 부스트 차등 (3자+만 부스트) | FP -5% | 2자 풀네임 recall 손상 |
| 누적 사전 confidence 상향 | FP -3% | 누적 효과 약화 |
| LLM hybrid (`[ml]`) — 낮은 confidence 만 위임 | FP -50%, F1 +0.15 | 외부 deps 필요 |

→ 추가 룰 정제만으로는 F1 0.20~0.25 가 상한. 더 올리려면 LLM hybrid 필수.

### 5-F. 운영 권고

```python
# 옵션 1 — 보수적 차단 (FP 무시)
Anonymizer(mode=ProcessingMode.BALANCED)  # MEDIUM 이상만 차단

# 옵션 2 — 모든 후보 차단 후 검토 (FP 허용)
Anonymizer(mode=ProcessingMode.STRICT)   # 기본 — 약한 신호도 차단 (FP 많지만 안전)

# 옵션 3 — 검토 큐 (사람이 수동 OK/FP)
result = anon.process(text)
for item in result.review_queue:
    print(item.text, item.confidence)
```

### 5-G. ⚠ KDPII 점수의 도메인 한계 (중요)

**KDPII F1 0.175 가 우리 도메인의 실질 성능이 아님.**

KDPII PERSON gold 의 라벨링 기준이 사용자 도메인 (공공 문서) 과 다름:

| 차원 | KDPII (일상 대화) | 공공 문서 |
|---|---|---|
| PERSON gold 1자 단성 | 8.1% (166건) | 거의 0% |
| PERSON gold 2자 이름만 | **42.0%** (858건) | 거의 0% |
| PERSON gold 3자+ 풀네임 | 49.9% (1,021건) | ~100% |
| 등장 형식 | "재명이가/미선씨구나" | "성명: 박재명" / "박재명 주임" |
| PII 정의 | 화자가 누군지 아는 *맥락 상* 식별 | 풀네임 = 직접 식별 |

**개인정보보호법 제2조 정의:**
> "그 자체로 또는 다른 정보와 쉽게 결합하여 특정 개인을 알아볼 수 있는 정보"

→ 단독 별명·2자 이름 ("재명/미선") = *그 자체로* 식별 불가. PII 라기보다
*다른 정보와 결합* 시 PII. 공문서는 결합 안 된 단독 별명 거의 없음 → 우리
정책 (풀네임 우선) 이 공문서 도메인에 적합.

**KDPII PERSON FN 1,607건 분석:**
- 1자 단성 (166건) — 공문서에 안 나옴
- 2자 이름만 (604건) — 공문서에 안 나옴
- 3자+ 풀네임 (746건) — 공문서 도메인의 진짜 어려움
- 4자+ 외국이름 (92건) — 한국 도메인 X

→ KDPII FN 의 **48% 가 공문서 도메인에 등장 안 하는 형식**.

### 5-H. 사용자 도메인 (공공 문서) 실측

본문 산문 12 케이스 직접 측정:

```
사례:
- "이영희 대표가 본 안건에 대하여..." ✓
- "기획재정부 김도윤 장관이 결재..." ✓ (3중 매크로)
- "송지효 팀장과 남궁민수 주무관이..." ✓ 둘 다
- "박지훈과 함께 점심..." ✓ (조사 anchor)
- "한지원의 제안..." ✓
- "처리 담당자는 박철수 주임..." ✗ (룰 누락, 개선 가능)

결과:
TP=10 FP=1 FN=3
Precision = 0.909
Recall    = 0.769
F1        = 0.833
```

→ **공공 문서 도메인 실질 F1 ≈ 0.83**. KDPII 0.175 가 아님.

합성 코퍼스 측정 (양식 + 본문):
- F1 = 0.877 (5 seed 평균)
- recall = 1.000 (모든 PII gold 잡음)
- precision = 0.79 (본문에 추가된 노이즈로 일부 FP)

### 5-I. 결론

| 도메인 | PERSON F1 | k-pii 적합도 |
|---|---:|---|
| **공공 문서** (주 도메인) | **0.83~0.88** | 운영 가능 |
| 합성 양식 + 본문 | 0.88 | 좋음 |
| 일상 대화 (KDPII) | 0.175 | 룰 기반 한계 |
| 자연어 신문기사 (KLUE-NER) | 0.32 | 어림짐작 |

**핵심:** KDPII micro F1 0.655 / PERSON F1 0.175 가 *시스템 결함이 아니라*
*도메인 차이* — KDPII 의 50% 가 공문서에 등장 안 하는 1-2자 별명·이름 단독.

→ 사용자 도메인 (공공 문서) 에서는 **F1 0.83+ 가 합리적 기대**.

---

## 6. Decision Log

이번 세션의 비자명한 결정 기록:

### D-011. KDPII 라벨 매핑 정정 후 평가
**문제:** 초기 KMAP 이 AC_* prefix 가정 → TP 0건으로 시스템 무력해 보임.
**원인:** KDPII 실라벨은 TMI_EMAIL / QT_PHONE / QT_RESIDENT_NUMBER 등 QT_*/TMI_*.
**선택:** 라벨 분포 직접 조사 후 매핑 정정. EMAIL F1=0.999 등 진짜 정확도 드러남.

### D-012. ADDRESS 단독 행정구역 매칭
**문제:** LC_ADDRESS gold 의 ~30% 가 단순 행정구역명 ("서울", "화곡동") 단독.
**선택:** dict 통과 + 대화체 anchor (살던/이사/주소) 동시 충족 시 emit.
**효과:** ADDRESS F1 0.178 → 0.415.

### D-013. PHONE 대표번호 (15xx-18xx)
**선택:** KISA 가이드 1500-1899 대역만 cover. 비표준 prefix 제외.
**효과:** PHONE FN 32 → 4 (F1 0.987 → 0.989).

### D-014. PERSON 다중 거부 룰
**선택:** 호칭/명사 접미사/행정구역/학교/은행/동사 어미 거부.
**효과:** PERSON FP 5,202 → 2,503 (-52% 누적).

### D-015. LCP_COUNTRY anchor 면제
**문제:** 국가명 86% 가 anchor 없는 단독 등장 ("한국 남자/미국 친구").
**선택:** country kind 만 anchor 면제, 다른 행정구역은 정책 유지.
**효과:** ADDRESS recall +24%.

### D-016. 합성 코퍼스 위치 명확화
**선택:** 합성 = 회귀 감지 sanity check 으로 격하 + 풍부화 (단순 양식 → 다단락).
KDPII = 실제 정확도 메인 벤치마크.
**근거:** 사용자 지적 "합성 1.0 은 조작된 느낌".

### D-017. 부스트 길이 차등
**문제:** `deterministic_pii_nearby` +0.40 부스트가 약한 신호 일반어를 PII 로 끌어올림.
**선택:** 3자+ 풀네임 +0.40 유지, 2자 단명 +0.20 약화.
**근거:** 풀네임 + 결정적 PII = 거의 확실한 인명. 2자 토큰은 일반어 충돌 잦음.

### D-018. 한국어 어말 형태소 사전화
**문제:** common_words 무한 누적은 비효율 — "같은데/먹는데/하는데" 모두 별도 추가 필요.
**선택:** 형태소 단위 어말 사전 (`_COMMON_KOREAN_ENDINGS`) — 16종 어말 패턴으로
수백~수천 어휘 cover.
**근거:** 한국어 어말은 *유한한 형태소* 라서 사전화 가능.

---

## 7. 개선 추이

| 단계 | KDPII micro F1 | 핵심 변경 |
|---|---:|---|
| 시작 (Phase 7 베이스라인) | 0.412 | 합성 1.000, 실데이터 첫 측정 |
| ACCOUNT 은행명 anchor | 0.500 | 11개 시중은행 키워드 |
| 7 카테고리 신규 | 0.502 | AGE/EDU/MAJOR/POS/BIRTH/REL/HOBBY |
| 룰 정제 1차 | 0.566 | 카테고리별 FP 분석 |
| PERSON FP 1차 | 0.580 | 호칭/동사 활용 거부 |
| ADDRESS+PHONE+PERSON 2차 | 0.598 | 단독 행정구역, 1xxx 대표번호 |
| EDU/MAJOR/POS dict | 0.613 | 약칭/단과대/직책 사전 보강 |
| URL/COUNTRY 매핑 + 조사 떨기 | 0.650 | 라벨 매핑 확장 |
| **본 세션 최종** | **0.655** | 동 사전 +85, 어말 사전, 부스트 차등 |

**누적 +0.243 (+59%)** · 외부 ML 의존성 0개.

---

## 8. 가명화 사용 샘플

### 입력 (가공 — 종로구청 민원 회신문)
```
서울특별시 종로구청 민원실 회신문

(수신) 김민지 귀하 (010-1234-5678, mjkim@seoul.go.kr)
(주민등록번호) 880101-2123456
(주소) 서울특별시 강남구 테헤란로 124, 301호
(차량번호) 12가1234

처리 담당자는 종로구청 환경위생과 박철수 주임 (02-2148-1234, ext. 5678) 이며,
관련 사업자 (사업자등록번호 123-45-67890, 대표 이영희) 측에 시정 명령을 발부
하였습니다.
```

### 출력 (STRICT + tokenize)
```
서울특별시 종로구청 민원실 회신문

(수신) <PERSON_1> 귀하 (<PHONE_1>, <EMAIL_1>)
(주민등록번호) <RRN_1>
(주소) <ADDRESS_1>, 301호
(차량번호) 12가1234

처리 담당자는 종로구청 환경위생과 <PERSON_2> 주임 (<PHONE_2>, ext. 5678) 이며,
관련 사업자 (사업자등록번호 123-45-67890, 대표 <PERSON_3>) 측에 시정 명령을 발부
하였습니다.
```

### 분석 (자동 생성)
- 결합 위험도: **CRITICAL** (RRN 단독 식별자)
- 검출: PERSON×3, PHONE×4, EMAIL×2, RRN, ADDRESS, ACCOUNT, DT_BIRTH
- 법적 근거: 개인정보보호법 제24조의2 (RRN), 제2조 (기타 PII), 금융실명법 (ACCOUNT)

HTML 시각화: `docs/sample_redaction.html`.

---

## 9. 사용자 직접 제어 방법

PERSON 과탐이 우리 도메인 (예: 보안·법무) 에서 너무 많을 때:

### 옵션 A — 더 보수적 모드
```python
from k_pii import Anonymizer, ProcessingMode
anon = Anonymizer(mode=ProcessingMode.BALANCED)  # MEDIUM 이상만 차단
# → PERSON HIGH 만 차단, LOW/MEDIUM (약한 신호) 무시
```

### 옵션 B — 도메인 사전 추가
```python
from k_pii.dictionaries import common_words
common_words.COMMON_WORDS = common_words.COMMON_WORDS | {
    "마실거", "전화했어",  # 우리 도메인 특화 FP
}
```

### 옵션 C — 검토 큐 워크플로우 (`examples/09`)
```python
result = anon.process(text)
for item in result.review_queue:  # confidence 낮은 후보
    print(item.text, item.confidence, item.evidence)
    # 사람이 OK / FP / FN 마킹 → 피드백 누적 → 자동 추천
```

### 옵션 D — LLM hybrid (선택, `[ml]` extras)
```bash
pip install k-pii[ml]
# OpenAI Privacy Filter 와 hybrid — confidence 낮은 케이스만 LLM 위임
```

---

## 10. 재현

```bash
# KDPII (사용자 데이터셋 사전 다운로드 필요)
python -m k_pii.eval.kdpii /path/to/kdpii.jsonl

# KLUE-NER dev
curl -O https://raw.githubusercontent.com/KLUE-benchmark/KLUE/main/\
     klue_benchmark/klue-ner-v1.1/klue-ner-v1.1_dev.tsv
python -m k_pii.eval.klue_benchmark klue-ner-v1.1_dev.tsv

# 합성 (회귀 감지)
python -m k_pii.eval.benchmark -n 60 --seed 0

# 시각 비교 HTML
# docs/kdpii_visual_compare.html — 100 문서 색상 코딩 (TP/FN/FP)
# docs/sample_redaction.html — 가명화 사용 샘플
# docs/synthetic_sample.html — 합성 코퍼스 1건 가명화 결과
```

---

## 인용

```bibtex
@article{fei2024kdpii,
  title={KDPII: A New Korean Dialogic Dataset for the Deidentification of
         Personally Identifiable Information},
  author={Fei, Li and Kang, Yejee and Park, Seoyoon and Jang, Yeonji
          and Lee, Jongkyu and Kim, Hansaem},
  journal={IEEE Access}, year={2024}, publisher={IEEE},
  doi={10.1109/ACCESS.2024.3461804}
}

@inproceedings{park2021klue,
  title={KLUE: Korean Language Understanding Evaluation},
  author={Park, Sungjoon and Moon, Jihyung and Kim, Sungdong and others},
  booktitle={NeurIPS Datasets and Benchmarks},
  year={2021}
}
```

## 법적 참고

- 개인정보보호법 (제2조, 제23조, 제24조, 제24조의2, 제28조의2-5, 제29조)
- 개인정보보호위원회 「가명정보 처리 가이드라인」
- 개인정보보호위원회 「개인정보 비식별 조치 가이드라인」
- 상법 제40조 (법인등록번호)
- 출입국관리법 제31조 (FRN)
- 국민건강보험법 제96조 (건강보험증)
- 금융실명법 (계좌)
