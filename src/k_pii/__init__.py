"""k-pii — rule-based PII detection for Korean public-sector documents.

Public API
----------
- ``Anonymizer`` / ``ProcessingMode`` / ``Action`` — high-level orchestration.
- ``ReversibleVault`` — reversible pseudonymization storage.
- ``detect_all`` — run every detector at once.
- ``DetectionResult`` / ``RiskLevel`` — core data types.
- ``tokenize`` / ``redact`` / ``hashed`` — substitution primitives.
"""
from k_pii.analytics import (
    AttributeClass, CombinedRiskReport,
    classify_attribute, score_combined_risk,
    KAnonymityReport, k_anonymity, evaluate_dataset,
)
from k_pii.integrations import (
    SecondaryDetector,
    MockSecondaryDetector,
    MergeMode,
    merge_detections,
    get_privacy_filter_adapter,
)
from k_pii.anonymizer import Anonymizer, AnonymizationResult, DetectionRecord
from k_pii.core.modes import Action, ProcessingMode
from k_pii.core.types import DetectionResult, RiskLevel
from k_pii.detect import detect_all
from k_pii.modes.fpe import fpe
from k_pii.modes.hashed import hashed
from k_pii.modes.partial import partial, mask_value
from k_pii.modes.redact import redact
from k_pii.modes.tokenize import tokenize
from k_pii.vault.reversible import ReversibleVault, VaultEntry

__version__ = "0.3.0"

__all__ = [
    "Anonymizer",
    "AnonymizationResult",
    "DetectionRecord",
    "Action",
    "ProcessingMode",
    "DetectionResult",
    "RiskLevel",
    "detect_all",
    "tokenize",
    "redact",
    "hashed",
    "partial",
    "mask_value",
    "fpe",
    "ReversibleVault",
    "VaultEntry",
    # analytics
    "AttributeClass",
    "CombinedRiskReport",
    "classify_attribute",
    "score_combined_risk",
    "KAnonymityReport",
    "k_anonymity",
    "evaluate_dataset",
    # integrations
    "SecondaryDetector",
    "MockSecondaryDetector",
    "MergeMode",
    "merge_detections",
    "get_privacy_filter_adapter",
    "__version__",
]
