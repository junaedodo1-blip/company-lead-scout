import os
import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

from core.company_enricher import CompanyEnricher
from core.contact_parser import ContactParser

class LinkedInFinder:
    """Multi-engine concurrent LinkedIn decision-maker scout optimized for 24/7 cloud execution."""

    def __init__(self, user_agent: str = None):
        self.headers = {
            "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def search_ddgs_package(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        if not DDGS:
            return results
        try:
            with DDGS(timeout=3) as ddgs:
                ddg_res = list(ddgs.text(query, max_results=max_results * 2))
                for item in ddg_res:
                    url = item.get("href", "")
                    title = item.get("title", "")
                    body = item.get("body", "")
                    if ContactParser.is_valid_linkedin_profile(url):
                        results.append({
                            "title": title,
                            "snippet": body,
                            "url": url
                        })
        except Exception as e:
            print(f"[LinkedInFinder] DDGS search note: {e}")
        return results

    def search_bing_html(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        try:
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
            resp = requests.get(url, headers=self.headers, timeout=4)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for item in soup.find_all("li", class_="b_algo"):
                    a_tag = item.find("a")
                    if not a_tag:
                        continue
                    href = a_tag.get("href", "")
                    title = a_tag.get_text(strip=True)
                    p_tag = item.find("p")
                    snippet = p_tag.get_text(strip=True) if p_tag else ""

                    if ContactParser.is_valid_linkedin_profile(href):
                        results.append({
                            "title": title,
                            "snippet": snippet,
                            "url": href
                        })
        except Exception as e:
            print(f"[LinkedInFinder] Bing Search note: {e}")
        return results

    def execute_parallel_search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Runs Bing and DDGS engines simultaneously in parallel for guaranteed cloud yield."""
        engines = [
            self.search_ddgs_package,
            self.search_bing_html,
        ]
        
        combined_results = []
        seen = set()

        with ThreadPoolExecutor(max_workers=len(engines)) as executor:
            future_to_engine = {executor.submit(engine, query, max_results): engine for engine in engines}
            for future in as_completed(future_to_engine, timeout=5):
                try:
                    res = future.result()
                    for item in res:
                        url = item.get("url")
                        if url and url not in seen:
                            seen.add(url)
                            combined_results.append(item)
                except Exception:
                    pass

        return combined_results

    def find_decision_makers(self, company_input: str, target_titles: List[str] = None, max_results: int = 5) -> List[Dict[str, Any]]:
        if CompanyEnricher.is_direct_linkedin_url(company_input):
            return [ContactParser.parse_direct_profile_url(company_input)]

        clean_company = CompanyEnricher.clean_company_name(company_input)
        queries = CompanyEnricher.get_search_queries(company_input, target_titles)

        seen_urls = set()
        leads = []

        for query in queries[:2]:
            if len(leads) >= max_results:
                break

            raw_results = self.execute_parallel_search(query, max_results=max_results)

            for item in raw_results:
                url = item["url"]
                clean_url = ContactParser.clean_linkedin_url(url)
                if clean_url in seen_urls:
                    continue

                if not ContactParser.is_relevant_lead(item["title"], item["snippet"], clean_company):
                    continue

                seen_urls.add(clean_url)

                contact = ContactParser.parse_snippet(
                    title_str=item["title"],
                    snippet_str=item["snippet"],
                    url_str=url,
                    target_company=clean_company
                )
                leads.append(contact)

                if len(leads) >= max_results:
                    break

        return leads
