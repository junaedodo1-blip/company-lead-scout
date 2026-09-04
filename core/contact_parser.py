import re
from typing import Dict, Any, Optional

class ContactParser:
    """Parses raw search result snippets into structured decision-maker contact records."""

    @staticmethod
    def is_valid_linkedin_profile(url: str) -> bool:
        if not url or "linkedin.com/in/" not in url.lower():
            return False
        # Filter out job listings, company pages, posts, or directories
        invalid_patterns = ["/jobs/", "/company/", "/posts/", "/dir/", "/pulse/", "/learning/"]
        return not any(p in url.lower() for p in invalid_patterns)

    @staticmethod
    def clean_linkedin_url(url: str) -> str:
        # Strip tracking query params (e.g. ?utm_source=...)
        clean = url.split("?")[0].rstrip("/")
        return clean

    @staticmethod
    def parse_snippet(title_str: str, snippet_str: str, url_str: str, target_company: str) -> Dict[str, Any]:
        """
        Parses title & snippet from search engine (e.g., 'John Doe - Chief Executive Officer - Acme Corp | LinkedIn')
        """
        clean_url = ContactParser.clean_linkedin_url(url_str)
        
        # Default fallback values
        name = "Decision Maker"
        job_title = "Executive / Leader"
        location = "United States"

        # Try parsing name and headline from search result title string
        # Examples: "Jane Smith - Founder & CEO - TechCorp | LinkedIn", "Bob Miller | LinkedIn"
        title_clean = re.sub(r"\s*\|\s*LinkedIn.*$", "", title_str, flags=re.IGNORECASE).strip()
        title_clean = re.sub(r"\s*-\s*LinkedIn.*$", "", title_clean, flags=re.IGNORECASE).strip()

        parts = [p.strip() for p in re.split(r"\s*[-–|•]\s*", title_clean) if p.strip()]

        if len(parts) >= 1:
            name = parts[0]
        if len(parts) >= 2:
            job_title = parts[1]
        elif len(parts) >= 3:
            job_title = f"{parts[1]} ({parts[2]})"

        # If name has job title embedded (e.g. "Jane Smith, CEO"), split it
        if "," in name and len(name.split(",")) == 2:
            possible_name, possible_title = name.split(",")
            if any(term in possible_title.upper() for term in ["CEO", "FOUNDER", "PRESIDENT", "DIRECTOR", "MANAGER"]):
                name = possible_name.strip()
                job_title = possible_title.strip()

        # Parse snippet for additional location or title clues
        if snippet_str:
            # Check for location patterns like "Location: Greater New York Area" or "London, United Kingdom"
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
