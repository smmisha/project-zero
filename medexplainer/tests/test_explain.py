"""
Tests for text simplification and explanation functionality.
"""

import pytest
from app.explain import MedicalExplainer, medical_explainer
from app.models import StudyType, ConfidenceLevel


@pytest.fixture
def explainer():
    """Create a MedicalExplainer instance for testing."""
    return MedicalExplainer()


class TestMedicalExplainer:
    """Test cases for MedicalExplainer class."""
    
    def test_simplify_text_english(self, explainer):
        """Test text simplification in English."""
        text = "This is a meta-analysis of hypertension treatment."
        simplified = explainer.simplify_text(text, "en")
        
        assert "a study that combines results from multiple studies" in simplified
        assert "high blood pressure" in simplified
    
    def test_simplify_text_russian(self, explainer):
        """Test text simplification in Russian."""
        text = "Это мета-анализ лечения гипертонии."
        simplified = explainer.simplify_text(text, "ru")
        
        assert "исследование, объединяющее результаты нескольких исследований" in simplified
        assert "повышенное артериальное давление" in simplified
    
    def test_simplify_text_empty(self, explainer):
        """Test simplification of empty text."""
        assert explainer.simplify_text("", "en") == ""
        assert explainer.simplify_text(None, "en") == ""
    
    def test_generate_simple_explanation_english(self, explainer):
        """Test generating simple explanation in English."""
        study = {
            "study_type": StudyType.META_ANALYSIS,
            "title": "Meta-analysis of vitamin D and depression",
            "abstract": "This meta-analysis found that vitamin D supplementation reduces depression symptoms.",
            "participants": 10000
        }
        
        explanation = explainer.generate_simple_explanation(study, "en")
        
        assert "Meta-analysis" in explanation or "meta-analysis" in explanation
        assert "10000" in explanation
        assert "high quality" in explanation.lower()
    
    def test_generate_simple_explanation_russian(self, explainer):
        """Test generating simple explanation in Russian."""
        study = {
            "study_type": StudyType.RANDOMIZED_CONTROLLED_TRIAL,
            "title": "Рандомизированное контролируемое исследование витамина D",
            "abstract": "Это исследование показало эффективность витамина D.",
            "participants": 500
        }
        
        explanation = explainer.generate_simple_explanation(study, "ru")
        
        assert "рандомизированное контролируемое исследование" in explanation.lower() or "рки" in explanation.lower()
        assert "500" in explanation
        assert "золотой стандарт" in explanation.lower()
    
    def test_generate_simple_explanation_no_participants(self, explainer):
        """Test explanation without participants."""
        study = {
            "study_type": StudyType.SYSTEMATIC_REVIEW,
            "title": "Systematic review of treatments",
            "abstract": "A comprehensive review.",
            "participants": None
        }
        
        explanation = explainer.generate_simple_explanation(study, "en")
        
        assert "Systematic review" in explanation or "systematic review" in explanation
        assert "participants" not in explanation.lower()
    
    def test_extract_key_findings_english(self, explainer):
        """Test extracting key findings in English."""
        abstract = "We found that vitamin D reduces depression. This study showed significant results. We demonstrated the effect."
        
        findings = explainer.extract_key_findings(abstract, "en")
        
        assert len(findings) > 0
        assert any("vitamin D" in finding.lower() for finding in findings)
    
    def test_extract_key_findings_russian(self, explainer):
        """Test extracting key findings in Russian."""
        abstract = "Мы обнаружили, что витамин D снижает депрессию. Это исследование показало значимые результаты."
        
        findings = explainer.extract_key_findings(abstract, "ru")
        
        assert len(findings) > 0
        assert any("витамин D" in finding.lower() or "депрессию" in finding.lower() for finding in findings)
    
    def test_extract_key_findings_empty(self, explainer):
        """Test extracting findings from empty abstract."""
        assert explainer.extract_key_findings("", "en") == []
        assert explainer.extract_key_findings(None, "en") == []
    
    def test_generate_summary_with_results(self, explainer):
        """Test generating summary with results."""
        results = [
            {"study_type": StudyType.META_ANALYSIS},
            {"study_type": StudyType.RANDOMIZED_CONTROLLED_TRIAL},
            {"study_type": StudyType.COHORT_STUDY}
        ]
        
        summary_en = explainer.generate_summary(results, "vitamin D", "en")
        assert "3 studies" in summary_en
        assert "high-quality" in summary_en.lower()
        
        summary_ru = explainer.generate_summary(results, "витамин D", "ru")
        assert "3" in summary_ru
        assert "высококачественных" in summary_ru.lower()
    
    def test_generate_summary_no_results(self, explainer):
        """Test generating summary with no results."""
        summary_en = explainer.generate_summary([], "test query", "en")
        assert "No studies found" in summary_en
        
        summary_ru = explainer.generate_summary([], "тестовый запрос", "ru")
        assert "не найдены" in summary_ru.lower()
    
    def test_generate_summary_only_low_quality(self, explainer):
        """Test generating summary with only low-quality studies."""
        results = [
            {"study_type": StudyType.CASE_REPORT},
            {"study_type": StudyType.CASE_SERIES}
        ]
        
        summary = explainer.generate_summary(results, "test", "en")
        assert "lower-quality" in summary.lower() or "low" in summary.lower()
    
    def test_study_type_confidence_mapping(self, explainer):
        """Test that study types are correctly mapped to confidence levels."""
        assert explainer.STUDY_TYPE_CONFIDENCE[StudyType.META_ANALYSIS] == ConfidenceLevel.HIGH
        assert explainer.STUDY_TYPE_CONFIDENCE[StudyType.SYSTEMATIC_REVIEW] == ConfidenceLevel.HIGH
        assert explainer.STUDY_TYPE_CONFIDENCE[StudyType.RANDOMIZED_CONTROLLED_TRIAL] == ConfidenceLevel.HIGH
        assert explainer.STUDY_TYPE_CONFIDENCE[StudyType.COHORT_STUDY] == ConfidenceLevel.MODERATE
        assert explainer.STUDY_TYPE_CONFIDENCE[StudyType.CASE_REPORT] == ConfidenceLevel.VERY_LOW
        assert explainer.STUDY_TYPE_CONFIDENCE[StudyType.ANIMAL_STUDY] == ConfidenceLevel.VERY_LOW
