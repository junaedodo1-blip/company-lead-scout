# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import unittest
import concurrent.futures
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.email_intelligence import EmailIntelligence
from core.mailflare_engine import MailflareEngine
from core.email_warmup import EmailWarmupEngine
from core.openreply_engine import OpenReplyEngine
from core.google_sheets_sync import GoogleSheetsSync
from core.crm_sync import CRMSyncEngine
from core.contact_verifier import ContactVerifier
from core.analytics_engine import AnalyticsEngine
from core.contact_parser import ContactParser
from core.company_enricher import CompanyEnricher

class TestBugAndStressSuite(unittest.TestCase):

    def setUp(self):
        self.test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(self.test_data_dir, exist_ok=True)
        self.mailflare = MailflareEngine(data_dir=self.test_data_dir)
        self.warmup = EmailWarmupEngine(data_dir=self.test_data_dir)
        self.openreply = OpenReplyEngine(data_dir=self.test_data_dir)
        self.sheets = GoogleSheetsSync(data_dir=self.test_data_dir)
        self.crm = CRMSyncEngine(data_dir=self.test_data_dir)
        self.analytics = AnalyticsEngine(data_dir=self.test_data_dir)

    # --- 1. EMAIL INTELLIGENCE EDGE CASE TESTS ---
    def test_email_quoted_text_stripping_edge_cases(self):
        self.assertEqual(EmailIntelligence.strip_quoted_reply(""), "")
        self.assertEqual(EmailIntelligence.strip_quoted_reply(None), "")

        nested_quoted = (
            "Hi team, let's meet tomorrow at 3 PM.\n"
            "> > On Sep 9, 2026, John wrote:\n"
            "> > > Can we reschedule to Thursday?\n"
            "--- Original Message ---\n"
            "From: john@example.com"
        )
        cleaned = EmailIntelligence.strip_quoted_reply(nested_quoted)
        self.assertIn("let's meet tomorrow at 3 PM.", cleaned)
        self.assertNotIn("Can we reschedule", cleaned)
        self.assertNotIn("Original Message", cleaned)

    # --- 2. MAILFLARE ENGINE CONCURRENCY STRESS TEST ---
    def test_mailflare_db_concurrency_stress(self):
        """Simulate 30 concurrent threads creating emails & replies simultaneously."""
        def worker(i):
            email = f"lead_{i}@testdomain.com"
            res = self.mailflare.send_outreach_email(
                to_email=email,
                subject=f"Stress Test Subject {i}",
                body=f"Stress test body content {i}",
                lead_name=f"Lead {i}",
                company="Stress Corp"
            )
            thread_id = res.get("thread_id")
            if thread_id:
                self.mailflare.add_reply(thread_id, body=f"Reply from worker {i}", direction="inbound")
            return res.get("success", False)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(30)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertEqual(len(results), 30)
        self.assertTrue(all(results))

    # --- 3. OPENREPLY MULTI-CHANNEL WEBHOOK & CONCURRENCY TESTS ---
    def test_openreply_multi_channel(self):
        channels = self.openreply.get_channels()
        self.assertIn("instagram", channels)
        self.assertIn("whatsapp", channels)

        # Webhook test for new inbound Instagram message
        res = self.openreply.handle_webhook("instagram", {"from": "@new_lead", "body": "Need pricing for 100 leads"})
        self.assertTrue(res.get("success"))
        threads = self.openreply.get_threads(channel="instagram")
        self.assertGreaterEqual(len(threads), 1)

    # --- 4. GOOGLE SHEETS & CRM SYNC TESTS ---
    def test_sheets_and_crm_sync(self):
        mock_leads = [
            {"name": "Rubyat Sobnom", "title": "Executive", "company": "Bproperty.com", "linkedin_url": "https://linkedin.com/in/rubyat"}
        ]
        sheet_res = self.sheets.sync_leads_to_sheet(mock_leads)
        self.assertTrue(sheet_res.get("success"))
        self.assertEqual(sheet_res.get("synced_count"), 1)

        crm_res = self.crm.sync_leads_to_crm(mock_leads, crm_type="Salesforce")
        self.assertTrue(crm_res.get("success"))
        self.assertEqual(crm_res.get("crm_type"), "Salesforce")

    # --- 5. DELIVERABILITY VERIFIER & ANALYTICS TESTS ---
    def test_contact_verifier_and_analytics(self):
        valid_res = ContactVerifier.verify_email_deliverability("rubyat.sobnom@bproperty.com")
        self.assertTrue(valid_res["deliverable"])

        disposable_res = ContactVerifier.verify_email_deliverability("spammer@tempmail.com")
        self.assertFalse(disposable_res["deliverable"])

        funnel_data = self.analytics.get_funnel_analytics()
        self.assertIn("funnel", funnel_data)
        self.assertIn("discovered_leads", funnel_data["funnel"])

if __name__ == "__main__":
    unittest.main()
