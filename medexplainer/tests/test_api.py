"""
Tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.models import StudyType, ConfidenceLevel


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_pubmed_searcher():
    """Mock PubMedSearcher for API tests."""
    with patch('app.main.pubmed_searcher') as mock:
        yield mock


@pytest.fixture
def mock_medical_explainer():
    """Mock MedicalExplainer for API tests."""
    with patch('app.main.medical_explainer') as mock:
        yield mock


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root(self, client):
        """Test root endpoint returns basic info."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.json()["name"] == "MedExplainer"
        assert response.json()["version"] == "0.1.0"
        assert "docs" in response.json()


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["version"] == "0.1.0"
        assert "services" in response.json()


class TestSearchEndpoint:
    """Test search endpoint."""
    
    @patch('app.main.pubmed_searcher')
    @patch('app.main.medical_explainer')
    def test_search_post_success(self, mock_explainer, mock_searcher, client):
        """Test successful POST search."""
        # Mock search results
        mock_searcher.search.return_value = [
            {
                "pmid": "12345678",
                "title": "Test Meta-Analysis",
                "abstract": "Test abstract",
                "authors": ["Smith J"],
                "journal": "Test Journal",
                "publication_date": "2023-01-01",
                "study_type": StudyType.META_ANALYSIS,
                "participants": 1000,
                "doi": "10.1234/test",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/"
            }
        ]
        
        # Mock explainer
        mock_explainer.generate_simple_explanation.return_value = "This is a meta-analysis with high quality evidence."
        mock_explainer.extract_key_findings.return_value = ["Key finding 1", "Key finding 2"]
        mock_explainer.generate_summary.return_value = "Found 1 high-quality study."
        mock_explainer.STUDY_TYPE_CONFIDENCE = {
            StudyType.META_ANALYSIS: ConfidenceLevel.HIGH
        }
        
        response = client.post("/search", json={
            "query": "vitamin D depression",
            "study_types": ["meta_analysis"],
            "language": "en",
            "limit": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "vitamin D depression"
        assert data["total_results"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["pmid"] == "12345678"
        assert data["results"][0]["simple_explanation"] == "This is a meta-analysis with high quality evidence."
        assert data["summary"] == "Found 1 high-quality study."
    
    @patch('app.main.pubmed_searcher')
    @patch('app.main.medical_explainer')
    def test_search_get_success(self, mock_explainer, mock_searcher, client):
        """Test successful GET search."""
        mock_searcher.search.return_value = []
        mock_explainer.generate_summary.return_value = "No studies found for 'test'."
        
        response = client.get("/search", params={
            "query": "test",
            "study_types": ["meta_analysis"],
            "language": "en",
            "limit": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert data["total_results"] == 0
        assert data["summary"] == "No studies found for 'test'."
    
    @patch('app.main.pubmed_searcher')
    def test_search_empty_query(self, mock_searcher, client):
        """Test search with empty query."""
        response = client.post("/search", json={
            "query": "ab",
            "study_types": ["meta_analysis"],
            "language": "en",
            "limit": 10
        })
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.main.pubmed_searcher')
    @patch('app.main.medical_explainer')
    def test_search_with_filters(self, mock_explainer, mock_searcher, client):
        """Test search with filters."""
        mock_searcher.search.return_value = [
            {
                "pmid": "12345678",
                "title": "Test Study",
                "abstract": "Test",
                "authors": [],
                "journal": "Test",
                "publication_date": "2023-01-01",
                "study_type": StudyType.RANDOMIZED_CONTROLLED_TRIAL,
                "participants": 500,
                "doi": None,
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/"
            }
        ]
        
        mock_explainer.generate_simple_explanation.return_value = "Test explanation"
        mock_explainer.extract_key_findings.return_value = []
        mock_explainer.generate_summary.return_value = "Found 1 study."
        mock_explainer.STUDY_TYPE_CONFIDENCE = {
            StudyType.RANDOMIZED_CONTROLLED_TRIAL: ConfidenceLevel.HIGH
        }
        
        response = client.post("/search", json={
            "query": "test",
            "study_types": ["randomized_controlled_trial"],
            "min_participants": 100,
            "publication_year": 2023,
            "language": "en",
            "limit": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1
        
        # Check that search was called with correct parameters
        mock_searcher.search.assert_called_once()
        call_args = mock_searcher.search.call_args
        assert call_args[1]["query"] == "test"
        assert call_args[1]["publication_year"] == 2023
    
    @patch('app.main.pubmed_searcher')
    def test_search_api_error(self, mock_searcher, client):
        """Test search with API error."""
        mock_searcher.search.side_effect = Exception("API Error")
        
        response = client.post("/search", json={
            "query": "test",
            "study_types": ["meta_analysis"],
            "language": "en",
            "limit": 10
        })
        
        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()


class TestStudyDetailsEndpoint:
    """Test study details endpoint."""
    
    @patch('app.main.pubmed_searcher')
    @patch('app.main.medical_explainer')
    def test_get_study_details_success(self, mock_explainer, mock_searcher, client):
        """Test getting study details by PMID."""
        mock_searcher.get_study_details.return_value = {
            "pmid": "12345678",
            "title": "Test Study",
            "abstract": "Test abstract",
            "authors": ["Smith J"],
            "journal": "Test Journal",
            "publication_date": "2023-01-01",
            "study_type": StudyType.META_ANALYSIS,
            "participants": 1000,
            "doi": "10.1234/test",
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/"
        }
        
        mock_explainer.generate_simple_explanation.return_value = "Test explanation"
        mock_explainer.extract_key_findings.return_value = ["Finding 1"]
        mock_explainer.STUDY_TYPE_CONFIDENCE = {
            StudyType.META_ANALYSIS: ConfidenceLevel.HIGH
        }
        
        response = client.get("/study/12345678")
        
        assert response.status_code == 200
        data = response.json()
        assert data["pmid"] == "12345678"
        assert data["title"] == "Test Study"
        assert data["simple_explanation"] == "Test explanation"
    
    @patch('app.main.pubmed_searcher')
    def test_get_study_details_not_found(self, mock_searcher, client):
        """Test getting non-existent study."""
        mock_searcher.get_study_details.return_value = None
        
        response = client.get("/study/99999999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestWebEndpoint:
    """Test web interface endpoint."""
    
    def test_web_endpoint(self, client):
        """Test web endpoint returns interface info."""
        response = client.get("/web")
        
        assert response.status_code == 200
        assert "MedExplainer Web Interface" in response.json()["message"]
