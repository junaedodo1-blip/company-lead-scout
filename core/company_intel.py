import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

class CompanyIntelScout:
    """Scrapes company web presence, social media handles, Google reviews/ratings, and direct competitors."""

    def __init__(self, user_agent: str = None):
        self.headers = {
            "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def fetch_website_details(self, domain_or_name: str) -> Dict[str, Any]:
        """Scrapes company website home page for meta descriptions, social links, and contact info."""
        url = domain_or_name if domain_or_name.startswith("http") else f"https://{domain_or_name}"
        data = {
            "url": url,
            "title": "",
            "description": "",
            "social_links": {},
            "status": "offline"
        }
        try:
            resp = requests.get(url, headers=self.headers, timeout=8)
            if resp.status_code == 200:
                data["status"] = "online"
                soup = BeautifulSoup(resp.text, "html.parser")
                title_tag = soup.find("title")
                data["title"] = title_tag.get_text(strip=True) if title_tag else ""
                
                desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
                data["description"] = desc_tag.get("content", "").strip() if desc_tag else ""

                # Extract social links from anchor tags
                for a in soup.find_all("a", href=True):
                    href = a["href"].lower()
                    if "facebook.com" in href and "facebook" not in data["social_links"]:
                        data["social_links"]["facebook"] = a["href"]
                    elif "instagram.com" in href and "instagram" not in data["social_links"]:
                        data["social_links"]["instagram"] = a["href"]
                    elif "linkedin.com" in href and "linkedin" not in data["social_links"]:
                        data["social_links"]["linkedin"] = a["href"]
                    elif "twitter.com" in href or "x.com" in href:
                        if "twitter" not in data["social_links"]:
                            data["social_links"]["twitter"] = a["href"]
        except Exception as e:
            data["error"] = str(e)

        return data

    def search_google_maps_reviews(self, company_name: str) -> Dict[str, Any]:
        """Scrapes search snippets to discover Google rating, review counts, and customer sentiment highlights."""
        info = {
            "rating": None,
            "review_count": None,
            "snippets": []
        }
        if not DDGS:
            return info

        query = f'"{company_name}" reviews ratings Google Maps'
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                for item in results:
                    body = item.get("body", "")
                    title = item.get("title", "")
                    info["snippets"].append(f"{title}: {body}")

                    # Regex match rating like "4.5 stars" or "4.2/5"
                    match = re.search(r"(\d\.\d)\s*(?:stars|\/5|\bstar\b)", body, re.IGNORECASE)
                    if match and not info["rating"]:
                        info["rating"] = float(match.group(1))

                    # Regex match review count like "120 reviews"
                    match_rev = re.search(r"(\d+[\d,]*)\s*reviews", body, re.IGNORECASE)
                    if match_rev and not info["review_count"]:
                        info["review_count"] = match_rev.group(1)
        except Exception as e:
            info["error"] = str(e)

        return info

    def find_competitors(self, company_name: str, industry_or_niche: str = "") -> List[Dict[str, str]]:
        """Finds direct competitors for target company using search queries."""
        competitors = []
        if not DDGS:
            return competitors

        query = f'"{company_name}" competitors alternatives top {industry_or_niche} companies'
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=6))
                seen = set()
                for item in results:
                    title = item.get("title", "")
                    body = item.get("body", "")
                    url = item.get("href", "")
                    domain = urllib.parse.urlparse(url).netloc.replace("www.", "")

                    if domain and domain not in seen and company_name.lower() not in domain.lower():
                        seen.add(domain)
                        competitors.append({
                            "name": title.split(" - ")[0].split(" | ")[0].strip(),
                            "domain": domain,
                            "snippet": body,
                            "url": url
                        })
        except Exception as e:
            print(f"[CompanyIntelScout] Competitor search note: {e}")

        return competitors[:5]
