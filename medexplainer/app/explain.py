"""
Text simplification and explanation module for MedExplainer.
"""

import re
from typing import List, Dict, Optional
from .models import StudyResult, StudyType, ConfidenceLevel


class MedicalExplainer:
    """Simplifies medical text and generates user-friendly explanations."""
    
    # Mapping from study types to confidence levels
    STUDY_TYPE_CONFIDENCE = {
        StudyType.META_ANALYSIS: ConfidenceLevel.HIGH,
        StudyType.SYSTEMATIC_REVIEW: ConfidenceLevel.HIGH,
        StudyType.RANDOMIZED_CONTROLLED_TRIAL: ConfidenceLevel.HIGH,
        StudyType.COHORT_STUDY: ConfidenceLevel.MODERATE,
        StudyType.CASE_CONTROL_STUDY: ConfidenceLevel.MODERATE,
        StudyType.CROSS_SECTIONAL_STUDY: ConfidenceLevel.LOW,
        StudyType.CASE_REPORT: ConfidenceLevel.VERY_LOW,
        StudyType.CASE_SERIES: ConfidenceLevel.VERY_LOW,
        StudyType.ANIMAL_STUDY: ConfidenceLevel.VERY_LOW,
        StudyType.IN_VITRO_STUDY: ConfidenceLevel.VERY_LOW,
        StudyType.REVIEW: ConfidenceLevel.MODERATE,
        StudyType.OTHER: ConfidenceLevel.LOW
    }
    
    # Common medical terms and their simple explanations (English)
    MEDICAL_TERMS_EN = {
        # Study types
        "meta-analysis": "a study that combines results from multiple studies",
        "systematic review": "a thorough summary of all available evidence on a topic",
        "randomized controlled trial": "a study where participants are randomly assigned to different treatments",
        "cohort study": "a study that follows a group of people over time",
        "case-control study": "a study that compares people with a disease to people without it",
        "cross-sectional study": "a study that looks at data from a single point in time",
        "placebo": "a fake treatment used in studies to compare against real treatments",
        "double-blind": "a study where neither participants nor researchers know who gets which treatment",
        
        # Common conditions
        "hypertension": "high blood pressure",
        "diabetes": "a condition where blood sugar levels are too high",
        "depression": "a mental health condition with persistent sadness",
        "anxiety": "a mental health condition with excessive worry",
        "cardiovascular disease": "heart and blood vessel diseases",
        "obesity": "excessive body fat",
        "asthma": "a condition that makes breathing difficult",
        "arthritis": "joint inflammation and pain",
        
        # Treatments
        "pharmacotherapy": "treatment with medications",
        "psychotherapy": "treatment through talking with a mental health professional",
        "cognitive behavioral therapy": "a type of talk therapy that helps change negative thought patterns",
        "surgery": "medical operation",
        "radiotherapy": "treatment with radiation",
        "chemotherapy": "drug treatment for cancer",
        
        # Measurements
        "systolic blood pressure": "blood pressure when the heart beats",
        "diastolic blood pressure": "blood pressure when the heart rests between beats",
        "body mass index": "a measure of body fat based on height and weight",
        "glucose": "sugar in the blood",
        "cholesterol": "a type of fat in the blood",
        
        # Statistical terms
        "statistically significant": "a result that is unlikely to be due to chance",
        "p-value": "a number that shows how likely a result is due to chance",
        "confidence interval": "a range of values that likely contains the true effect",
        "hazard ratio": "a measure of how often a particular event happens in one group compared to another",
        "odds ratio": "a measure of association between an exposure and an outcome",
        "relative risk": "the probability of an event occurring in one group compared to another",
        
        # Other
        "prevalence": "how common a condition is in a population",
        "incidence": "how often new cases of a condition occur",
        "mortality": "death rate",
        "morbidity": "disease rate",
        "etiology": "the causes of a disease",
        "pathogenesis": "how a disease develops",
        "prognosis": "the likely course and outcome of a disease",
        "diagnosis": "identifying a disease",
        "prophylaxis": "prevention of disease",
        "efficacy": "how well a treatment works in ideal conditions",
        "effectiveness": "how well a treatment works in real-world conditions",
        "adverse effects": "side effects",
        "contraindications": "reasons not to use a treatment"
    }
    
    # Common medical terms and their simple explanations (Russian)
    MEDICAL_TERMS_RU = {
        # Типы исследований
        "мета-анализ": "исследование, объединяющее результаты нескольких исследований",
        "систематический обзор": "тщательный обзор всех доступных данных по теме",
        "рандомизированное контролируемое исследование": "исследование, где участники случайным образом распределяются по группам",
        "когортное исследование": "исследование, которое наблюдает за группой людей в течение времени",
        "исследование случай-контроль": "исследование, сравнивающее людей с заболеванием и без него",
        "поперечное исследование": "исследование, которое анализирует данные в один момент времени",
        "плацебо": "фиктивное лечение, используемое для сравнения",
        "двойное слепое": "исследование, где ни участники, ни исследователи не знают, кто получает какое лечение",
        
        # Распространенные заболевания
        "гипертония": "повышенное артериальное давление",
        "гипертонии": "повышенное артериальное давление",
        "диабет": "заболевание, при котором уровень сахара в крови слишком высок",
        "депрессия": "состояние с устойчивой грустью и потерей интереса к жизни",
        "тревожность": "состояние с чрезмерным беспокойством",
        "сердечно-сосудистые заболевания": "заболевания сердца и сосудов",
        "ожирение": "чрезмерное накопление жира в организме",
        "астма": "заболевание, вызывающее затруднение дыхания",
        "артрит": "воспаление и боль в суставах",
        
        # Методы лечения
        "фармакотерапия": "лечение лекарственными препаратами",
        "психотерапия": "лечение через разговоры с психологом",
        "когнитивно-поведенческая терапия": "вид психотерапии, помогающий изменить негативные мысли",
        "хирургия": "хирургическая операция",
        "лучевая терапия": "лечение с помощью радиации",
        "химиотерапия": "лечение рака лекарствами",
        
        # Измерения
        "систолическое артериальное давление": "давление в артериях при сокращении сердца",
        "диастолическое артериальное давление": "давление в артериях между сокращениями сердца",
        "индекс массы тела": "показатель, оценивающий вес человека по отношению к его росту",
        "глюкоза": "сахар в крови",
        "холестерин": "вид жира в крови",
        
        # Статистические термины
        "статистически значимый": "результат, который вряд ли является случайностью",
        "значение p": "показатель, насколько результат может быть случайным",
        "доверительный интервал": "диапазон значений, который, вероятно, содержит истинный эффект",
        "риск": "вероятность возникновения события",
        "отношение шансов": "показатель связи между фактором и исходом",
        "относительный риск": "вероятность события в одной группе по сравнению с другой",
        
        # Другие
        "распространенность": "насколько часто встречается заболевание в популяции",
        "заболеваемость": "как часто появляются новые случаи заболевания",
        "смертность": "уровень смертности",
        "заболеваемость": "уровень заболеваний",
        "этиология": "причины заболевания",
        "патогенез": "как развивается заболевание",
        "прогноз": "вероятный исход заболевания",
        "диагноз": "определение заболевания",
        "профилактика": "предотвращение заболевания",
        "эффективность": "насколько хорошо работает лечение в идеальных условиях",
        "результативность": "насколько хорошо работает лечение в реальных условиях",
        "побочные эффекты": "нежелательные последствия лечения",
        "противопоказания": "причины, по которым не следует использовать лечение"
    }
    
    def __init__(self):
        self.terms_en = self.MEDICAL_TERMS_EN
        self.terms_ru = self.MEDICAL_TERMS_RU
    
    def simplify_text(self, text: str, language: str = "en") -> str:
        """
        Simplify medical text by replacing complex terms with simpler explanations.
        
        Args:
            text: The text to simplify
            language: Language for simplification (en/ru)
            
        Returns:
            Simplified text
        """
        if not text:
            return ""
        
        terms = self.terms_en if language == "en" else self.terms_ru
        
        # Replace terms while preserving case
        simplified = text
        for term, explanation in terms.items():
            # Create case-insensitive pattern
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            # Replace with explanation, preserving original case for the term
            simplified = pattern.sub(explanation, simplified)
        
        return simplified
    
    def generate_simple_explanation(self, study: Dict, language: str = "en") -> str:
        """
        Generate a simple explanation for a study.
        
        Args:
            study: Study data dictionary
            language: Language for explanation (en/ru)
            
        Returns:
            Simple explanation string
        """
        study_type = study.get("study_type", StudyType.OTHER)
        title = study.get("title", "")
        abstract = study.get("abstract", "")
        participants = study.get("participants")
        
        # Get confidence level based on study type
        confidence = self.STUDY_TYPE_CONFIDENCE.get(study_type, ConfidenceLevel.LOW)
        
        # Generate base explanation based on study type
        if language == "en":
            type_explanations = {
                StudyType.META_ANALYSIS: "This is a meta-analysis, which combines results from multiple studies to provide stronger evidence.",
                StudyType.SYSTEMATIC_REVIEW: "This is a systematic review, which thoroughly summarizes all available evidence on the topic.",
                StudyType.RANDOMIZED_CONTROLLED_TRIAL: "This is a randomized controlled trial, the gold standard for testing treatments.",
                StudyType.COHORT_STUDY: "This is a cohort study, which follows a group of people over time to see how often a disease or condition occurs.",
                StudyType.CASE_CONTROL_STUDY: "This is a case-control study, which compares people with a disease to people without it.",
                StudyType.CROSS_SECTIONAL_STUDY: "This is a cross-sectional study, which looks at data from a single point in time.",
                StudyType.CASE_REPORT: "This is a case report, which describes a single patient's experience.",
                StudyType.CASE_SERIES: "This is a case series, which describes the experiences of a small group of patients.",
                StudyType.ANIMAL_STUDY: "This is an animal study, which tests treatments on animals before human trials.",
                StudyType.IN_VITRO_STUDY: "This is a laboratory study, which tests treatments on cells or tissues in a controlled environment.",
                StudyType.REVIEW: "This is a review article, which summarizes existing research on a topic.",
                StudyType.OTHER: "This study provides information about the topic."
            }
            confidence_explanations = {
                ConfidenceLevel.HIGH: "The evidence is high quality.",
                ConfidenceLevel.MODERATE: "The evidence is moderate quality.",
                ConfidenceLevel.LOW: "The evidence is low quality.",
                ConfidenceLevel.VERY_LOW: "The evidence is very low quality."
            }
            participants_text = f" It involved {participants} participants." if participants else ""
            
            explanation = f"{type_explanations.get(study_type, '')} {confidence_explanations.get(confidence, '')}{participants_text}"
        else:  # Russian
            type_explanations = {
                StudyType.META_ANALYSIS: "Это мета-анализ, который объединяет результаты нескольких исследований для получения более достоверных данных.",
                StudyType.SYSTEMATIC_REVIEW: "Это систематический обзор, который тщательно обобщает все доступные данные по теме.",
                StudyType.RANDOMIZED_CONTROLLED_TRIAL: "Это рандомизированное контролируемое исследование — золотой стандарт для тестирования методов лечения.",
                StudyType.COHORT_STUDY: "Это когортное исследование, которое наблюдает за группой людей в течение времени, чтобы увидеть, как часто возникает заболевание или состояние.",
                StudyType.CASE_CONTROL_STUDY: "Это исследование случай-контроль, которое сравнивает людей с заболеванием и без него.",
                StudyType.CROSS_SECTIONAL_STUDY: "Это поперечное исследование, которое анализирует данные в один момент времени.",
                StudyType.CASE_REPORT: "Это описание клинического случая, которое описывает опыт одного пациента.",
                StudyType.CASE_SERIES: "Это серия клинических случаев, которая описывает опыт небольшой группы пациентов.",
                StudyType.ANIMAL_STUDY: "Это исследование на животных, которое тестирует методы лечения перед испытаниями на людях.",
                StudyType.IN_VITRO_STUDY: "Это лабораторное исследование, которое тестирует методы лечения на клетках или тканях в контролируемой среде.",
                StudyType.REVIEW: "Это обзорная статья, которая обобщает существующие исследования по теме.",
                StudyType.OTHER: "Это исследование предоставляет информацию по теме."
            }
            confidence_explanations = {
                ConfidenceLevel.HIGH: "Доказательства высокого качества.",
                ConfidenceLevel.MODERATE: "Доказательства среднего качества.",
                ConfidenceLevel.LOW: "Доказательства низкого качества.",
                ConfidenceLevel.VERY_LOW: "Доказательства очень низкого качества."
            }
            participants_text = f" В нем приняли участие {participants} человек." if participants else ""
            
            explanation = f"{type_explanations.get(study_type, '')} {confidence_explanations.get(confidence, '')}{participants_text}"
        
        # Simplify the title and add to explanation
        simplified_title = self.simplify_text(title, language)
        if simplified_title:
            explanation = f"{simplified_title}. {explanation}"
        
        return explanation.strip()
    
    def extract_key_findings(self, abstract: str, language: str = "en") -> List[str]:
        """
        Extract key findings from an abstract.
        
        Args:
            abstract: The abstract text
            language: Language for findings (en/ru)
            
        Returns:
            List of key findings in simple terms
        """
        if not abstract:
            return []
        
        # Simple heuristic: look for sentences with keywords like "found", "showed", "demonstrated"
        # This is a placeholder - in a real implementation, you'd use more sophisticated NLP
        findings = []
        
        if language == "en":
            keywords = ["found", "showed", "demonstrated", "revealed", "indicated", 
                       "suggested", "concluded", "proved", "confirmed", "identified"]
        else:  # Russian
            keywords = ["обнаружено", "показано", "демонстрирует", "выявлено", "указано",
                       "предполагает", "заключили", "доказано", "подтверждено", "выявлены"]
        
        sentences = re.split(r'(?<=[.!?])\s+', abstract)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in keywords):
                simplified = self.simplify_text(sentence, language)
                findings.append(simplified)
        
        return findings[:3]  # Return at most 3 key findings
    
    def generate_summary(self, results: List[Dict], query: str, language: str = "en") -> str:
        """
        Generate a summary of search results.
        
        Args:
            results: List of study results
            query: Original search query
            language: Language for summary (en/ru)
            
        Returns:
            Summary string
        """
        if not results:
            if language == "en":
                return f"No studies found for '{query}'."
            else:
                return f"По запросу '{query}' исследования не найдены."
        
        # Count by study type
        type_counts = {}
        for result in results:
            study_type = result.get("study_type", StudyType.OTHER)
            type_counts[study_type] = type_counts.get(study_type, 0) + 1
        
        # Get high-quality studies
        high_quality_types = [
            StudyType.META_ANALYSIS, 
            StudyType.SYSTEMATIC_REVIEW, 
            StudyType.RANDOMIZED_CONTROLLED_TRIAL
        ]
        high_quality_count = sum(
            count for study_type, count in type_counts.items() 
            if study_type in high_quality_types
        )
        
        if language == "en":
            if high_quality_count > 0:
                return f"Found {len(results)} studies for '{query}', including {high_quality_count} high-quality studies (meta-analyses, systematic reviews, or randomized trials)."
            else:
                return f"Found {len(results)} studies for '{query}'. Most are lower-quality evidence (observational studies, case reports)."
        else:
            if high_quality_count > 0:
                return f"По запросу '{query}' найдено {len(results)} исследований, включая {high_quality_count} высококачественных (мета-анализы, систематические обзоры или рандомизированные испытания)."
            else:
                return f"По запросу '{query}' найдено {len(results)} исследований. Большинство из них — исследования с низким уровнем доказательности (наблюдательные исследования, описания случаев)."


# Singleton instance
medical_explainer = MedicalExplainer()
