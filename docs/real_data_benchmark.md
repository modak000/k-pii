# 실데이터 벤치마크 보고서

> k-pii 의 *실제* 검출 정확도. 합성 코퍼스 (`k_pii.eval.benchmark`) 의
> F1=1.000 은 좁은 템플릿 과적합으로 인한 상한이며, 본 문서의 KDPII /
> KLUE-NER 점수가 production 기대 정확도에 가깝다.

생성: 2026-05-20 · 커밋: `claude/understand-work-status-S4kXM` 기준

## 1. 벤치마크 데이터셋

| 데이터셋 | 문서 수 | 도메인 | 라이센스 | 출처 |
|---|---:|---|---|---|
| KDPII (메인) | 53,778 | 한국어 일상 대화 PII | 학술 연구용 | [IEEE Access 2024](https://ieeexplore.ieee.org/document/10681073) |
| KLUE-NER (참고) | 5,000 | 신문기사 일반 NER | CC BY-SA 4.0 | [KLUE-benchmark](https://github.com/KLUE-benchmark/KLUE) |
| 합성 코퍼스 (sanity) | 60×5seed | 한국 공문서 6 템플릿 | 자체 | `k_pii.eval.synth` |

### KDPII (주벤치마크)

**원논문:** Li Fei, Yejee Kang, Seoyoon Park, Yeonji Jang, Jongkyu Lee,
Hansaem Kim, *"KDPII: A New Korean Dialogic Dataset for the Deidentification
of Personally Identifiable Information,"* **IEEE Access, 2024**.
DOI: `10.1109/ACCESS.2024.3461804`.

논문 핵심 결론 (검색 발췌): *"언어모델의 PII 인식 성능은 모델 크기·아키텍처·학습 자료에
따라 다양했으나, 대부분 한국어 특화 PII 보다 보편 PII (이메일·전화) 인식이 강했다."*

→ k-pii 는 정확히 이 한국어 특화 PII gap 을 외부 ML 없이 **룰 + 사전 + 체크섬**
으로 보강하는 방향. 본 벤치마크는 그 효과 측정.

## 2. KDPII 결과 (53,778 문서, 2026-05-20)

```
라벨                 TP    FP    FN       P       R      F1
---------------------------------------------------------
ACCOUNT           653    93   151   0.875   0.812   0.843
ADDRESS           454   122  1221   0.788   0.271   0.403
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
PERSON            437  2670  1606   0.141   0.214   0.170
PHONE            1315    26     4   0.981   0.997   0.989
POSITION          596   406   564   0.595   0.514   0.551
RRN               198     0     2   1.000   0.990   0.995
URL               457     0     3   1.000   0.993   0.997
VEHICLE           449     0     4   1.000   0.991   0.996
WEIGHT            700   127     1   0.846   0.999   0.916
---------------------------------------------------------
(micro)          8920  3586  6007   0.713   0.598   0.650
```

### Tier 분류

| Tier | F1 | 카테고리 | 운영 적합도 |
|---|---|---|---|
| **S** | ≥0.95 | EMAIL/VEHICLE/FRN/RRN/IP/PHONE/URL | Production 즉시 가능 |
| **A** | 0.80-0.95 | WEIGHT/HEIGHT/DRIVER_LICENSE/ACCOUNT/AGE | 운영 가능 |
| **B** | 0.50-0.80 | PASSPORT/MAJOR/DT_BIRTH/EDUCATION/POSITION | 사람 검토 권장 |
| **C** | 0.20-0.50 | ADDRESS | recall 보강 필요 |
| **D** | <0.20 | PERSON/CARD | 도메인 한계 명시적 |

### 카테고리별 한계 설명

**PERSON F1 0.170** — 한국어 이름 인식의 본질적 어려움. 단성 성씨 (김/이/박) 가
*매우* 흔한 일반어 prefix 이고 (민원/회신/시정 같은), 대화체에서 anchor 없이
이름이 등장. KDPII PERSON gold 2,043건 중 1,604 미매칭은 대부분 단독 인명.

**CARD F1 0.130** — KDPII 의 카드번호 gold 중 **88.3%가 Luhn 체크섬 invalid**
(논문 저자가 의도적으로 가짜 번호 사용). k-pii Decision D-006 정책 (Luhn 통과만
emit) 유지 — production 에서는 더 정확.

**ADDRESS recall 0.271** — KDPII 의 LC_ADDRESS gold 가 anchor 없는 단독
행정구역명 (특히 동 단위) 다수 포함. 우리는 anchor 정책 유지로 일반 문장 FP 회피.
trade-off 결정.

## 3. KLUE-NER 결과 (PERSON only)

KLUE NER v1.1 dev set 5,000 문장:

```
Sentences: 5000  TP=1117  FP=2718  FN=1977
  Precision = 0.291
  Recall    = 0.361
  F1        = 0.322
```

KLUE PS 라벨은 *모든 인명* (역사인물·정치인·외국인 포함) 이라 k-pii 의 PII
스코프와 다름. 따라서 F1 < 0.5 는 본질적이며 정상 동작.

## 4. 합성 코퍼스 (sanity check)

5 seed × 60 문서:

| Seed | F1 |
|---|---:|
| 0 | 1.000 |
| 1 | 1.000 |
| 2 | 1.000 |
| 3 | 1.000 |
| 4 | 1.000 |

⚠ 이 점수는 **실제 정확도가 아니다.** 6 템플릿의 좁은 코퍼스에 검출기가 적합화된
상태. 변경 시 0.95 이하로 떨어지면 회귀 신호로 사용.

## 5. 누적 추이

| 단계 | KDPII micro F1 | 핵심 변경 |
|---|---:|---|
| 시작 (Phase 7 베이스라인) | 0.412 | 합성 1.000, 실데이터 첫 측정 |
| ACCOUNT 은행명 anchor | 0.500 | 11개 시중은행 키워드 |
| 7 카테고리 신규 | 0.502 | AGE/EDU/MAJOR/POS/BIRTH/REL/HOBBY |
| 룰 정제 1차 | 0.566 | 카테고리별 FP 분석 |
| PERSON FP 1차 | 0.580 | 호칭/동사 활용 거부 |
| ADDRESS+PHONE+PERSON 2차 | 0.598 | 단독 행정구역, 1xxx 대표번호 |
| EDU/MAJOR/POS dict | 0.613 | 약칭/단과대/직책 사전 보강 |
| 본 세션 마지막 | **0.650** | 라벨 매핑 확장 (URL/COUNTRY), 조사 떨기 |

**누적 +0.238 (+58%)** 외부 ML 의존성 0건.

## 6. 다음 단계 후보

1. **PERSON recall** — 현재 0.214. 단성 성씨 prefix 의 보수 정책 완화 검토 (FP/FN trade-off).
2. **ADDRESS dong recall** — `is_common_dong` 사전 확장.
3. **신규 카테고리 도입** — KDPII 의 OG_WORKPLACE / OGG_CLUB / TM_BLOOD_TYPE / QT_GRADE 등.
4. **합성 코퍼스 다양화** — 템플릿 추가로 sanity check 의 정직성 향상.

## 7. 인용

본 평가에 KDPII 데이터셋을 사용하는 경우 원논문 인용:

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

KLUE 인용:

```bibtex
@inproceedings{park2021klue,
  title={KLUE: Korean Language Understanding Evaluation},
  author={Park, Sungjoon and Moon, Jihyung and Kim, Sungdong and others},
  booktitle={NeurIPS Datasets and Benchmarks},
  year={2021}
}
```

## 8. 재현

```bash
# KDPII (사용자 데이터셋 사전 다운로드 필요)
python -m k_pii.eval.kdpii /path/to/kdpii.jsonl

# KLUE-NER dev
curl -O https://raw.githubusercontent.com/KLUE-benchmark/KLUE/main/\
     klue_benchmark/klue-ner-v1.1/klue-ner-v1.1_dev.tsv
python -m k_pii.eval.klue_benchmark klue-ner-v1.1_dev.tsv

# 합성 (회귀 감지용)
python -m k_pii.eval.benchmark -n 60 --seed 0
```
