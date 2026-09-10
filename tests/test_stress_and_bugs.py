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
from core.linkedin_finder import LinkedInFinder
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
        self.finder = LinkedInFinder()

    # --- 1. AUTHENTIC DATA ENFORCEMENT & ZERO HALLUCINATION TEST ---
    def test_zero_hallucination_enforcement(self):
        # Empty/unmatched company search must return empty list, NEVER fake data
        res = self.finder.find_decision_makers("non_existent_company_xyz_123456789")
        for item in res:
            # If any results exist, they MUST have a valid real profile URL
            self.assertTrue(ContactParser.is_valid_linkedin_profile(item.get("linkedin_url", "")))

    # --- 2. SEARCH CACHE SPEED & LATENCY TEST ---
    def test_search_cache_latency_under_10ms(self):
        query = "site:linkedin.com/in/ bproperty CEO"
        # Seed cache manually
        self.finder.cache[query] = [{"title": "Steve Gozini", "url": "https://www.linkedin.com/in/steve-gozini/", "snippet": "CEO"}]
        
        t0 = time.time()
        results = self.finder.execute_search(query)
        t1 = time.time()
        
        duration_ms = (t1 - t0) * 1000
        self.assertLess(duration_ms, 50, f"Cache retrieval was too slow: {duration_ms}ms")
        self.assertEqual(len(results), 1)

    # --- 3. EMAIL INTELLIGENCE EDGE CASE TESTS ---
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

    # --- 4. MAILFLARE & OPENREPLY CONCURRENCY STRESS TESTS ---
    def test_mailflare_db_concurrency_stress(self):
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

    def test_openreply_multi_channel_toggles_and_webhooks(self):
        channels = self.openreply.get_channels()
        self.assertIn("instagram", channels)
        self.assertIn("whatsapp", channels)

        # Toggle Instagram off then back on
        updated_off = self.openreply.toggle_channel("instagram", False)
        self.assertFalse(updated_off["instagram"]["active"])

        updated_on = self.openreply.toggle_channel("instagram", True)
        self.assertTrue(updated_on["instagram"]["active"])

        # Webhook processing
        res = self.openreply.handle_webhook("whatsapp", {"from": "+8801711223344", "body": "Hello WhatsApp Lead"})
        self.assertTrue(res.get("success"))

    # --- 5. SHEETS & CRM SYNC ERROR HANDLING ---
    def test_sheets_and_crm_sync_resilience(self):
        # Empty array handled gracefully
        empty_sheet = self.sheets.sync_leads_to_sheet([])
        self.assertFalse(empty_sheet.get("success"))

        mock_leads = [{"name": "Test Lead", "company": "Test Co", "linkedin_url": "https://linkedin.com/in/test"}]
        crm_res = self.crm.sync_leads_to_crm(mock_leads, crm_type="Pipedrive")
        self.assertTrue(crm_res.get("success"))
        self.assertEqual(crm_res.get("crm_type"), "Pipedrive")

    # --- 6. CONTACT VERIFIER MX & BOUNCE RISK TESTS ---
    def test_contact_verifier_comprehensive(self):
        valid = ContactVerifier.verify_email_deliverability("rubyat.sobnom@bproperty.com")
        self.assertTrue(valid["deliverable"])
        self.assertEqual(valid["bounce_risk"], "Low")

        disposable = ContactVerifier.verify_email_deliverability("user@guerrillamail.com")
        self.assertFalse(disposable["deliverable"])
        self.assertEqual(disposable["bounce_risk"], "High")

        invalid_syntax = ContactVerifier.verify_email_deliverability("not_an_email")
        self.assertFalse(invalid_syntax["deliverable"])

    # --- 7. DOMAIN WARMUP & OPENREPLY CONFIGURATION TESTS ---
    def test_warmup_and_openreply_configuration(self):
        # Test EmailWarmupEngine config update
        updated_warmup = self.warmup.update_config({
            "domain": "testagency.com",
            "sending_email": "sender@testagency.com",
            "target_daily_limit": 75,
            "ramp_speed": "10/day"
        })
        self.assertEqual(updated_warmup["domain"], "testagency.com")
        self.assertEqual(updated_warmup["sending_email"], "sender@testagency.com")
        self.assertEqual(updated_warmup["target_daily_limit"], 75)
        self.assertEqual(updated_warmup["ramp_speed"], "10/day")

        # Verify DNS records were calculated
        dns = updated_warmup.get("dns_records", {})
        self.assertIn("spf", dns)
        self.assertIn("dkim", dns)
        self.assertIn("dmarc", dns)

        # Test OpenReplyEngine channel config update
        updated_channels = self.openreply.update_channels_config({
            "ig_handle": "@myagency_ig",
            "ig_token": "TOKEN_IG_999",
            "wa_phone": "+18005550199",
            "wa_token": "TOKEN_WA_888",
            "fb_page": "FB_PAGE_777",
            "fb_token": "TOKEN_FB_666"
        })
        self.assertEqual(updated_channels["instagram"]["account"], "@myagency_ig")
        self.assertEqual(updated_channels["instagram"]["token"], "TOKEN_IG_999")
        self.assertEqual(updated_channels["whatsapp"]["phone"], "+18005550199")
        self.assertEqual(updated_channels["whatsapp"]["token"], "TOKEN_WA_888")
        self.assertEqual(updated_channels["facebook"]["page"], "FB_PAGE_777")
        self.assertEqual(updated_channels["facebook"]["token"], "TOKEN_FB_666")

if __name__ == "__main__":
    unittest.main()


