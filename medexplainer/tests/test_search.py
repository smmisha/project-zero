"""
Tests for PubMed search functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.search import PubMedSearcher, pubmed_searcher
from app.models import StudyType


@pytest.fixture
def mock_searcher():
    """Create a mock PubMedSearcher for testing."""
    return PubMedSearcher()


class TestPubMedSearcher:
    """Test cases for PubMedSearcher class."""
    
    @patch('app.search.requests.Session.get')
    def test_search_success(self, mock_get, mock_searcher):
        """Test successful search with mock API response."""
        # Mock response for esearch
        esearch_response = MagicMock()
        esearch_response.json.return_value = {
            "esearchresult": {
                "idlist": ["12345678", "87654321"]
            }
        }
        esearch_response.raise_for_status.return_value = None
        
        # Mock response for efetch
        efetch_response = MagicMock()
        efetch_response.json.return_value = {
            "pubmeddata": {
                "article": {
                    "12345678": {
                        "medlinecitation": {
                            "pmid": "12345678",
                            "articletitle": "Test Study Title",
                            "abstract": {
                                "abstracttext": ["This is a test abstract."]
                            },
                            "authorlist": [
                                {"author": {"name": "Smith J"}},
                                {"author": {"name": "Doe A"}}
                            ],
                            "journal": {
                                "title": "Test Journal",
                                "journalissue": {
                                    "pubdate": {
                                        "year": "2023",
                                        "month": "05",
                                        "day": "15"
                                    }
                                }
                            },
                            "elocationid": "doi:10.1234/test"
                        }
                    },
                    "87654321": {
                        "medlinecitation": {
                            "pmid": "87654321",
                            "articletitle": "Randomized controlled trial of test drug",
                            "abstract": {
                                "abstracttext": ["This is a randomized controlled trial with 100 participants."]
                            },
                            "authorlist": [],
                            "journal": {
                                "title": "Another Journal",
                                "journalissue": {
                                    "pubdate": {
                                        "year": "2022",
                                        "month": "Jan",
                                        "day": "01"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        efetch_response.raise_for_status.return_value = None
        
        # Set up mock to return different responses based on endpoint
        def side_effect(url, **kwargs):
            if "esearch" in url:
                return esearch_response
            elif "efetch" in url:
                return efetch_response
            return MagicMock()
        
        mock_get.side_effect = side_effect
        
        # Call search
        results = mock_searcher.search("test query", max_results=2)
        
        # Assertions
        assert len(results) == 2
        assert results[0]["pmid"] == "12345678"
        assert results[0]["title"] == "Test Study Title"
        assert results[0]["authors"] == ["Smith J", "Doe A"]
        assert results[0]["journal"] == "Test Journal"
        assert results[0]["publication_date"] == "2023-05-15"
        assert results[0]["doi"] == "10.1234/test"
        assert results[0]["url"] == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
        
        # Check study type detection
        assert results[1]["study_type"] == StudyType.RANDOMIZED_CONTROLLED_TRIAL
        assert results[1]["participants"] == 100
    
    @patch('app.search.requests.Session.get')
    def test_search_no_results(self, mock_get, mock_searcher):
        """Test search with no results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "esearchresult": {
                "idlist": []
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        results = mock_searcher.search("nonexistent query")
        
        assert results == []
    
    @patch('app.search.requests.Session.get')
    def test_search_api_error(self, mock_get, mock_searcher):
        """Test search with API error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_get.return_value = mock_response
        
        results = mock_searcher.search("test query")
        
        assert results == []
    
    def test_detect_study_type(self, mock_searcher):
        """Test study type detection from text."""
        # Test meta-analysis
        assert mock_searcher._detect_study_type(
            "Meta-analysis of vitamin D", ""
        ) == StudyType.META_ANALYSIS
        
        # Test systematic review
        assert mock_searcher._detect_study_type(
            "Systematic review of treatments", ""
        ) == StudyType.SYSTEMATIC_REVIEW
        
        # Test RCT
        assert mock_searcher._detect_study_type(
            "Randomized controlled trial", ""
        ) == StudyType.RANDOMIZED_CONTROLLED_TRIAL
        
        # Test cohort study
        assert mock_searcher._detect_study_type(
            "Cohort study of patients", ""
        ) == StudyType.COHORT_STUDY
        
        # Test case-control
        assert mock_searcher._detect_study_type(
            "Case-control study", ""
        ) == StudyType.CASE_CONTROL_STUDY
        
        # Test cross-sectional
        assert mock_searcher._detect_study_type(
            "Cross-sectional study", ""
        ) == StudyType.CROSS_SECTIONAL_STUDY
        
        # Test case report
        assert mock_searcher._detect_study_type(
            "Case report", ""
        ) == StudyType.CASE_REPORT
        
        # Test animal study
        assert mock_searcher._detect_study_type(
            "Animal study in mice", ""
        ) == StudyType.ANIMAL_STUDY
        
        # Test in vitro
        assert mock_searcher._detect_study_type(
            "In vitro study", ""
        ) == StudyType.IN_VITRO_STUDY
        
        # Test default
        assert mock_searcher._detect_study_type(
            "Some other study", ""
        ) == StudyType.OTHER
    
    def test_extract_participants(self, mock_searcher):
        """Test participant extraction from abstract."""
        # Test n = 100
        assert mock_searcher._extract_participants(
            "We enrolled n = 100 participants"
        ) == 100
        
        # Test with comma
        assert mock_searcher._extract_participants(
            "The study included 1,000 subjects"
        ) == 1000
        
        # Test sample size
        assert mock_searcher._extract_participants(
            "Sample size: 500"
        ) == 500
        
        # Test enrolled
        assert mock_searcher._extract_participants(
            "We enrolled 250 patients"
        ) == 250
        
        # Test no participants
        assert mock_searcher._extract_participants(
            "No participants mentioned"
        ) is None
    
    def test_parse_pubmed_date(self, mock_searcher):
        """Test date parsing from PubMed format."""
        # Test with numeric month
        assert mock_searcher._parse_pubmed_date({
            "year": "2023",
            "month": "05",
            "day": "15"
        }) == "2023-05-15"
        
        # Test with month name
        assert mock_searcher._parse_pubmed_date({
            "year": "2022",
            "month": "Jan",
            "day": "01"
        }) == "2022-01-01"
        
        # Test with missing day
        assert mock_searcher._parse_pubmed_date({
            "year": "2021",
            "month": "12"
        }) == "2021-12-01"
        
        # Test with missing month
        assert mock_searcher._parse_pubmed_date({
            "year": "2020"
        }) == "2020-01-01"
        
        # Test with no year
        assert mock_searcher._parse_pubmed_date({}) is None
