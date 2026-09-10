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
from core.mailflare_engine import MailflareEngine
from core.email_intelligence import EmailIntelligence
from core.email_warmup import EmailWarmupEngine
from core.openreply_engine import OpenReplyEngine
from core.google_sheets_sync import GoogleSheetsSync
from core.crm_sync import CRMSyncEngine
from core.contact_verifier import ContactVerifier
from core.analytics_engine import AnalyticsEngine

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
mailflare = MailflareEngine()
warmup_engine = EmailWarmupEngine()
openreply = OpenReplyEngine()
sheets_sync = GoogleSheetsSync()
crm_sync = CRMSyncEngine()
analytics = AnalyticsEngine()


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
    
    # Sanitize and cap to max 10 companies per request to protect against abuse
    clean_companies = [c.strip()[:100] for c in req.companies if c.strip()][:10]
    if not clean_companies:
        raise HTTPException(status_code=400, detail="No valid company names provided.")

    all_leads = []
    for comp in clean_companies:
        try:
            leads = finder.find_decision_makers(
                comp,
                target_titles=req.target_titles,
                max_results=min(req.max_results_per_company or 5, 20)
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


# --- MAILFLARE INBOX & AUTOMATION ENDPOINTS ---

class OutreachEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    lead_name: Optional[str] = ""
    company: Optional[str] = ""

class ThreadReplyRequest(BaseModel):
    thread_id: str
    body: str

class WarmupUpdateRequest(BaseModel):
    active: Optional[bool] = None
    target_daily_limit: Optional[int] = None


@app.get("/api/mailflare/threads")
def get_mailflare_threads():
    return {"threads": mailflare.get_threads()}


@app.get("/api/mailflare/threads/{thread_id}")
def get_mailflare_thread(thread_id: str):
    thread = mailflare.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@app.post("/api/mailflare/send")
def send_outreach_email(req: OutreachEmailRequest):
    if not req.to_email or "@" not in req.to_email:
        raise HTTPException(status_code=400, detail="Valid recipient email required")
    res = mailflare.send_outreach_email(
        to_email=req.to_email,
        subject=req.subject,
        body=req.body,
        lead_name=req.lead_name,
        company=req.company
    )
    return res


@app.post("/api/mailflare/reply")
def reply_to_thread(req: ThreadReplyRequest):
    if not req.thread_id or not req.body:
        raise HTTPException(status_code=400, detail="Thread ID and message body required")
    res = mailflare.add_reply(thread_id=req.thread_id, body=req.body, direction="outbound")
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "Failed to add reply"))
    return res


@app.post("/api/mailflare/smart-reply")
def generate_smart_reply(thread_id: str = Query(...)):
    thread = mailflare.get_thread(thread_id)
    if not thread or not thread.get("messages"):
        raise HTTPException(status_code=404, detail="Thread or messages not found")

    last_inbound = None
    for msg in reversed(thread["messages"]):
        if msg["direction"] == "inbound":
            last_inbound = msg
            break

    if not last_inbound:
        last_inbound = thread["messages"][-1]

    clean_body = EmailIntelligence.strip_quoted_reply(last_inbound["body"])
    intent_analysis = EmailIntelligence.classify_intent(clean_body)
    suggested_reply = EmailIntelligence.generate_smart_reply_suggestion(
        thread_subject=thread["subject"],
        lead_name=thread["lead_name"],
        lead_message=clean_body
    )

    return {
        "thread_id": thread_id,
        "lead_name": thread["lead_name"],
        "intent": intent_analysis,
        "suggested_reply": suggested_reply
    }


@app.get("/api/mailflare/warmup/status")
def get_warmup_status():
    return warmup_engine.get_status()


@app.post("/api/mailflare/warmup/status")
def update_warmup_status(req: WarmupUpdateRequest):
    updates = {}
    if req.active is not None:
        updates["active"] = req.active
    if req.target_daily_limit is not None:
        updates["target_daily_limit"] = req.target_daily_limit
    return warmup_engine.update_status(updates)


@app.post("/api/mailflare/webhook")
def handle_mailflare_webhook(payload: dict):
    return mailflare.handle_webhook_event(payload)


# --- OPENREPLY MULTI-CHANNEL ENDPOINTS ---

class OpenReplyChannelToggle(BaseModel):
    channel: str
    active: bool

class OpenReplyMessageReq(BaseModel):
    thread_id: str
    body: str

class SheetsConfigReq(BaseModel):
    webhook_url: Optional[str] = None
    enabled: Optional[bool] = None

class CRMSyncReq(BaseModel):
    leads: List[dict]
    crm_type: Optional[str] = "HubSpot"

class EmailVerifyReq(BaseModel):
    email: str


@app.get("/api/openreply/channels")
def get_openreply_channels():
    return openreply.get_channels()


@app.post("/api/openreply/channels")
def toggle_openreply_channel(req: OpenReplyChannelToggle):
    return openreply.toggle_channel(req.channel, req.active)


@app.get("/api/openreply/threads")
def get_openreply_threads(channel: Optional[str] = Query(None)):
    return {"threads": openreply.get_threads(channel)}


@app.post("/api/openreply/send")
def send_openreply_msg(req: OpenReplyMessageReq):
    res = openreply.send_message(req.thread_id, req.body)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to send message"))
    return res


@app.post("/api/openreply/webhook/{channel}")
def handle_openreply_webhook(channel: str, payload: dict):
    return openreply.handle_webhook(channel, payload)


# --- GOOGLE SHEETS & CRM SYNC ENDPOINTS ---

@app.get("/api/sheets/config")
def get_sheets_config():
    return sheets_sync.get_config()


@app.post("/api/sheets/config")
def update_sheets_config(req: SheetsConfigReq):
    updates = {}
    if req.webhook_url is not None:
        updates["webhook_url"] = req.webhook_url
    if req.enabled is not None:
        updates["enabled"] = req.enabled
    return sheets_sync.update_config(updates)


@app.post("/api/sheets/sync")
def sync_leads_to_sheets(leads: List[dict]):
    if not leads:
        raise HTTPException(status_code=400, detail="No leads provided for sheet sync")
    return sheets_sync.sync_leads_to_sheet(leads)


@app.post("/api/crm/sync")
def sync_leads_to_crm(req: CRMSyncReq):
    if not req.leads:
        raise HTTPException(status_code=400, detail="No leads provided for CRM sync")
    return crm_sync.sync_leads_to_crm(req.leads, req.crm_type or "HubSpot")


# --- DELIVERABILITY & ANALYTICS ENDPOINTS ---

@app.post("/api/verify/email")
def verify_email_deliverability(req: EmailVerifyReq):
    return ContactVerifier.verify_email_deliverability(req.email)


@app.get("/api/analytics/funnel")
def get_funnel_analytics():
    return analytics.get_funnel_analytics()


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

