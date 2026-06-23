"""
Main FastAPI application for MedExplainer.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List
from .models import (
    SearchRequest, 
    SearchResponse, 
    StudyResult, 
    StudyType,
    HealthCheckResponse
)
from .search import pubmed_searcher
from .explain import medical_explainer
from .config import settings
import uvicorn


# Create FastAPI app
app = FastAPI(
    title="MedExplainer API",
    description="A service to search and simplify medical research from PubMed and other sources.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "MedExplainer",
        "version": "0.1.0",
        "description": "Search and simplify medical research",
        "docs": "/docs",
        "web": "/web"
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "services": {
            "pubmed": "operational",
            "explainer": "operational"
        }
    }


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_studies(request: SearchRequest):
    """
    Search for medical studies and get simplified explanations.
    
    This endpoint:
    1. Searches PubMed for studies matching the query
    2. Filters by study type (meta-analyses, RCT, etc.)
    3. Simplifies the results for non-experts
    4. Returns structured data with confidence levels
    """
    try:
        # Convert study_types from strings to StudyType enums
        study_type_enum_list = [StudyType(st) for st in request.study_types]
        
        # Perform search
        raw_results = pubmed_searcher.search(
            query=request.query,
            max_results=request.limit * 2,  # Get more to filter by type
            publication_year=request.publication_year
        )
        
        # Filter by study type
        filtered_results = []
        for result in raw_results:
            if result.get("study_type") in study_type_enum_list:
                filtered_results.append(result)
                if len(filtered_results) >= request.limit:
                    break
        
        # Filter by minimum participants if specified
        if request.min_participants:
            filtered_results = [
                r for r in filtered_results 
                if r.get("participants") and r["participants"] >= request.min_participants
            ]
        
        # Convert to StudyResult models with explanations
        results = []
        for result in filtered_results:
            # Generate simple explanation
            simple_explanation = medical_explainer.generate_simple_explanation(
                result, 
                request.language
            )
            
            # Extract key findings
            key_findings = medical_explainer.extract_key_findings(
                result.get("abstract", ""),
                request.language
            )
            
            study_result = StudyResult(
                pmid=result.get("pmid", ""),
                title=result.get("title", ""),
                abstract=result.get("abstract"),
                authors=result.get("authors", []),
                journal=result.get("journal"),
                publication_date=result.get("publication_date"),
                study_type=result.get("study_type", StudyType.OTHER),
                participants=result.get("participants"),
                confidence=medical_explainer.STUDY_TYPE_CONFIDENCE.get(
                    result.get("study_type", StudyType.OTHER),
                    "low"
                ),
                doi=result.get("doi"),
                url=result.get("url", ""),
                simple_explanation=simple_explanation,
                key_findings=key_findings
            )
            results.append(study_result)
        
        # Generate summary
        summary = medical_explainer.generate_summary(
            filtered_results,
            request.query,
            request.language
        )
        
        return SearchResponse(
            query=request.query,
            total_results=len(filtered_results),
            results=results,
            summary=summary
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during search: {str(e)}"
        )


@app.get("/search", tags=["Search"])
async def search_studies_get(
    query: str = Query(..., min_length=3, description="Search query"),
    study_types: List[str] = Query(
        default=["meta_analysis", "randomized_controlled_trial"],
        description="Filter by study types (comma-separated)"
    ),
    min_participants: int = Query(None, description="Minimum number of participants"),
    publication_year: int = Query(None, description="Filter by publication year"),
    language: str = Query(default="en", description="Language for explanations (en/ru)"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of results")
):
    """
    GET version of search endpoint for easier testing.
    """
    request = SearchRequest(
        query=query,
        study_types=study_types,
        min_participants=min_participants,
        publication_year=publication_year,
        language=language,
        limit=limit
    )
    return await search_studies(request)


@app.get("/study/{pmid}", response_model=StudyResult, tags=["Studies"])
async def get_study_details(pmid: str):
    """
    Get detailed information and simplified explanation for a single study by PMID.
    """
    try:
        # Get study details from PubMed
        study_data = pubmed_searcher.get_study_details(pmid)
        if not study_data:
            raise HTTPException(status_code=404, detail="Study not found")
        
        # Generate explanation (default to English)
        simple_explanation = medical_explainer.generate_simple_explanation(
            study_data, 
            "en"
        )
        
        # Extract key findings
        key_findings = medical_explainer.extract_key_findings(
            study_data.get("abstract", ""),
            "en"
        )
        
        return StudyResult(
            pmid=study_data.get("pmid", pmid),
            title=study_data.get("title", ""),
            abstract=study_data.get("abstract"),
            authors=study_data.get("authors", []),
            journal=study_data.get("journal"),
            publication_date=study_data.get("publication_date"),
            study_type=study_data.get("study_type", StudyType.OTHER),
            participants=study_data.get("participants"),
            confidence=medical_explainer.STUDY_TYPE_CONFIDENCE.get(
                study_data.get("study_type", StudyType.OTHER),
                "low"
            ),
            doi=study_data.get("doi"),
            url=study_data.get("url", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"),
            simple_explanation=simple_explanation,
            key_findings=key_findings
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )


@app.get("/web", tags=["Web"])
async def web_interface():
    """Serve the web interface."""
    return {
        "message": "MedExplainer Web Interface",
        "url": "/static/index.html"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True
    )
