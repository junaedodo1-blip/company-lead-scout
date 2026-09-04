import re
from typing import Dict, Any, List

class CompanyEnricher:
    """Normalizes company inputs (names or domain URLs) and creates optimized search queries."""

    @staticmethod
    def clean_company_name(input_str: str) -> str:
        if not input_str:
            return ""
        
        # Remove http/https and www if passed as URL
        cleaned = re.sub(r"https?://(www\.)?", "", input_str.strip(), flags=re.IGNORECASE)
        # Remove trailing slashes and paths if URL
        cleaned = cleaned.split('/')[0]
        # Remove domain extensions if domain-like (e.g. acme.com -> acme)
        if '.' in cleaned and not ' ' in cleaned:
            cleaned = cleaned.split('.')[0]
        
        # Clean legal entity suffixes for broader search matching
        suffixes = [
            r"\bInc\.?\b", r"\bLLC\.?\b", r"\bLtd\.?\b", r"\bCorp\.?\b",
            r"\bCorporation\b", r"\bGmbH\b", r"\bCo\.?\b", r"\bServices\b", r"\bGroup\b"
        ]
        company_name = cleaned
        for suffix in suffixes:
            company_name = re.sub(suffix, "", company_name, flags=re.IGNORECASE).strip()
        
        return company_name if company_name else cleaned

    @staticmethod
    def get_search_queries(company_raw: str, target_titles: List[str] = None) -> List[str]:
        clean_name = CompanyEnricher.clean_company_name(company_raw)
        raw_name = company_raw.strip()

        if not target_titles:
            target_titles = ["CEO", "Founder", "President", "Owner", "COO", "Managing Director", "Controller"]

        queries = []
        # Title specific queries
        for title in target_titles[:4]:
            queries.append(f'site:linkedin.com/in/ "{clean_name}" {title}')

        # Combined executive fallback queries
        queries.append(f'site:linkedin.com/in/ "{clean_name}" executive OR founder OR owner')
        queries.append(f'site:linkedin.com/in/ "{raw_name}"')

        return queries

