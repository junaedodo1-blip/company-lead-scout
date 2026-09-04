from typing import Dict, Any

class OutreachGenerator:
    """Generates tailored LinkedIn connection notes (<300 chars) and InMail/Email drafts."""

    @staticmethod
    def generate_connection_note(name: str, title: str, company: str) -> str:
        first_name = name.split()[0] if name else "there"
        clean_company = company or "your firm"
        
        # High impact connection note under 300 characters
        note = (
            f"Hi {first_name}, noticed your work leading operations/growth at {clean_company}. "
            f"We help executive leaders streamline core operations and client workflows. "
            f"Would love to connect and share a quick resource with you!"
        )
        if len(note) > 300:
            note = (
                f"Hi {first_name}, impressed by your leadership at {clean_company}. "
                f"Would love to connect and share key insights for scaling operations!"
            )
        return note

    @staticmethod
    def generate_inmail_draft(name: str, title: str, company: str) -> Dict[str, str]:
        first_name = name.split()[0] if name else "there"
        clean_company = company or "your company"
        clean_title = title or "Executive"

        subject = f"Quick question regarding operations at {clean_company}"
        body = (
            f"Hi {first_name},\n\n"
            f"I hope you're having a productive week. I reached out after seeing your role as {clean_title} at {clean_company}.\n\n"
            f"We specialize in helping high-growth teams automate repetitive bookkeeping, administrative workflows, and client onboarding so decision-makers can focus on strategic scaling.\n\n"
            f"Would you be open to a brief 10-minute chat next Tuesday to see if this could save your team 15+ hours a week?\n\n"
            f"Best regards,\nOutreach Team"
        )
        return {
            "subject": subject,
            "body": body
        }

    @staticmethod
    def enrich_lead_with_outreach(lead: Dict[str, Any]) -> Dict[str, Any]:
        name = lead.get("name", "Decision Maker")
        title = lead.get("title", "Executive")
        company = lead.get("company", "Target Company")

        lead["connection_note"] = OutreachGenerator.generate_connection_note(name, title, company)
        lead["inmail"] = OutreachGenerator.generate_inmail_draft(name, title, company)
        return lead
