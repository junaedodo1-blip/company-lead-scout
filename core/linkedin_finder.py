import os
import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

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
    """Finds LinkedIn profile contacts for target companies across DDGS API and search fallback engines."""

    def __init__(self, user_agent: str = None):
        self.headers = {
            "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def search_ddgs_package(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        if not DDGS:
            return results
        try:
            with DDGS() as ddgs:
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

    def search_duckduckgo_html(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                links = soup.find_all("a", class_="result__url")
                snippets = soup.find_all("a", class_="result__snippet")
                titles = soup.find_all("a", class_="result__a")

                for i in range(min(len(links), max_results * 2)):
                    href = links[i].get("href", "")
                    if "uddg=" in href:
                        match = re.search(r"uddg=([^&]+)", href)
                        if match:
                            href = urllib.parse.unquote(match.group(1))

                    if ContactParser.is_valid_linkedin_profile(href):
                        title_text = titles[i].get_text(strip=True) if i < len(titles) else ""
                        snippet_text = snippets[i].get_text(strip=True) if i < len(snippets) else ""
                        results.append({
                            "title": title_text,
                            "snippet": snippet_text,
                            "url": href
                        })
        except Exception as e:
            print(f"[LinkedInFinder] DDG HTML Search note: {e}")
        return results

    def find_decision_makers(self, company_input: str, target_titles: List[str] = None, max_results: int = 5) -> List[Dict[str, Any]]:
        clean_company = CompanyEnricher.clean_company_name(company_input)
        queries = CompanyEnricher.get_search_queries(company_input, target_titles)

        seen_urls = set()
        leads = []

        for query in queries:
            if len(leads) >= max_results:
                break

            # 1. Primary: DDGS package search
            raw_results = self.search_ddgs_package(query, max_results=max_results)

            # 2. Fallback: DDG HTML scraping search
            if not raw_results:
                raw_results = self.search_duckduckgo_html(query, max_results=max_results)

            for item in raw_results:
                url = item["url"]
                clean_url = ContactParser.clean_linkedin_url(url)
                if clean_url in seen_urls:
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

            time.sleep(0.5)

        return leads
