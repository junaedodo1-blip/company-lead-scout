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
        leads = finder.find_decision_makers(
            comp,
            target_titles=req.target_titles,
            max_results=req.max_results_per_company or 5
        )
        for l in leads:
            l = OutreachGenerator.enrich_lead_with_outreach(l)
            all_leads.append(l)

    return {"total": len(all_leads), "leads": all_leads}

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
    uvicorn.run(app, host="127.0.0.1", port=8000)
