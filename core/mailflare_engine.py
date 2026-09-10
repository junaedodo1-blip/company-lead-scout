# -*- coding: utf-8 -*-
import os
import json
import time
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional

import threading

class MailflareEngine:
    """Outbound email dispatcher, Cloudflare/Mailflare webhook parser, and campaign state machine."""
    _lock = threading.Lock()

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_file = os.path.join(self.data_dir, "mailflare_db.json")
        self._init_db()

    def _init_db(self):
        with MailflareEngine._lock:
            if not os.path.exists(self.db_file):
                initial_data = {
                    "threads": [
                        {
                            "thread_id": "thread-demo-1",
                            "lead_name": "Rubyat Sobnom",
                            "lead_email": "rubyat.sobnom@bproperty.com",
                            "company": "Bproperty.com",
                            "subject": "Quick question regarding operations at Bproperty.com",
                            "status": "Meeting Requested",
                            "intent": "High Intent",
                            "last_updated": time.time() - 3600,
                            "messages": [
                                {
                                    "msg_id": "msg-1",
                                    "direction": "outbound",
                                    "from": "outreach@cielvisuals.com",
                                    "to": "rubyat.sobnom@bproperty.com",
                                    "date": "2026-09-10 10:00:00",
                                    "body": "Hi Rubyat,\n\nI reached out after seeing your role as Executive at Bproperty.com.\nWe help high-growth teams automate administrative & lead outreach workflows.\nWould you be open to a brief 10-minute chat next Tuesday?"
                                },
                                {
                                    "msg_id": "msg-2",
                                    "direction": "inbound",
                                    "from": "rubyat.sobnom@bproperty.com",
                                    "to": "outreach@cielvisuals.com",
                                    "date": "2026-09-10 11:30:00",
                                    "body": "Hi there,\n\nThanks for reaching out. Yes, Tuesday at 2 PM works well for me. Could you send over a calendar invite?\n\nBest,\nRubyat"
                                }
                            ]
                        }
                    ],
                    "campaigns": [
                        {
                            "id": "camp-1",
                            "name": "BD Real Estate Decision Makers",
                            "sent_count": 24,
                            "reply_count": 7,
                            "status": "Active"
                        }
                    ],
                    "accounts": [
                        {
                            "id": "acc-default",
                            "email": "outreach@cielvisuals.com",
                            "sender_name": "Junaed (Ciel Visuals Outreach)",
                            "smtp_host": "smtp.mailflare.io",
                            "smtp_port": 587,
                            "smtp_user": "outreach@cielvisuals.com",
                            "smtp_pass": "••••••••••••",
                            "signature": "Best regards,\nJunaed | Ciel Visuals Outbound",
                            "is_default": True,
                            "status": "Connected"
                        }
                    ]
                }
                with open(self.db_file, "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, indent=2)

    def get_accounts(self) -> List[Dict[str, Any]]:
        db = self._load_db()
        accounts = db.get("accounts", [])
        if not accounts:
            default_acc = {
                "id": "acc-default",
                "email": "outreach@cielvisuals.com",
                "sender_name": "Junaed (Ciel Visuals Outreach)",
                "smtp_host": "smtp.mailflare.io",
                "smtp_port": 587,
                "smtp_user": "outreach@cielvisuals.com",
                "smtp_pass": "••••••••••••",
                "signature": "Best regards,\nJunaed | Ciel Visuals Outbound",
                "is_default": True,
                "status": "Connected"
            }
            accounts = [default_acc]
            db["accounts"] = accounts
            self._save_db(db)
        return accounts

    def add_or_update_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        with MailflareEngine._lock:
            with open(self.db_file, "r", encoding="utf-8") as f:
                db = json.load(f)
            
            accounts = db.get("accounts", [])
            acc_id = account_data.get("id") or f"acc-{uuid.uuid4().hex[:8]}"
            
            existing = None
            for a in accounts:
                if a["id"] == acc_id or a["email"].lower() == account_data.get("email", "").lower():
                    existing = a
                    break

            if account_data.get("is_default"):
                for a in accounts:
                    a["is_default"] = False

            new_acc = {
                "id": acc_id,
                "email": account_data.get("email", "").strip(),
                "sender_name": account_data.get("sender_name", "").strip(),
                "smtp_host": account_data.get("smtp_host", "smtp.gmail.com").strip(),
                "smtp_port": int(account_data.get("smtp_port", 587)),
                "smtp_user": account_data.get("smtp_user", "").strip(),
                "smtp_pass": account_data.get("smtp_pass", "").strip(),
                "signature": account_data.get("signature", "").strip(),
                "is_default": account_data.get("is_default", len(accounts) == 0),
                "status": "Connected"
            }

            if existing:
                accounts[accounts.index(existing)] = new_acc
            else:
                accounts.append(new_acc)

            db["accounts"] = accounts
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)

            return {"success": True, "account": new_acc}

    def delete_account(self, acc_id: str) -> Dict[str, Any]:
        with MailflareEngine._lock:
            with open(self.db_file, "r", encoding="utf-8") as f:
                db = json.load(f)
            
            accounts = [a for a in db.get("accounts", []) if a["id"] != acc_id]
            if accounts and not any(a.get("is_default") for a in accounts):
                accounts[0]["is_default"] = True
            db["accounts"] = accounts
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)
            return {"success": True}

    def _load_db(self) -> Dict[str, Any]:
        with MailflareEngine._lock:
            with open(self.db_file, "r", encoding="utf-8") as f:
                return json.load(f)

    def _save_db(self, data: Dict[str, Any]):
        with MailflareEngine._lock:
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def get_threads(self) -> List[Dict[str, Any]]:
        db = self._load_db()
        return db.get("threads", [])

    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        db = self._load_db()
        for t in db.get("threads", []):
            if t["thread_id"] == thread_id:
                return t
        return None

    def send_outreach_email(self, to_email: str, subject: str, body: str, lead_name: str = "", company: str = "") -> Dict[str, Any]:
        thread_id = f"thread-{uuid.uuid4().hex[:8]}"
        msg_id = f"msg-{uuid.uuid4().hex[:6]}"
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        new_thread = {
            "thread_id": thread_id,
            "lead_name": lead_name or to_email.split("@")[0].capitalize(),
            "lead_email": to_email,
            "company": company or "Target Lead",
            "subject": subject,
            "status": "Sent",
            "intent": "Pending Reply",
            "last_updated": time.time(),
            "messages": [
                {
                    "msg_id": msg_id,
                    "direction": "outbound",
                    "from": os.getenv("OUTREACH_FROM_EMAIL", "outreach@cielvisuals.com"),
                    "to": to_email,
                    "date": now_str,
                    "body": body
                }
            ]
        }

        smtp_host = os.getenv("SMTP_HOST")
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        smtp_port = int(os.getenv("SMTP_PORT", 587))

        sent_via_server = False
        if smtp_host and smtp_user and smtp_pass:
            try:
                msg = MIMEMultipart()
                msg["From"] = os.getenv("OUTREACH_FROM_EMAIL", smtp_user)
                msg["To"] = to_email
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                sent_via_server = True
            except Exception as e:
                print(f"[MailflareEngine SMTP Error]: {e}")

        with MailflareEngine._lock:
            with open(self.db_file, "r", encoding="utf-8") as f:
                db = json.load(f)
            db["threads"].insert(0, new_thread)
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)

        return {
            "success": True,
            "thread_id": thread_id,
            "sent_via_server": sent_via_server,
            "message": "Outreach email dispatched successfully."
        }

    def add_reply(self, thread_id: str, body: str, direction: str = "outbound", from_email: str = "") -> Dict[str, Any]:
        with MailflareEngine._lock:
            with open(self.db_file, "r", encoding="utf-8") as f:
                db = json.load(f)

            for t in db["threads"]:
                if t["thread_id"] == thread_id:
                    msg_id = f"msg-{uuid.uuid4().hex[:6]}"
                    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

                    new_msg = {
                        "msg_id": msg_id,
                        "direction": direction,
                        "from": from_email or (os.getenv("OUTREACH_FROM_EMAIL", "outreach@cielvisuals.com") if direction == "outbound" else t["lead_email"]),
                        "to": t["lead_email"] if direction == "outbound" else os.getenv("OUTREACH_FROM_EMAIL", "outreach@cielvisuals.com"),
                        "date": now_str,
                        "body": body
                    }
                    t["messages"].append(new_msg)
                    t["last_updated"] = time.time()
                    if direction == "outbound":
                        t["status"] = "Replied"
                    with open(self.db_file, "w", encoding="utf-8") as f:
                        json.dump(db, f, indent=2)
                    return {"success": True, "message": new_msg}
        return {"success": False, "error": "Thread not found"}

    def handle_webhook_event(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        from_email = webhook_data.get("from", "")
        subject = webhook_data.get("subject", "")
        body = webhook_data.get("text", "") or webhook_data.get("body", "")

        db = self._load_db()
        matched_thread = None
        for t in db["threads"]:
            if t["lead_email"].lower() == from_email.lower():
                matched_thread = t
                break

        if matched_thread:
            return self.add_reply(matched_thread["thread_id"], body=body, direction="inbound", from_email=from_email)
        else:
            return self.send_outreach_email(to_email=from_email, subject=subject, body=body, lead_name=from_email.split("@")[0])
