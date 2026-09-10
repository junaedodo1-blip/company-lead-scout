import re
from typing import Dict, Any, List

class CompanyEnricher:
    """Normalizes company inputs (names, domains, or direct LinkedIn URLs) and creates optimized natural search queries."""

    @staticmethod
    def is_direct_linkedin_url(input_str: str) -> bool:
        if not input_str:
            return False
        clean = input_str.strip().lower()
        return "linkedin.com/in/" in clean or "bd.linkedin.com/in/" in clean

    @staticmethod
    def clean_company_name(input_str: str) -> str:
        if not input_str:
            return ""
        
        if CompanyEnricher.is_direct_linkedin_url(input_str):
            return input_str.strip()

        cleaned = re.sub(r"https?://(www\.)?", "", input_str.strip(), flags=re.IGNORECASE)
        cleaned = cleaned.split('/')[0]
        return cleaned

    @staticmethod
    def get_search_queries(company_raw: str, target_titles: List[str] = None) -> List[str]:
        raw_name = company_raw.strip()
        clean_domain = CompanyEnricher.clean_company_name(company_raw)
        brand_name = clean_domain.split('.')[0] if '.' in clean_domain else clean_domain

        if not target_titles:
            target_titles = ["CEO", "Founder", "President", "Owner", "COO", "Managing Director", "Controller"]

        queries = []

        # 1. Natural search query (bypasses bot filters on cloud servers)
        queries.append(f'{clean_domain} linkedin decision maker ceo founder')
        
        # 2. Targeted location & brand query
        queries.append(f'{brand_name} Bangladesh linkedin executive director')
        
        # 3. Exact site query fallback
        queries.append(f'site:linkedin.com/in/ "{brand_name}"')

        return queries
