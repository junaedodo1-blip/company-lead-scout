# -*- coding: utf-8 -*-
import re
from typing import Dict, Any, Optional

class ContactParser:
    """Parses raw search result snippets into structured decision-maker contact records with strict relevance filtering."""

    @staticmethod
    def is_valid_linkedin_profile(url: str) -> bool:
        if not url or "linkedin.com/in/" not in url.lower():
            return False
        invalid_patterns = ["/jobs/", "/company/", "/posts/", "/dir/", "/pulse/", "/learning/"]
        return not any(p in url.lower() for p in invalid_patterns)

    @staticmethod
    def clean_linkedin_url(url: str) -> str:
        clean = url.split("?")[0].rstrip("/")
        return clean

    @staticmethod
    def is_relevant_lead(title_str: str, snippet_str: str, target_company: str) -> bool:
        """Strictly validates if profile result matches target company/domain to prevent false positive hallucinations."""
        if not target_company or len(target_company) < 2:
            return True
        
        comp_lower = target_company.lower().replace(".com", "").replace(".bd", "").strip()
        text_full = f"{title_str} {snippet_str}".lower()

        # Direct match or word boundary match
        if comp_lower in text_full:
            return True
        
        # Split tokens for multi-word company names
        tokens = [t for t in comp_lower.split() if len(t) > 2]
        if tokens and all(t in text_full for t in tokens):
            return True
            
        return False

    @staticmethod
    def parse_direct_profile_url(profile_url: str) -> Dict[str, Any]:
        """Parses a direct LinkedIn profile URL pasted by user into a clean lead card record."""
        clean_url = ContactParser.clean_linkedin_url(profile_url)
        handle = clean_url.split("/in/")[-1].replace("-", " ").strip()
        name_parts = [word.capitalize() for word in handle.split() if not word.isdigit()]
        name = " ".join(name_parts[:3]) if name_parts else "LinkedIn Professional"

        return {
            "name": name if name else "Target Contact",
            "title": "Decision Maker / Executive",
            "company": "Direct Profile",
            "linkedin_url": clean_url,
            "location": "Direct LinkedIn Profile",
            "raw_snippet": f"Directly imported LinkedIn profile: {clean_url}"
        }

    @staticmethod
    def parse_snippet(title_str: str, snippet_str: str, url_str: str, target_company: str) -> Dict[str, Any]:
        clean_url = ContactParser.clean_linkedin_url(url_str)
        
        name = "Decision Maker"
        job_title = "Executive / Leader"
        location = "Global / Direct"

        title_clean = re.sub(r"\s*\|\s*LinkedIn.*$", "", title_str, flags=re.IGNORECASE).strip()
        title_clean = re.sub(r"\s*-\s*LinkedIn.*$", "", title_clean, flags=re.IGNORECASE).strip()

        parts = [p.strip() for p in re.split(r"\s*[-|]\s*", title_clean) if p.strip()]

        if len(parts) >= 1:
            name = parts[0]
        if len(parts) >= 2:
            job_title = parts[1]
        if len(parts) >= 3 and not "linkedin" in parts[2].lower():
            location = parts[2]

        if "," in name and len(name.split(",")) == 2:
            possible_name, possible_title = name.split(",")
            if any(term in possible_title.upper() for term in ["CEO", "FOUNDER", "PRESIDENT", "DIRECTOR", "MANAGER", "OFFICER"]):
                name = possible_name.strip()
                job_title = possible_title.strip()

        if snippet_str:
            loc_match = re.search(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)*,\s*[A-Z][a-zA-Z\s]+)\b", snippet_str)
            if loc_match:
                location = loc_match.group(1).strip()

        return {
            "name": name,
            "title": job_title,
            "company": target_company,
            "linkedin_url": clean_url,
            "location": location,
            "raw_snippet": snippet_str[:200] if snippet_str else ""
        }
