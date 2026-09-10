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
    """100% Authentic LinkedIn decision-maker scout across SerpAPI, Google CSE, and multi-engine real search scrapers."""

    def __init__(self, user_agent: str = None):
        self.headers = {
            "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def search_serpapi(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """SerpAPI integration for 100% reliable cloud Google search results."""
        api_key = os.getenv("SERPAPI_KEY")
        results = []
        if not api_key:
            return results
        try:
            url = f"https://serpapi.com/search.json?engine=google&q={urllib.parse.quote(query)}&api_key={api_key}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                items = resp.json().get("organic_results", [])
                for item in items:
                    href = item.get("link", "")
                    if ContactParser.is_valid_linkedin_profile(href):
                        results.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "url": href
                        })
        except Exception as e:
            print(f"[LinkedInFinder] SerpAPI Note: {e}")
        return results

    def search_google_custom_search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Google Custom Search API for official real Google results."""
        api_key = os.getenv("GOOGLE_API_KEY", "AIzaSyBpWXVWgwpV76W4VY74-m3r__tBJBMJcRI")
        cse_id = os.getenv("GOOGLE_CSE_ID", "53f2ae2525ea0477f")
        results = []
        if not api_key or not cse_id:
            return results
        try:
            url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cse_id}&q={urllib.parse.quote(query)}"
            resp = requests.get(url, timeout=4)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                for item in items:
                    href = item.get("link", "")
                    if ContactParser.is_valid_linkedin_profile(href):
                        results.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "url": href
                        })
        except Exception as e:
            print(f"[LinkedInFinder] Google CSE Note: {e}")
        return results

    def search_ddgs_package(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        if not DDGS:
            return results
        try:
            with DDGS(timeout=4) as ddgs:
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

    def execute_search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        # 1. SerpAPI (if SERPAPI_KEY is set)
        res = self.search_serpapi(query, max_results=max_results)
        if res:
            return res

        # 2. Google Custom Search (if GOOGLE_API_KEY is set)
        res = self.search_google_custom_search(query, max_results=max_results)
        if res:
            return res

        # 3. DDGS Real Package
        res = self.search_ddgs_package(query, max_results=max_results)
        if res:
            return res

        # 4. Bing Real Scraper
        return self.search_bing_html(query, max_results=max_results)

    def find_decision_makers(self, company_input: str, target_titles: List[str] = None, max_results: int = 5) -> List[Dict[str, Any]]:
        # Handle direct pasted LinkedIn profile URL
        if CompanyEnricher.is_direct_linkedin_url(company_input):
            return [ContactParser.parse_direct_profile_url(company_input)]

        clean_company = CompanyEnricher.clean_company_name(company_input)
        queries = CompanyEnricher.get_search_queries(company_input, target_titles)

        seen_urls = set()
        leads = []

        for query in queries[:3]:
            if len(leads) >= max_results:
                break

            raw_results = self.execute_search(query, max_results=max_results)

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
