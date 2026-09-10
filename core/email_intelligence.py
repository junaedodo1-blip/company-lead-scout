# -*- coding: utf-8 -*-
import re
from typing import Dict, Any, List

class EmailIntelligence:
    """Analyzes email threads, classifies lead intent, and generates intelligent reply drafts."""

    @staticmethod
    def strip_quoted_reply(body_text: str) -> str:
        """Removes quoted history from reply messages to reduce noise and context bloat."""
        if not body_text:
            return ""
        lines = body_text.splitlines()
        clean_lines = []
        for line in lines:
            if re.match(r"^\s*>", line):
                continue
            if re.search(r"---+\s*Original Message\s*---+", line, re.IGNORECASE):
                break
            if re.search(r"On\s+.*wrote:", line, re.IGNORECASE):
                break
            clean_lines.append(line)
        return "\n".join(clean_lines).strip()

    @staticmethod
    def classify_intent(text: str) -> Dict[str, Any]:
        """Classifies lead response intent (Interested, Meeting Requested, Not Interested, Unsubscribe)."""
        clean = text.lower()

        # High Intent / Meeting Request
        meeting_keywords = ["call", "zoom", "meet", "schedule", "time", "calendar", "tuesday", "wednesday", "tomorrow", "available"]
        if any(k in clean for k in meeting_keywords) and any(pos in clean for pos in ["yes", "sure", "sounds good", "send", "works"]):
            return {
                "category": "Meeting Requested",
                "label": "🔥 High Intent",
                "confidence": 0.95,
                "action_recommended": "Send Calendar Booking Link / Meeting Confirmation"
            }

        # Warm Interest
        interest_keywords = ["interested", "pricing", "details", "info", "tell me more", "deck", "proposal"]
        if any(k in clean for k in interest_keywords):
            return {
                "category": "Warm Lead",
                "label": "💡 Interested",
                "confidence": 0.85,
                "action_recommended": "Send Product Brief & 30-Sec Demo Video"
            }

        # Unsubscribe / Opt-out
        unsubscribe_keywords = ["unsubscribe", "remove", "stop", "don't email", "not interested", "no thanks"]
        if any(k in clean for k in unsubscribe_keywords):
            return {
                "category": "Unsubscribe",
                "label": "⛔ Opt-Out",
                "confidence": 0.99,
                "action_recommended": "Auto-Suppress Lead & Archive Thread"
            }

        # Default Neutral / Inquiry
        return {
            "category": "Inquiry",
            "label": "💬 General Inquiry",
            "confidence": 0.70,
            "action_recommended": "Reply with Tailored FAQ Response"
        }

    @staticmethod
    def generate_smart_reply_suggestion(thread_subject: str, lead_name: str, lead_message: str) -> str:
        """Generates contextual AI reply suggestions based on detected intent."""
        intent_data = EmailIntelligence.classify_intent(lead_message)
        category = intent_data["category"]
        first_name = lead_name.split()[0] if lead_name else "there"

        if category == "Meeting Requested":
            return (
                f"Hi {first_name},\n\n"
                f"Great! I've sent over a calendar invite for our discussion. Looking forward to sharing how we streamline operations.\n\n"
                f"Here is our direct calendar link if you'd like to adjust the time: https://cal.com/cielvisuals/meeting\n\n"
                f"Best,\nOutreach Team"
            )
        elif category == "Warm Lead":
            return (
                f"Hi {first_name},\n\n"
                f"Thanks for your interest! I've attached our 1-page overview detailing how we automate lead generation and client outreach.\n\n"
                f"Would Tuesday afternoon work for a quick 10-minute walkthrough?\n\n"
                f"Best regards,\nOutreach Team"
            )
        elif category == "Unsubscribe":
            return (
                f"Hi {first_name},\n\n"
                f"Understood. You've been removed from our list. Have a great week!\n\n"
                f"Best,\nOutreach Team"
            )
        else:
            return (
                f"Hi {first_name},\n\n"
                f"Thank you for your reply regarding {thread_subject}. Happy to answer any questions you have!\n\n"
                f"Best regards,\nOutreach Team"
            )
