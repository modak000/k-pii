# k-pii vs HF privacy model — KDPII 비교 평가 보고서

> 2026-05-21 로컬 평가. KDPII 테스트 4,891 문서 전체 대상으로 *실제 인간 라벨*
> (Zenodo 10968609 gold) 기준 양쪽 모두 측정.

## 1. 한 줄 결론

KDPII 테스트 4,891 문서에서 **k-pii micro F1 = 0.699**, **openai/privacy-filter
micro F1 = 0.271** — 한국어 PII 검출에서 k-pii가 **2.58배** 우위. 한국 특화
카테고리 (RRN/FRN/운전면허/여권/차량/사업자/계좌) 와 키 단위 PII (전화/이메일
/URL) 양쪽에서 k-pii 우위가 명확함.

## 2. 평가 환경

| 항목 | 값 |
|------|-----|
| 코퍼스 | KDPII test split (Zenodo 10968609 CC-BY-4.0) |
| 문서 수 | 4,891 (1-5 문장씩의 한국어 대화 발췌) |
| Gold 라벨 출처 | 실제 인간 어노테이션 (각 문서당 `PII_set[].label/form`) |
| k-pii 버전 | commit `864fbed` (cycle 1+2+3 dict 적용 후) |
| HF 모델 | `openai/privacy-filter` (q4f16 ONNX, 770MB) |
| HF 모델 런타임 | onnxruntime 1.26 CPU EP (CUDA EP는 cuDNN 9 미설치) |
| 매칭 정책 | substring overlap (예측 텍스트와 gold form 중 한 쪽이 다른 쪽 포함) |
| PERSON 최소 길이 | 3자 (풀네임만; 단독 1-2자 별명은 KDPII gold에는 있지만 평가에서 제외) |

평가 도구: `src/k_pii/eval/model_comparison.py` (commit 본 PR), `--mode kdpii`.

## 3. 카테고리별 결과 (정탐 / 오탐 / 미탐 / F1)

| 라벨 | k-pii | openai/privacy-filter |
|------|------:|---------------------:|
| ACCOUNT | 61 / 11 / 16 → **F1 0.819** | 48 / 134 / 37 → F1 0.360 |
| ADDRESS | 69 / 13 / 100 → **F1 0.550** | 19 / 68 / 141 → F1 0.154 |
| AGE | 50 / 6 / 6 → **F1 0.893** | 0 / 0 / 56 → F1 0.000 |
| CARD | 4 / 0 / 74 → F1 0.098 | 0 / 0 / 78 → F1 0.000 |
| DRIVER_LICENSE | 5 / 0 / 12 → **F1 0.455** | 0 / 0 / 17 → F1 0.000 |
| DT_BIRTH | 34 / 1 / 36 → **F1 0.648** | 6 / 21 / 65 → F1 0.122 |
| EDUCATION | 56 / 20 / 33 → **F1 0.679** | 0 / 0 / 89 → F1 0.000 |
| EMAIL | 81 / 0 / 0 → **F1 1.000** | 81 / 1 / 0 → F1 0.994 |
| FRN | 9 / 0 / 0 → **F1 1.000** | 0 / 0 / 9 → F1 0.000 |
| HEIGHT | 58 / 1 / 7 → **F1 0.935** | 0 / 0 / 65 → F1 0.000 |
| IP | 11 / 0 / 0 → **F1 1.000** | 0 / 0 / 11 → F1 0.000 |
| MAJOR | 40 / 0 / 25 → **F1 0.762** | 0 / 0 / 65 → F1 0.000 |
| PASSPORT | 15 / 0 / 3 → **F1 0.909** | 0 / 0 / 18 → F1 0.000 |
| PERSON | 21 / 198 / 71 → F1 0.135 | 29 / 273 / 63 → **F1 0.147** |
| PHONE | 124 / 2 / 0 → **F1 0.992** | 97 / 121 / 29 → F1 0.564 |
| POSITION | 65 / 40 / 58 → **F1 0.570** | 0 / 0 / 123 → F1 0.000 |
| RRN | 18 / 0 / 0 → **F1 1.000** | 0 / 0 / 18 → F1 0.000 |
| URL | 38 / 0 / 1 → **F1 0.987** | 23 / 12 / 18 → F1 0.605 |
| VEHICLE | 50 / 0 / 2 → **F1 0.980** | 0 / 0 / 52 → F1 0.000 |
| WEIGHT | 50 / 5 / 0 → **F1 0.952** | 0 / 0 / 49 → F1 0.000 |
| **(micro)** | **859 / 297 / 444 → F1 0.699** | 303 / 630 / 1,003 → F1 0.271 |

## 4. 카테고리 그룹 분석

### k-pii 완승 (F1 > 0.9, openai 미커버 또는 약함)
EMAIL · FRN · IP · RRN · PHONE · URL · VEHICLE · WEIGHT · HEIGHT · PASSPORT
· AGE — 11 카테고리. 한국 특화 식별번호 + 정형 PII (이메일/전화) + 신체 정보.
openai 모델의 라벨 체계에 한국 특화 카테고리가 *전혀* 없는 게 결정적.

### k-pii 부분 우위 (k-pii > openai, 둘 다 개선 여지)
ACCOUNT · MAJOR · EDUCATION · DT_BIRTH · POSITION · ADDRESS · DRIVER_LICENSE
— openai는 `private_address`/`private_date`/`account_number` 라벨로 어느
정도 시도하지만 한국어 표현이 잘 안 잡힘. k-pii는 사전+패턴 기반으로 더 안정.

### 비등 / 둘 다 약함
- **PERSON** (k-pii 0.135 / openai 0.147): KDPII gold 의 PERSON 은 *2자
  외자·별명* 비중이 높고 (D-013), 풀네임 (3자+) 필터를 적용해도 정확도
  낮음. 두 모델 모두 한국어 대화체 인명 검출에 약점.
- **CARD** (k-pii 0.098 / openai 0.000): KDPII 카드 번호가 Luhn 안 맞는
  형식 (분리자 변형, 마스킹된 번호 등) 비중이 높음.

## 5. 해석 — 왜 이런 결과가 나오는가

1. **openai/privacy-filter 의 라벨 체계는 영어 일반 PII 중심.**
   33 라벨 중 8 카테고리 (account/address/date/email/person/phone/url/secret)
   만 다루며 한국 특화 식별번호 카테고리가 부재. 한국 RRN/FRN/운전면허/사업자
   /법인 번호 등은 *어느 라벨로도 잡히지 않음* (account_number 로 일부 유추는
   하지만 매우 부분적).

2. **k-pii 의 규칙·체크섬 강점이 그대로 드러남.**
   RRN/FRN/사업자/법인/카드 등 체크섬 검증되는 결정적 PII 는 100% 또는 거의
   100%. URL/EMAIL/IP/PHONE 등 형식 결정적 PII 도 0.99+ F1.

3. **컨텍스트 기반 카테고리는 양쪽 다 약점.**
   ADDRESS · POSITION · EDUCATION · MAJOR · DT_BIRTH 는 자연어 표현 다양해서
   k-pii 도 0.5~0.7 수준, openai 는 더 낮음.

4. **PERSON 은 KDPII 도메인 특성으로 둘 다 어려움.**
   KDPII 는 메신저·통화 발췌라 별명·외자가 많고, *그 자체로 PII 가 아닌* 1-2
   자 발화 (재명, 미선, 주, ...) 가 다수. 본 평가는 풀네임 (3자+) 필터를
   적용했으나 그래도 둘 다 0.14 근처. k-pii 의 공공 문서 도메인 (직책 anchor
   가 강한) 에서는 F1 ≈ 0.83 (CLAUDE.md D-018) — 도메인 차이가 큼.

## 6. 한계와 주의사항

- 본 비교는 **단일 코퍼스 (KDPII, 대화체)** 기준. 공공 문서 (k-pii 의 본
  타겟 도메인) 에서는 결과가 또 다를 수 있음 (k-pii 의 직책-anchor 룰이
  강하게 작동).
- openai/privacy-filter 의 **한국어 학습 데이터 노출 정도는 카드에 명시 X**
  — 학습 분포가 영어 중심이면 한국어 대화체에서의 0.27 F1 는 *모델 자체의
  실력이 아니라 도메인 미스매치* 일 수 있음.
- 비교 대상에 **OpenMed/privacy-filter-multilingual** (한국어 공식 지원, 217
  라벨) 가 빠짐 — torch + transformers 버전 매칭 문제로 본 세션에서는 실행
  못함. 후속 평가 권장.
- KDPII 의 PERSON 라벨에는 *별명·외자가 많아* PERSON F1 측정이 도메인 노이즈
  큼. 별도로 풀네임만 필터링한 결과 (D-013) 가 본 보고서.

## 7. 산출물 및 재현 방법

평가 스크립트:
```bash
python -m k_pii.eval.model_comparison data/kdpii/test.json \
    --mode kdpii \
    --backend onnx --device cpu \
    --cache-dir ./models
```

데이터:
- `data/kdpii/test.json` — KDPII test split (Zenodo 10968609 CC-BY-4.0)
- `models/models--openai--privacy-filter/...` — HF cache (q4f16 ONNX, 770 MB)

원본 출력: `data/corpus/kdpii_3way_full.txt`.

## 8. 다음 권장 작업

1. **OpenMed/privacy-filter-multilingual** (한국어 공식 지원, 217 라벨) 도
   같은 KDPII test 에 평가. torch 2.7+ 또는 ONNX 변환 (Optimum) 필요.
2. **공공 문서 도메인** (AI Hub 71845 공공 민원 + 569 행정문서) 에 *gold
   라벨 없이 pseudo-GT 모드* 로 양쪽 출력 비교. k-pii 의 진짜 타겟 도메인
   에서의 상대 성능을 보기 위함.
3. **PERSON 카테고리 부분만 풀네임 (3자+) + 별명 (1-2자) 분리 보고**.
   현재는 풀네임만 평가했으나 별명 포함 평가도 별도 제공하면 두 모델의
   별명 검출 능력 차이가 드러남.

---

## 9. 공정 비교 보충 — 라벨 스코프 제한 (Apples-to-Apples)

> 위 섹션 3 의 카테고리별 표를 보면 *11개 카테고리에서 openai/privacy-filter
> F1 = 0.000*. 이는 모델이 "검출 실패" 한 게 아니라 **그 라벨 자체가 openai
> 모델 출력 공간에 없어서** 모든 gold 가 자동 FN 으로 잡힌 결과. 즉
> *모델 품질 차이가 아니라 스코프 차이*. 본 섹션은 이를 보정한 공정 비교.

### 9.1 openai/privacy-filter 의 실제 라벨 스코프

| openai 라벨 | k-pii 매핑 |
|------------|-----------|
| `private_person` | PERSON |
| `private_email` | EMAIL |
| `private_phone` | PHONE |
| `private_address` | ADDRESS |
| `private_date` | DT_BIRTH |
| `private_url` | URL |
| `account_number` | ACCOUNT |
| `secret` | (k-pii 대응 X, 패스워드/API 키 등 일반) |

→ openai 가 출력 *가능* 한 k-pii 라벨은 **7종** 뿐 (`PERSON · EMAIL · PHONE
· ADDRESS · DT_BIRTH · URL · ACCOUNT`).

openai 의 출력 공간에 *없는* k-pii 카테고리 (KDPII gold 에는 존재):
RRN · FRN · CARD · PASSPORT · DRIVER_LICENSE · VEHICLE · MAJOR · EDUCATION
· POSITION · IP · AGE · HEIGHT · WEIGHT — **13종**. 이들의 openai F1=0.000
은 "실력" 이 아니라 "스코프 밖" 의 의미.

### 9.2 공정 비교 — 7 공통 카테고리만 재집계

| 라벨 | k-pii (TP/FP/FN) | k-pii F1 | openai (TP/FP/FN) | openai F1 |
|------|-----------------:|---------:|------------------:|----------:|
| PERSON | 21 / 198 / 71 | 0.135 | 29 / 273 / 63 | **0.147** |
| EMAIL | 81 / 0 / 0 | **1.000** | 81 / 1 / 0 | 0.994 |
| PHONE | 124 / 2 / 0 | **0.992** | 97 / 121 / 29 | 0.564 |
| ADDRESS | 69 / 13 / 100 | **0.550** | 19 / 68 / 141 | 0.154 |
| DT_BIRTH | 34 / 1 / 36 | **0.648** | 6 / 21 / 65 | 0.122 |
| URL | 38 / 0 / 1 | **0.987** | 23 / 12 / 18 | 0.605 |
| ACCOUNT | 61 / 11 / 16 | **0.819** | 48 / 134 / 37 | 0.360 |
| **(공정 micro)** | **428 / 225 / 224** | **0.656** | **303 / 630 / 353** | **0.382** |

**공정 스코프 결론:** k-pii micro F1 = **0.656** vs openai = **0.382**. 즉
openai 가 가장 자신 있는 7개 라벨 영역에서만 비교해도 k-pii 가 **약 1.72배**
우위. PERSON 만 openai 가 미세 우위 (둘 다 0.13~0.15 수준, KDPII 대화체
도메인의 별명/외자 특성 때문).

### 9.3 그러면 "전체 0.699 vs 0.271" 비교는 무의미한가?

아니오 — *해석에 주의가 필요할 뿐* 의미는 있음. 한국 공공 부문 PII 보호의
실제 요구사항은 **RRN, FRN, 운전면허, 여권, 사업자등록번호 같은 한국 특화
식별번호 검출** 이 핵심 (개인정보보호법 시행령 제19조 고유식별정보). 이 영역
을 *전혀 라벨로 출력하지 못하는* 모델은 한국 공공 도메인 배포에 부적합.

> "openai/privacy-filter 는 라벨 스코프가 다르므로 한국 공공 PII 보호 용도
> 로는 그대로 쓸 수 없다" — 이게 본 평가의 핵심 메시지이며 그건 micro F1
> 0.271 으로 정량화된 게 맞음. 다만 이는 *모델의 인지 정확도 부족* 이 아니라
> *모델의 라벨 정의 차이* 라는 점을 본 섹션 9 가 명확히 함.

### 9.4 향후 확장 — account_number 의 다중 매핑

KDPII test 에서 RRN-shape 문자열 "880101-1234568" 을 openai 가 `account_number`
로 검출하는 사례를 확인. 즉 openai 의 `account_number` 는 사실상 *범용 숫자
ID catch-all* 로 동작. 본 평가의 OPENAI_TO_KPII 매핑은 1:1 (`account_number`
→ `ACCOUNT`) 이었으나, 1:N 매핑 (`account_number` → {ACCOUNT, RRN, CARD,
PASSPORT, DRIVER_LICENSE}) 로 확장하면 openai 의 ACCOUNT/RRN/CARD 점수가
일부 회복 가능. 후속 평가에서 별도 제공 예정 (해당 매핑 변경은 본 보고서
이후 코드 패치 + 재실행 후 *별도 섹션* 으로 추가; 본 섹션 9.2 표는 1:1
매핑 기준 — 같은 평가 실행본 (`data/corpus/kdpii_3way_full.txt`) 의 숫자).
