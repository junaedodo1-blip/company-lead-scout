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
from core.contact_parser import ContactParser
from core.linkedin_finder import LinkedInFinder
from core.company_enricher import CompanyEnricher

class TestBugAndStressSuite(unittest.TestCase):

    def setUp(self):
        self.test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(self.test_data_dir, exist_ok=True)
        self.mailflare = MailflareEngine(data_dir=self.test_data_dir)
        self.warmup = EmailWarmupEngine(data_dir=self.test_data_dir)
        self.finder = LinkedInFinder()

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

    def test_intent_classification_boundaries(self):
        # High intent
        self.assertEqual(EmailIntelligence.classify_intent("Yes sure, Tuesday works for a call!")["category"], "Meeting Requested")
        # Warm lead
        self.assertEqual(EmailIntelligence.classify_intent("Please send over pricing and deck info")["category"], "Warm Lead")
        # Unsubscribe
        self.assertEqual(EmailIntelligence.classify_intent("Stop emailing me, unsubscribe immediately")["category"], "Unsubscribe")
        # Neutral
        self.assertEqual(EmailIntelligence.classify_intent("Thanks for the message.")["category"], "Inquiry")

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
        threads = self.mailflare.get_threads()
        self.assertGreaterEqual(len(threads), 30)

    # --- 3. INPUT INJECTION & SECURITY STRESS TESTS ---
    def test_contact_parser_security_and_malformed_urls(self):
        self.assertFalse(ContactParser.is_valid_linkedin_profile(None))
        self.assertFalse(ContactParser.is_valid_linkedin_profile("http://malicious.com/search?q=linkedin"))
        self.assertFalse(ContactParser.is_valid_linkedin_profile("https://www.linkedin.com/jobs/view/12345"))

        # Valid domain assertions
        self.assertTrue(ContactParser.is_valid_linkedin_profile("https://www.linkedin.com/in/john-doe-123"))
        self.assertTrue(ContactParser.is_valid_linkedin_profile("https://crunchbase.com/person/steve-gozini"))

    def test_company_enricher_long_inputs(self):
        super_long_input = "A" * 5000 + "<script>alert(1)</script>"
        clean = CompanyEnricher.clean_company_name(super_long_input)
        queries = CompanyEnricher.get_search_queries(super_long_input)
        self.assertIsInstance(clean, str)
        self.assertIsInstance(queries, list)
        self.assertGreater(len(queries), 0)

    # --- 4. WARMUP ENGINE STATUS BOUNDARY TESTS ---
    def test_warmup_engine_boundaries(self):
        status = self.warmup.get_status()
        self.assertIn("deliverability_health_score", status)
        
        # Test boundary update
        updated = self.warmup.update_status({"target_daily_limit": 500})
        self.assertEqual(updated["target_daily_limit"], 500)

if __name__ == "__main__":
    unittest.main()
