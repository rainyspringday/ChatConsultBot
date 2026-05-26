from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.intent_detection_service import IntentDetectionService


def test_weather_is_report_not_framework():
    detector = IntentDetectionService()
    assert detector.detect("What is the weather tomorrow?") == "REPORT"


def test_framework_explanation_detected():
    detector = IntentDetectionService()
    assert detector.detect("Explain SWOT") == "FRAMEWORK"
    assert detector.detect("Define Porter's Five Forces") == "FRAMEWORK"


def test_analysis_detected():
    detector = IntentDetectionService()
    assert detector.detect("Which framework should I use to address churn?") == "ANALYSIS"
    assert detector.detect("Recommend a framework for my business problem") == "ANALYSIS"


def test_unknown_framework_not_marked_framework():
    detector = IntentDetectionService()
    # intent remains REPORT; whitelist rejection happens in RAG pipeline
    assert detector.detect("Explain the GE–McKinsey Matrix") == "REPORT"

