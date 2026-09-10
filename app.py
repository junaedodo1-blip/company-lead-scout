import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import pandas as pd
import io

from core.linkedin_finder import LinkedInFinder
from core.outreach_generator import OutreachGenerator
from core.company_enricher import CompanyEnricher
from core.company_intel import CompanyIntelScout
from core.vulnerability_analyzer import VulnerabilityAnalyzer

app = FastAPI(title="Target Company Decision-Maker & LinkedIn Finder API")

# Enable CORS for local web dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

finder = LinkedInFinder()
intel_scout = CompanyIntelScout()


class SearchRequest(BaseModel):
    companies: List[str]
    target_titles: Optional[List[str]] = None
    max_results_per_company: Optional[int] = 5

@app.get("/api/health")
def health_check():
    return {"status": "online", "service": "company-lead-scout"}

@app.get("/api/titles")
def get_default_titles():
    titles_file = os.path.join(os.path.dirname(__file__), "config", "titles.json")
    if os.path.exists(titles_file):
        with open(titles_file, "r") as f:
            return json.load(f)
    return {"high_priority_titles": ["CEO", "Founder", "President", "COO", "Controller"]}

@app.post("/api/search")
def search_leads(req: SearchRequest):
    if not req.companies:
        raise HTTPException(status_code=400, detail="Companies list cannot be empty.")
    
    all_leads = []
    for comp in req.companies:
        if not comp.strip():
            continue
        try:
            leads = finder.find_decision_makers(
                comp,
                target_titles=req.target_titles,
                max_results=req.max_results_per_company or 5
            )
            for l in leads:
                l = OutreachGenerator.enrich_lead_with_outreach(l)
                all_leads.append(l)
        except Exception as err:
            print(f"[app.py Search Error for '{comp}']: {err}")

    return {"total": len(all_leads), "leads": all_leads}


@app.get("/api/company/intel")
def get_company_intel(company: str = Query(..., description="Target company name or domain")):
    if not company:
        raise HTTPException(status_code=400, detail="Company parameter required")
    
    web_data = intel_scout.fetch_website_details(company)
    review_data = intel_scout.search_google_maps_reviews(company)
    competitors = intel_scout.find_competitors(company)
    analysis = VulnerabilityAnalyzer.analyze_vulnerabilities(web_data, review_data, competitors)
    
    return {
        "company": company,
        "website": web_data,
        "reviews": review_data,
        "competitors": competitors,
        "analysis": analysis
    }


@app.post("/api/export/csv")
def export_csv(leads: List[dict]):
    if not leads:
        raise HTTPException(status_code=400, detail="No leads provided for export")
    
    df = pd.DataFrame(leads)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    response = StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=target_company_leads.csv"
    return response

# Mount web frontend static files
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/")
    def read_index():
        return FileResponse(os.path.join(web_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

