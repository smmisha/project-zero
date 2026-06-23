"""
PubMed search module for MedExplainer.
"""

import requests
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
from .models import StudyResult, StudyType, ConfidenceLevel
from .config import settings


class PubMedSearcher:
    """Search and retrieve studies from PubMed API."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    def __init__(self):
        self.email = settings.pubmed_email
        self.tool = settings.pubmed_tool
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"{self.tool} ({self.email})"
        })
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Make a request to PubMed API with rate limiting."""
        params["email"] = self.email
        params["tool"] = self.tool
        
        try:
            response = self.session.get(f"{self.BASE_URL}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making PubMed request: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def search(self, query: str, max_results: int = 10, publication_year: Optional[int] = None) -> List[Dict]:
        """
        Search PubMed for studies matching the query.
        
        Args:
            query: Search query (e.g., "vitamin D depression")
            max_results: Maximum number of results to return
            publication_year: Filter by publication year
            
        Returns:
            List of raw study data from PubMed
        """
        # Build search query
        search_query = query
        if publication_year:
            search_query += f" AND ({publication_year}[Date - Publication])"
        
        # First, get the list of PMIDs
        esearch_params = {
            "db": "pubmed",
            "term": search_query,
            "retmode": "json",
            "retmax": max_results,
            "sort": "relevance"
        }
        
        esearch_result = self._make_request("esearch.fcgi", esearch_params)
        if not esearch_result or "esearchresult" not in esearch_result:
            return []
        
        pmid_list = esearch_result.get("esearchresult", {}).get("idlist", [])
        if not pmid_list:
            return []
        
        # Now fetch details for each PMID
        pmid_str = ",".join(pmid_list)
        efetch_params = {
            "db": "pubmed",
            "id": pmid_str,
            "retmode": "json",
            "rettype": "abstract"
        }
        
        efetch_result = self._make_request("efetch.fcgi", efetch_params)
        if not efetch_result:
            return []
        
        # Parse the results
        studies = []
        pubmed_data = efetch_result.get("pubmeddata", {})
        
        for pmid, article in pubmed_data.get("article", {}).items():
            study = self._parse_article(article, pmid)
            if study:
                studies.append(study)
        
        return studies
    
    def _parse_article(self, article: Dict, pmid: str) -> Optional[Dict]:
        """Parse a PubMed article into a structured format."""
        try:
            # Extract basic info
            medline_citation = article.get("medlinecitation", {})
            article_title = medline_citation.get("articletitle", "")
            abstract = medline_citation.get("abstract", {}).get("abstracttext", ["]")
            abstract = " ".join(abstract) if isinstance(abstract, list) else abstract
            
            # Extract authors
            authors = []
            author_list = medline_citation.get("authorlist", [])
            for author in author_list:
                author_name = author.get("author", {}).get("name", "")
                if author_name:
                    authors.append(author_name)
            
            # Extract journal info
            journal_info = medline_citation.get("journal", {})
            journal_title = journal_info.get("title", "")
            journal_issue = journal_info.get("journalissue", {})
            pub_date = journal_issue.get("pubdate", {})
            publication_date = self._parse_pubmed_date(pub_date)
            
            # Extract DOI
            doi = ""
            elocation_id = medline_citation.get("elocationid", "")
            if elocation_id and elocation_id.startswith("doi:"):
                doi = elocation_id[4:]
            
            # Extract study type from title/abstract
            study_type = self._detect_study_type(article_title, abstract)
            
            # Extract participants if mentioned
            participants = self._extract_participants(abstract)
            
            return {
                "pmid": pmid,
                "title": article_title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal_title,
                "publication_date": publication_date,
                "study_type": study_type,
                "participants": participants,
                "doi": doi,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            }
        except Exception as e:
            print(f"Error parsing article {pmid}: {e}")
            return None
    
    def _parse_pubmed_date(self, pub_date: Dict) -> Optional[str]:
        """Parse PubMed date format into YYYY-MM-DD."""
        try:
            year = pub_date.get("year", "")
            month = pub_date.get("month", "01")
            day = pub_date.get("day", "01")
            
            if not year:
                return None
            
            # Convert month name to number if needed
            month_num = month
            if month and not month.isdigit():
                month_num = str(self._month_to_num(month))
            
            return f"{year}-{month_num.zfill(2)}-{day.zfill(2)}"
        except:
            return None
    
    def _month_to_num(self, month: str) -> int:
        """Convert month name to number."""
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        return months.get(month.lower()[:3], 1)
    
    def _detect_study_type(self, title: str, abstract: str) -> StudyType:
        """Detect study type from title and abstract."""
        text = f"{title} {abstract}".lower()
        
        # Check for highest quality first
        if any(word in text for word in ["meta-analysis", "meta analysis", "systematic review and meta"]):
            return StudyType.META_ANALYSIS
        if any(word in text for word in ["systematic review", "systematic literature review"]):
            return StudyType.SYSTEMATIC_REVIEW
        if any(word in text for word in ["randomized controlled trial", "randomised controlled trial", 
                                         "rct", "randomized trial", "clinical trial"]):
            return StudyType.RANDOMIZED_CONTROLLED_TRIAL
        if any(word in text for word in ["cohort study", "prospective cohort", "retrospective cohort"]):
            return StudyType.COHORT_STUDY
        if any(word in text for word in ["case-control study", "case control study"]):
            return StudyType.CASE_CONTROL_STUDY
        if any(word in text for word in ["cross-sectional study", "cross sectional"]):
            return StudyType.CROSS_SECTIONAL_STUDY
        if any(word in text for word in ["case report", "case study"]):
            return StudyType.CASE_REPORT
        if any(word in text for word in ["case series", "case-series"]):
            return StudyType.CASE_SERIES
        if any(word in text for word in ["animal study", "in vivo", "murine", "rat", "mouse"]):
            return StudyType.ANIMAL_STUDY
        if any(word in text for word in ["in vitro", "cell culture", "laboratory study"]):
            return StudyType.IN_VITRO_STUDY
        if any(word in text for word in ["review", "narrative review"]):
            return StudyType.REVIEW
        
        return StudyType.OTHER
    
    def _extract_participants(self, abstract: str) -> Optional[int]:
        """Extract number of participants from abstract."""
        # Look for patterns like "n = 100", "100 participants", "100 subjects"
        patterns = [
            r"n\s*=\s*(\d{1,4}(?:,\d{3})*)",
            r"(\d{1,4}(?:,\d{3})*)\s*(?:participants?|subjects?|patients?|individuals?)",
            r"sample size\s*[:\-]\s*(\d{1,4}(?:,\d{3})*)",
            r"(\d{1,4}(?:,\d{3})*)\s*(?:enrolled|included|recruited)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, abstract, re.IGNORECASE)
            if match:
                num_str = match.group(1).replace(",", "")
                try:
                    return int(num_str)
                except ValueError:
                    continue
        
        return None
    
    def get_study_details(self, pmid: str) -> Optional[Dict]:
        """Get detailed information for a single study by PMID."""
        efetch_params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "json",
            "rettype": "abstract"
        }
        
        efetch_result = self._make_request("efetch.fcgi", efetch_params)
        if not efetch_result:
            return None
        
        pubmed_data = efetch_result.get("pubmeddata", {})
        article = pubmed_data.get("article", {}).get(pmid, {})
        
        if not article:
            return None
        
        return self._parse_article(article, pmid)


# Singleton instance
pubmed_searcher = PubMedSearcher()
