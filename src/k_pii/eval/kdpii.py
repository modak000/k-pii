"""KDPII (Korean Dialog PII) 벤치마크 어댑터.

KDPII 코퍼스 (KAIST/KETI 한국어 대화체 PII 데이터셋) 의 JSONL 포맷을 읽어
k-pii detect_all 출력과 라벨별 P/R/F1 측정.

데이터 포맷 (per line):
    {
      "query": "<대화 텍스트>",
      "answer": [{"label": "PS_NAME", "form": "김민지"}, ...]
    }

KDPII 라벨 → k-pii LABEL 매핑은 ``KDPII_LABEL_MAP`` 참조. 본 매핑은
2026-05-19 시점 KDPII 라벨 분포 직접 조사로 정정 (초기 매핑 오류 사례
docs/kdpii_session_report.md D-011 참조).

매칭 정책: **substring overlap** — 예측 텍스트가 gold form 의 부분 문자열
이거나 그 반대일 경우 TP. ``010-1234-5678`` 검출이 gold ``010 1234 5678``
과도 매칭되도록.

사용:
    from k_pii.eval.kdpii import load_kdpii, evaluate_kdpii, format_kdpii_report

    docs = load_kdpii("kdpii.jsonl")
    report = evaluate_kdpii(docs)
    print(format_kdpii_report(report))
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from k_pii.core.types import DetectionResult
from k_pii.detect import detect_all


# KDPII 라벨 → k-pii LABEL 매핑.
# (PS_NAME / OGG_EDUCATION 같이 KDPII 가 사용하는 정식 라벨 기준)
KDPII_LABEL_MAP: dict[str, str] = {
    "PS_NAME": "PERSON",
    "QT_AGE": "AGE",
    "OGG_EDUCATION": "EDUCATION",
    "FD_MAJOR": "MAJOR",
    "CV_POSITION": "POSITION",
    "DT_BIRTH": "DT_BIRTH",
    "QT_PHONE": "PHONE",
    "QT_MOBILE": "PHONE",
    "TMI_EMAIL": "EMAIL",
    "QT_RESIDENT_NUMBER": "RRN",
    "LC_ADDRESS": "ADDRESS",
    "QT_CARD_NUMBER": "CARD",
    "QT_ACCOUNT_NUMBER": "ACCOUNT",
    "QT_PASSPORT_NUMBER": "PASSPORT",
    "QT_DRIVER_NUMBER": "DRIVER_LICENSE",
    "QT_IP": "IP",
    "QT_ALIEN_NUMBER": "FRN",
    "QT_PLATE_NUMBER": "VEHICLE",
    "QT_LENGTH": "HEIGHT",
    "QT_WEIGHT": "WEIGHT",
}


@dataclass
class KdpiiDocument:
    query: str
    gold: dict[str, set[str]] = field(default_factory=dict)  # label → {form}


@dataclass
class LabelMetrics:
    label: str
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0


@dataclass
class KdpiiReport:
    per_label: dict[str, LabelMetrics] = field(default_factory=dict)
    n_documents: int = 0

    @property
    def micro_tp(self) -> int:
        return sum(m.tp for m in self.per_label.values())

    @property
    def micro_fp(self) -> int:
        return sum(m.fp for m in self.per_label.values())

    @property
    def micro_fn(self) -> int:
        return sum(m.fn for m in self.per_label.values())

    @property
    def micro_precision(self) -> float:
        t, f = self.micro_tp, self.micro_fp
        return t / (t + f) if t + f else 0.0

    @property
    def micro_recall(self) -> float:
        t, f = self.micro_tp, self.micro_fn
        return t / (t + f) if t + f else 0.0

    @property
    def micro_f1(self) -> float:
        p, r = self.micro_precision, self.micro_recall
        return 2 * p * r / (p + r) if p + r else 0.0


def load_kdpii(path: str | Path) -> list[KdpiiDocument]:
    """JSONL 파일 → KdpiiDocument 리스트. 매핑 안 된 라벨은 무시."""
    docs: list[KdpiiDocument] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            doc = KdpiiDocument(query=d["query"])
            for a in d.get("answer", []):
                mapped = KDPII_LABEL_MAP.get(a["label"])
                if mapped is None:
                    continue
                doc.gold.setdefault(mapped, set()).add(a["form"])
            docs.append(doc)
    return docs


def _matched_overlap(pred: set[str], gold: set[str]) -> tuple[set[str], set[str]]:
    """``(matched_pred, matched_gold)`` substring overlap 매칭.

    예측 텍스트가 gold form 의 부분이거나 반대이면 TP. 1:N / N:1 모두 허용
    (per-label set 평가; 위치 무시).
    """
    mp: set[str] = set()
    mg: set[str] = set()
    for pi in pred:
        for gi in gold:
            if pi in gi or gi in pi:
                mp.add(pi)
                mg.add(gi)
    return mp, mg


def evaluate_kdpii(
    docs: Iterable[KdpiiDocument],
    detector: Callable[[str], Iterable[DetectionResult]] = detect_all,
) -> KdpiiReport:
    report = KdpiiReport()
    for doc in docs:
        report.n_documents += 1
        pred_by_label: dict[str, set[str]] = defaultdict(set)
        for r in detector(doc.query):
            pred_by_label[r.label].add(r.text)
        for lab in set(doc.gold) | set(pred_by_label):
            g = doc.gold.get(lab, set())
            p = pred_by_label.get(lab, set())
            mp, mg = _matched_overlap(p, g)
            m = report.per_label.setdefault(lab, LabelMetrics(label=lab))
            m.tp += len(mp)
            m.fp += len(p - mp)
            m.fn += len(g - mg)
    return report


def format_kdpii_report(report: KdpiiReport) -> str:
    lines: list[str] = []
    lines.append(f"문서 수: {report.n_documents}")
    lines.append(f"라벨 매핑: {len(KDPII_LABEL_MAP)} KDPII → "
                 f"{len(set(KDPII_LABEL_MAP.values()))} k-pii LABEL")
    lines.append("")
    lines.append(f"{'라벨':<15}{'TP':>6}{'FP':>6}{'FN':>6}{'P':>8}{'R':>8}{'F1':>8}")
    lines.append("-" * 57)
    for lab in sorted(report.per_label):
        m = report.per_label[lab]
        lines.append(
            f"{lab:<15}{m.tp:>6}{m.fp:>6}{m.fn:>6}"
            f"{m.precision:>8.3f}{m.recall:>8.3f}{m.f1:>8.3f}"
        )
    lines.append("-" * 57)
    lines.append(
        f"{'(micro)':<15}{report.micro_tp:>6}{report.micro_fp:>6}{report.micro_fn:>6}"
        f"{report.micro_precision:>8.3f}{report.micro_recall:>8.3f}"
        f"{report.micro_f1:>8.3f}"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="k-pii-kdpii",
        description="KDPII 코퍼스에서 k-pii 검출 정확도 평가",
    )
    p.add_argument("path", help="KDPII JSONL 파일")
    args = p.parse_args(argv)
    docs = load_kdpii(args.path)
    report = evaluate_kdpii(docs)
    print(format_kdpii_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
