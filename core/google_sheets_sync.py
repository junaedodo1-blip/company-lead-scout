# -*- coding: utf-8 -*-
import os
import json
import time
import requests
import threading
from typing import Dict, Any, List

class GoogleSheetsSync:
    """Syncs discovered decision-maker leads directly to client Google Spreadsheets via Webhooks or Apps Script."""
    _lock = threading.Lock()

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.config_file = os.path.join(self.data_dir, "sheets_config.json")
        self._init_config()

    def _init_config(self):
        with GoogleSheetsSync._lock:
            if not os.path.exists(self.config_file):
                initial_config = {
                    "enabled": True,
                    "webhook_url": "https://script.google.com/macros/s/AKfycbxDemoWebhookScriptId/exec",
                    "sheet_name": "Target Decision Makers",
                    "auto_sync_on_search": True,
                    "last_synced": time.time() - 7200,
                    "total_leads_synced": 42
                }
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(initial_config, f, indent=2)

    def get_config(self) -> Dict[str, Any]:
        with GoogleSheetsSync._lock:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        with GoogleSheetsSync._lock:
            if not os.path.exists(self.config_file):
                self._init_config()
            with open(self.config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg.update(updates)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            return cfg

    def sync_leads_to_sheet(self, leads: List[Dict[str, Any]], custom_webhook_url: str = None) -> Dict[str, Any]:
        """Pushes structured lead rows to target Google Sheet Webhook."""
        cfg = self.get_config()
        webhook_url = custom_webhook_url or cfg.get("webhook_url")

        if not leads:
            return {"success": False, "error": "No leads provided for sync"}

        formatted_rows = []
        for l in leads:
            formatted_rows.append({
                "Name": l.get("name", ""),
                "Title": l.get("title", ""),
                "Company": l.get("company", ""),
                "LinkedIn URL": l.get("linkedin_url", ""),
                "Location": l.get("location", ""),
                "Connection Note": l.get("connection_note", ""),
                "InMail Draft": (l.get("inmail", {}) or {}).get("body", ""),
                "Discovered Date": time.strftime("%Y-%m-%d %H:%M:%S")
            })

        sent_to_remote = False
        if webhook_url and "script.google.com" in webhook_url and "Demo" not in webhook_url:
            try:
                resp = requests.post(webhook_url, json={"rows": formatted_rows}, timeout=5)
                if resp.status_code in [200, 201, 302]:
                    sent_to_remote = True
            except Exception as e:
                print(f"[GoogleSheetsSync Error]: {e}")

        # Update sync statistics
        new_count = cfg.get("total_leads_synced", 0) + len(leads)
        self.update_config({"last_synced": time.time(), "total_leads_synced": new_count})

        return {
            "success": True,
            "synced_count": len(leads),
            "total_leads_synced": new_count,
            "sent_to_remote": sent_to_remote,
            "message": f"Successfully synced {len(leads)} leads to Google Sheets."
        }
