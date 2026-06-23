"""
Data models for MedExplainer.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class StudyType(str, Enum):
    """Types of medical studies, ordered by evidence quality."""
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    RANDOMIZED_CONTROLLED_TRIAL = "randomized_controlled_trial"
    COHORT_STUDY = "cohort_study"
    CASE_CONTROL_STUDY = "case_control_study"
    CROSS_SECTIONAL_STUDY = "cross_sectional_study"
    CASE_REPORT = "case_report"
    CASE_SERIES = "case_series"
    ANIMAL_STUDY = "animal_study"
    IN_VITRO_STUDY = "in_vitro_study"
    REVIEW = "review"
    OTHER = "other"


class ConfidenceLevel(str, Enum):
    """Confidence levels based on GRADE approach."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


class StudyResult(BaseModel):
    """Represents a single study result from search."""
    
    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Study title")
    abstract: Optional[str] = Field(None, description="Study abstract")
    authors: List[str] = Field(default_factory=list, description="List of authors")
    journal: Optional[str] = Field(None, description="Journal name")
    publication_date: Optional[str] = Field(None, description="Publication date (YYYY-MM-DD)")
    study_type: StudyType = Field(StudyType.OTHER, description="Type of study")
    participants: Optional[int] = Field(None, description="Number of participants")
    confidence: ConfidenceLevel = Field(ConfidenceLevel.LOW, description="Confidence level")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    url: str = Field(..., description="URL to the study")
    simple_explanation: Optional[str] = Field(None, description="Simplified explanation for users")
    key_findings: List[str] = Field(default_factory=list, description="Key findings in simple terms")


class SearchRequest(BaseModel):
    """Request model for search endpoint."""
    
    query: str = Field(..., min_length=3, description="Search query")
    study_types: List[StudyType] = Field(
        default=[StudyType.META_ANALYSIS, StudyType.RANDOMIZED_CONTROLLED_TRIAL],
        description="Filter by study types"
    )
    min_participants: Optional[int] = Field(None, description="Minimum number of participants")
    publication_year: Optional[int] = Field(None, description="Filter by publication year")
    language: str = Field(default="en", description="Language for simple explanations (en/ru)")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")


class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    
    query: str
    total_results: int
    results: List[StudyResult]
    summary: Optional[str] = Field(None, description="Overall summary of results")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    status: str = "healthy"
    version: str = "0.1.0"
    services: dict = {}
