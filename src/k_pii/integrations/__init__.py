"""외부 PII 검출기 통합 — k-pii 와 결합 가능한 어댑터들.

본 라이브러리의 *코어* 는 절대 의존성을 추가하지 않는다 (CLAUDE.md §2 #1).
통합 어댑터들은 모두 *soft import* 로 동작하며, 외부 모델/라이브러리가
설치되어 있을 때만 활성화된다.

지원 어댑터:
- ``OpenAIPrivacyFilterAdapter`` — OpenAI Privacy Filter (Apache-2.0, 2026.4)
  · 한국어 일반 NER 보강
  · ``pip install k-pii[ml]`` 로 ML 의존성 설치
  · GPU 없이도 동작 (CPU 추론 가능, 다소 느림)

연계 패턴:
- **Layered (A)**: k-pii 결정적 PII + 보조 검출기 자연어 = 합산 → 가장 일반적
- **Cross-validation (B)**: 두 검출기 모두 찾으면 BLOCK, 한 쪽만이면 REVIEW
- **Enrich (C)**: 보조 검출 결과에 k-pii 한국 도메인 컨텍스트 부착
- **Fallback (D)**: k-pii 의 REVIEW 큐만 보조 검출기로 보냄
"""
from k_pii.integrations.base import SecondaryDetector, MockSecondaryDetector
from k_pii.integrations.hybrid import merge_detections, MergeMode

__all__ = [
    "SecondaryDetector",
    "MockSecondaryDetector",
    "merge_detections",
    "MergeMode",
]


def get_privacy_filter_adapter(**kwargs):
    """Lazy import of the OpenAI Privacy Filter adapter.

    Avoids loading torch/transformers at package import time.
    """
    from k_pii.integrations.openai_privacy_filter import OpenAIPrivacyFilterAdapter
    return OpenAIPrivacyFilterAdapter(**kwargs)
