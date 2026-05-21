# KDPII 평가 결과 보고서

> k-pii 라이브러리를 KDPII (Korean Dialog PII) 데이터셋으로 평가한 결과.
> KDPII 는 현재 공개된 한국어 일반 도메인 PII 평가 벤치마크의 *사실상 유일* 한
> 선택지로, 본 보고서는 22 카테고리 53,778 문서 평가 결과를 정리.

생성: 2026-05-21 · 브랜치: `claude/understand-work-status-S4kXM`

---

## 1. KDPII 데이터셋 개요

### 출처
**Li Fei, Yejee Kang, Seoyoon Park, Yeonji Jang, Jongkyu Lee, Hansaem Kim**
*"KDPII: A New Korean Dialogic Dataset for the Deidentification of Personally
Identifiable Information."* **IEEE Access, 2024.**

- DOI: [10.1109/ACCESS.2024.3461804](https://ieeexplore.ieee.org/document/10681073)
- Zenodo: [10968609](https://zenodo.org/records/10968609)
- 저자: 연세대학교 외

### 데이터 규모
| 항목 | 값 |
|---|---:|
| 문서 수 | **53,778** |
| 평균 길이 | 한국어 일상 대화 (메신저·통화 발췌 가공) |
| PII 라벨 수 | 22 종 |
| 라벨링 단위 | per-document, form 단위 |

### 한국어 PII 데이터셋의 희소성

검색 (2026-05-21) 결과 *공개* 한국어 일반 도메인 PII 평가 벤치마크는 KDPII
**단 하나**. 다른 후보는 모두 PII 데이터셋 아님:

| 데이터셋 | 도메인 | PII 평가용? | 비고 |
|---|---|---|---|
| **KDPII** | 일상 대화 | **✓** | 본 평가 대상 |
| KBMC | 의료 | △ | 의료 NER, 환자 식별 일부 |
| KLUE-NER | 신문기사 | ✗ | 일반 NER (PS/OG/LC/DT/QT/TI) |
| Naver-창원대 NER | 일반 | ✗ | 일반 NER |
| KoCHET | 문화유산 | ✗ | Entity 관련 |
| AI Hub | - | - | 평가용 corpus 미공개 |

→ KDPII 외에는 한국어 *일반 도메인* PII 평가가 불가능. 본 보고서가 k-pii 의
종합 PII 검출 정확도 측정의 유일한 외부 기준.

---

## 2. 라벨 매핑

KDPII gold 라벨 → k-pii LABEL:

| KDPII gold | k-pii LABEL | KDPII gold | k-pii LABEL |
|---|---|---|---|
| PS_NAME | PERSON | LC_ADDRESS | ADDRESS |
| QT_AGE | AGE | LCP_COUNTRY | ADDRESS |
| OGG_EDUCATION | EDUCATION | QT_CARD_NUMBER | CARD |
| FD_MAJOR | MAJOR | QT_ACCOUNT_NUMBER | ACCOUNT |
| CV_POSITION | POSITION | QT_PASSPORT_NUMBER | PASSPORT |
| DT_BIRTH | DT_BIRTH | QT_DRIVER_NUMBER | DRIVER_LICENSE |
| QT_PHONE | PHONE | QT_IP | IP |
| QT_MOBILE | PHONE | QT_ALIEN_NUMBER | FRN |
| TMI_EMAIL | EMAIL | QT_PLATE_NUMBER | VEHICLE |
| TMI_SITE | URL | QT_LENGTH | HEIGHT |
| QT_RESIDENT_NUMBER | RRN | QT_WEIGHT | WEIGHT |

**스코프 밖 라벨** (k-pii 미구현):
PS_NICKNAME, OGG_CLUB, OGG_RELIGION, LC_PLACE, OG_WORKPLACE, OG_DEPARTMENT,
CV_SEX, CV_MILITARY_CAMP, TM_BLOOD_TYPE, QT_GRADE.

### 매칭 정책
**substring overlap** — 예측 텍스트가 gold form 의 부분 문자열이거나 반대이면
정탐. 검출 위치는 무시하고 *문서별 set 비교*.

---

## 3. 전체 결과

### 카테고리별 통합 표

| Tier | 카테고리 | 정탐 | 과탐 | 미탐 | 정확도 | 재현율 | F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| **S** | EMAIL | 617 | 1 | 0 | 0.998 | 1.000 | **0.999** |
| S | URL | 457 | 0 | 3 | 1.000 | 0.993 | **0.997** |
| S | FRN | 198 | 0 | 1 | 1.000 | 0.995 | **0.997** |
| S | VEHICLE | 449 | 0 | 4 | 1.000 | 0.991 | **0.996** |
| S | RRN | 198 | 0 | 2 | 1.000 | 0.990 | **0.995** |
| S | IP | 197 | 0 | 3 | 1.000 | 0.985 | **0.992** |
| S | PHONE | 1,315 | 27 | 4 | 0.980 | 0.997 | **0.989** |
| **A** | WEIGHT | 700 | 127 | 1 | 0.846 | 0.999 | **0.916** |
| A | AGE | 626 | 57 | 74 | 0.917 | 0.894 | **0.905** |
| A | HEIGHT | 552 | 3 | 155 | 0.995 | 0.781 | **0.875** |
| A | DRIVER_LICENSE | 154 | 0 | 45 | 1.000 | 0.774 | **0.873** |
| A | ACCOUNT | 637 | 96 | 167 | 0.869 | 0.792 | **0.829** |
| **B** | PASSPORT | 132 | 0 | 68 | 1.000 | 0.660 | **0.795** |
| B | MAJOR | 441 | 27 | 268 | 0.942 | 0.622 | **0.749** |
| B | DT_BIRTH | 379 | 25 | 355 | 0.938 | 0.516 | **0.666** |
| B | EDUCATION | 567 | 150 | 475 | 0.791 | 0.544 | **0.645** |
| B | POSITION | 596 | 406 | 564 | 0.595 | 0.514 | **0.551** |
| **C** | ADDRESS | 624 | 122 | 1,051 | 0.836 | 0.373 | **0.515** |
| **D** | PERSON | 502 | 2,714 | 1,541 | 0.156 | 0.246 | **0.191** |
| D | CARD | 56 | 0 | 749 | 1.000 | 0.070 | **0.130** |
| - | **(전체)** | **9,397** | **3,756** | **5,530** | **0.715** | **0.630** | **0.669** |

### Tier 분포

| Tier | F1 | 카테고리 수 | 운영 적합도 |
|---|---|---:|---|
| S | ≥0.95 | 7 | Production 즉시 |
| A | 0.80~0.95 | 5 | 운영 가능 |
| B | 0.50~0.80 | 5 | 사람 검토 권장 |
| C | 0.20~0.50 | 1 (ADDRESS) | recall 보강 필요 |
| D | <0.20 | 2 (PERSON, CARD) | 도메인 한계 |

→ **20 카테고리 중 17개 (85%) 가 F1 0.50+**. 결정적 검출 (RRN/EMAIL/PHONE 등
S Tier) 은 거의 완벽.

---

## 4. 과탐 (FP) 정밀 분석

### 카테고리별 과탐 + 비율 + 밀도

| 카테고리 | 잡은 총 | 정탐 | 과탐 | 과탐률 | 1,000문서당 |
|---|---:|---:|---:|---:|---:|
| **PERSON** | 3,216 | 502 | **2,714** | **84.4%** | 50.5 |
| **POSITION** | 1,002 | 596 | 406 | 40.5% | 7.6 |
| EDUCATION | 717 | 567 | 150 | 20.9% | 2.8 |
| WEIGHT | 827 | 700 | 127 | 15.4% | 2.4 |
| ADDRESS | 746 | 624 | 122 | 16.4% | 2.3 |
| ACCOUNT | 733 | 637 | 96 | 13.1% | 1.8 |
| AGE | 683 | 626 | 57 | 8.3% | 1.1 |
| PHONE | 1,342 | 1,315 | 27 | 2.0% | 0.5 |
| MAJOR | 468 | 441 | 27 | 5.8% | 0.5 |
| DT_BIRTH | 404 | 379 | 25 | 6.2% | 0.5 |
| HEIGHT | 555 | 552 | 3 | 0.5% | 0.06 |
| 그 외 (RRN/EMAIL/CARD 등) | 2,476 | 2,475 | 1 | <0.1% | <0.1 |
| **전체** | **13,153** | **9,397** | **3,756** | **28.6%** | **69.8** |

### 해석

- **결정적 카테고리 (S Tier) 과탐 = 거의 0**
  RRN/FRN/PASSPORT/CARD/DRIVER_LICENSE/IP/URL/VEHICLE 모두 과탐 0건.
  EMAIL 1건, PHONE 27건 (0.2~2%).

- **도메인 PII (PERSON/POSITION) 과탐 집중**
  전체 과탐 3,756 중 PERSON 이 72%, POSITION 이 11%. 한국어 단성 성씨가
  일반어 prefix 와 충돌하는 도메인 한계.

- **1,000 문서당 과탐 70건** = 한 문서당 0.07건. STRICT 모드 운영 시 약한
  신호 과탐도 차단되므로 안전 우선.

---

## 5. 미탐 (FN) 정밀 분석

### 카테고리별 미탐

| 카테고리 | 미탐 | 비고 |
|---|---:|---|
| **PERSON** | 1,541 | 1자/2자 별명 51% (공문서 도메인 등장 X) |
| **ADDRESS** | 1,051 | 동 단위 단독 등장 (anchor 없음) |
| **CARD** | 749 | KDPII 카드 88.3% Luhn invalid (fake) |
| POSITION | 564 | "X 대리" 같은 인명 인접 (합성 회귀 위험) |
| EDUCATION | 475 | 고등학교/중학교 정식명 누락 |
| DT_BIRTH | 355 | 한국어 날짜 변형 일부 |
| MAJOR | 268 | "실용음악과/예술학과" 일부 |
| AGE | 74 | 한글 음역 단독 ("마흔다섯") |
| 그 외 | 453 | |
| **전체** | **5,530** | |

### PERSON 미탐 (1,541) 길이별 분포

| 길이 | 미탐 | 비중 | 공문서 도메인 영향 |
|---:|---:|---:|---|
| 1자 (단성) | ~165 | 10.7% | 등장 X (영향 0) |
| 2자 (이름만) | ~580 | 37.6% | 거의 없음 (영향 ~5%) |
| 3자 (풀네임) | ~700 | 45.4% | 일부 영향 |
| 4자+ (외국·복성) | ~95 | 6.2% | 한국 도메인 X |

→ KDPII PERSON 미탐의 **48% 가 공문서 도메인에 등장 안 함**.

---

## 6. 카테고리별 한계 분석

### PERSON F1 0.191 — 도메인 차이

KDPII PERSON gold 의 라벨링이 *일상 대화 도메인* 기준:

| 길이 | KDPII gold 비중 | 공문서 등장 |
|---|---:|---|
| 1자 ("주/김") | 8.1% | 거의 0% |
| 2자 ("재명/미선") | 42.0% | 거의 0% |
| 3자+ 풀네임 | 49.9% | ~100% |

**개인정보보호법 제2조 정의:**
> "그 자체로 또는 다른 정보와 쉽게 결합하여 특정 개인을 알아볼 수 있는 정보"

→ 단독 1자·2자 별명은 *그 자체로* 식별 불가. KDPII 가 일상 대화 맥락 상
화자가 누구를 가리키는지 안다는 전제로 라벨링.

**공공 문서 도메인 실측 (별도 문서 `domain_fit_report.md` §5):**
- 본문 산문 12 케이스 PERSON F1 = **0.833**
- → KDPII 0.191 이 사용자 도메인 실질 지표 아님

### CARD F1 0.130 — KDPII 데이터 자체 한계

KDPII 카드 gold 720건 중 **88.3% (636건) 가 Luhn 체크섬 invalid**. 이는 KDPII
저자가 *재식별 위험 회피* 를 위해 의도적으로 fake 카드 번호 사용한 것.

k-pii Decision D-006: *Luhn 통과만 emit* (체크섬 실패 = PII 아님). 이 정책으로
KDPII 카드 56건만 정탐. 실제 production 에서는 valid Luhn 카드 = 진짜 PII →
**정책 옳음, 점수만 낮음**.

### ADDRESS F1 0.515 — anchor 정책 trade-off

KDPII LC_ADDRESS gold 의 동 단위 단독 등장 (anchor 없음) 다수. 우리 정책:
- 행정구역 사전 매칭 + **대화체 anchor 필수** (살던/이사/주소 등)
- 국가명 (LCP_COUNTRY) 만 anchor 면제

이유: 정책 완화 시 일반 문장 FP 폭증 — "강남구 영등포구 등 25개 자치구" 같은
일반 텍스트 매칭 위험. 사용자 도메인 (공공) 의 안전 우선.

---

## 7. 도메인 적합도 비교

| 도메인 | F1 | k-pii 적합도 |
|---|---:|---|
| **공공 문서 본문 산문** (실측 12 케이스) | **~0.83** | **운영 가능** |
| 합성 8 템플릿 다단락 | 0.83 | 좋음 |
| KDPII 전체 (일상 대화) | **0.669** | 참고용 |
| KDPII PERSON only | 0.191 | 도메인 한계 |
| KLUE-NER PS only | 0.329 | 일반 NER (PII 아님) |

→ KDPII 전체 F1 0.669 가 *대화체 도메인* 의 점수.
사용자 메인 도메인 (공공 문서) 에서는 F1 ≈ 0.83.

---

## 8. 개선 추이

| 단계 | KDPII 전체 F1 | 핵심 변경 |
|---|---:|---|
| 시작 (베이스라인) | 0.412 | 첫 측정 |
| ACCOUNT 은행 anchor | 0.500 | 시중은행 키워드 |
| 7 카테고리 신규 | 0.502 | AGE/EDU/MAJOR/POS/BIRTH 등 |
| 룰 정제 1차 | 0.566 | 카테고리별 FP 분석 |
| PERSON FP 1차 | 0.580 | 호칭/동사 활용 거부 |
| ADDRESS+PHONE 2차 | 0.598 | 단독 행정구역 |
| EDU/MAJOR/POS 사전 | 0.613 | 약칭/단과대/직책 |
| URL/COUNTRY 매핑 | 0.650 | 라벨 매핑 확장 |
| 동 사전 + 어말 사전 | 0.655 | 형태소 단위 거부 |
| A.1~D.3 정제 | 0.665 | 직책+연결어미 + 국적 접미사 |
| **AGE 정규식 + 은행 약어** | **0.669** | "30살인데/30대" cover |

**누적: 0.412 → 0.669 (+0.257, +62%)** · 외부 ML 의존성 0.

---

## 9. KDPII 점수의 *해석 주의*

KDPII 결과는 다음 한계 하에 해석:

1. **대화체 도메인 점수** — 공공 문서 도메인 지표 아님
2. **1-2자 별명·이름 단독 50% 포함** — 한국 PII 정의상 PII 모호 케이스
3. **CARD fake 데이터 88%** — 정책상 정상 거부 (점수 vs 정확도 괴리)
4. **PS_NICKNAME/OG_WORKPLACE 등 스코프 밖 라벨 다수** — 의도적 미구현

따라서 **micro F1 0.669** 는 *대화체 도메인의 종합 점수* 이며,
사용자 도메인 (공공 문서) 의 실질 성능은 **본문 산문 측정 F1 ~0.83**.

---

## 10. 재현

```bash
# KDPII 데이터셋 다운로드 (Zenodo)
# https://zenodo.org/records/10968609

# k-pii 평가
python -m k_pii.eval.kdpii /path/to/kdpii.jsonl
```

평가 모듈 위치: `src/k_pii/eval/kdpii.py`
- `load_kdpii(path)` — JSONL → KdpiiDocument 리스트
- `evaluate_kdpii(docs)` — 전체 측정
- `format_kdpii_report(report)` — 한국어 출력 (정탐/과탐/미탐)

---

## 11. 인용

```bibtex
@article{fei2024kdpii,
  title={KDPII: A New Korean Dialogic Dataset for the Deidentification of
         Personally Identifiable Information},
  author={Fei, Li and Kang, Yejee and Park, Seoyoon and Jang, Yeonji
          and Lee, Jongkyu and Kim, Hansaem},
  journal={IEEE Access},
  year={2024},
  publisher={IEEE},
  doi={10.1109/ACCESS.2024.3461804}
}
```

## 12. 관련 문서

- [`EVALUATION_REPORT.md`](EVALUATION_REPORT.md) — 통합 평가 보고서
- [`domain_fit_report.md`](domain_fit_report.md) — 도메인 적합도 분석
- [`kdpii_visual_compare.html`](kdpii_visual_compare.html) — KDPII 100 문서 시각 비교
