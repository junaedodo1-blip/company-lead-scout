# -*- coding: utf-8 -*-
import os
import json
import time
import uuid
import threading
from typing import Dict, Any, List, Optional

class OpenReplyEngine:
    """Multi-channel messenger and webhook handler for Instagram DMs, WhatsApp Business, and Facebook Messenger."""
    _lock = threading.Lock()

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_file = os.path.join(self.data_dir, "openreply_db.json")
        self._init_db()

    def _init_db(self):
        with OpenReplyEngine._lock:
            if not os.path.exists(self.db_file):
                initial_data = {
                    "channels": {
                        "instagram": {"active": True, "account": "@cielvisuals.official", "status": "Connected"},
                        "whatsapp": {"active": True, "phone": "+8801700000000", "status": "Connected"},
                        "facebook": {"active": True, "page": "Ciel Visuals B2B", "status": "Connected"}
                    },
                    "threads": [
                        {
                            "thread_id": "open-demo-1",
                            "channel": "instagram",
                            "lead_name": "Nafis Ahmed",
                            "lead_handle": "@nafis_bproperty",
                            "company": "Bproperty BD",
                            "status": "Meeting Scheduled",
                            "intent": "High Intent",
                            "last_updated": time.time() - 1800,
                            "messages": [
                                {
                                    "msg_id": "m-1",
                                    "direction": "outbound",
                                    "channel": "instagram",
                                    "from": "@cielvisuals.official",
                                    "to": "@nafis_bproperty",
                                    "date": "2026-09-10 12:00:00",
                                    "body": "Hi Nafis, loved your recent post on property tech trends in Dhaka. Would love to share how we automate B2B lead generation!"
                                },
                                {
                                    "msg_id": "m-2",
                                    "direction": "inbound",
                                    "channel": "instagram",
                                    "from": "@nafis_bproperty",
                                    "to": "@cielvisuals.official",
                                    "date": "2026-09-10 12:45:00",
                                    "body": "Hey! Thanks for reaching out. Yes, we are actually looking for lead automation tools right now. Can we talk on WhatsApp?"
                                }
                            ]
                        },
                        {
                            "thread_id": "open-demo-2",
                            "channel": "whatsapp",
                            "lead_name": "Tariqul Islam",
                            "lead_handle": "+8801811223344",
                            "company": "Dhaka Logistics Ltd",
                            "status": "Active Inquiry",
                            "intent": "Warm Lead",
                            "last_updated": time.time() - 900,
                            "messages": [
                                {
                                    "msg_id": "m-3",
                                    "direction": "inbound",
                                    "channel": "whatsapp",
                                    "from": "+8801811223344",
                                    "to": "+8801700000000",
                                    "date": "2026-09-10 13:00:00",
                                    "body": "Hi, saw your service details on Facebook. Can you send me pricing for 500 decision maker leads?"
                                }
                            ]
                        }
                    ]
                }
                with open(self.db_file, "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, indent=2)

    def _load_db(self) -> Dict[str, Any]:
        with OpenReplyEngine._lock:
            with open(self.db_file, "r", encoding="utf-8") as f:
                return json.load(f)

    def _save_db(self, data: Dict[str, Any]):
        with OpenReplyEngine._lock:
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def get_channels(self) -> Dict[str, Any]:
        db = self._load_db()
        return db.get("channels", {})

    def toggle_channel(self, channel_name: str, active: bool) -> Dict[str, Any]:
        with OpenReplyEngine._lock:
            with open(self.db_file, "r", encoding="utf-8") as f:
                db = json.load(f)
            if channel_name in db["channels"]:
                db["channels"][channel_name]["active"] = active
                with open(self.db_file, "w", encoding="utf-8") as f:
                    json.dump(db, f, indent=2)
            return db.get("channels", {})

    def update_channels_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        with OpenReplyEngine._lock:
            with open(self.db_file, "r", encoding="utf-8") as f:
                db = json.load(f)
            
            channels = db.get("channels", {})
            if "instagram" not in channels: channels["instagram"] = {}
            if "whatsapp" not in channels: channels["whatsapp"] = {}
            if "facebook" not in channels: channels["facebook"] = {}

            if "ig_handle" in config and config["ig_handle"]:
                channels["instagram"]["account"] = config["ig_handle"].strip()
            if "ig_token" in config:
                channels["instagram"]["token"] = config["ig_token"].strip()
            if "ig_active" in config and config["ig_active"] is not None:
                channels["instagram"]["active"] = bool(config["ig_active"])

            if "wa_phone" in config and config["wa_phone"]:
                channels["whatsapp"]["phone"] = config["wa_phone"].strip()
            if "wa_token" in config:
                channels["whatsapp"]["token"] = config["wa_token"].strip()
            if "wa_active" in config and config["wa_active"] is not None:
                channels["whatsapp"]["active"] = bool(config["wa_active"])

            if "fb_page" in config and config["fb_page"]:
                channels["facebook"]["page"] = config["fb_page"].strip()
            if "fb_token" in config:
                channels["facebook"]["token"] = config["fb_token"].strip()
            if "fb_active" in config and config["fb_active"] is not None:
                channels["facebook"]["active"] = bool(config["fb_active"])

            db["channels"] = channels
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)
            return channels

    def get_threads(self, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        db = self._load_db()
        threads = db.get("threads", [])
        if channel:
            return [t for t in threads if t.get("channel") == channel]
        return threads

    def send_message(self, thread_id: str, body: str) -> Dict[str, Any]:
        with OpenReplyEngine._lock:
            with open(self.db_file, "r", encoding="utf-8") as f:
                db = json.load(f)

            for t in db.get("threads", []):
                if t["thread_id"] == thread_id:
                    msg_id = f"m-{uuid.uuid4().hex[:6]}"
                    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    new_msg = {
                        "msg_id": msg_id,
                        "direction": "outbound",
                        "channel": t["channel"],
                        "from": "System Host",
                        "to": t["lead_handle"],
                        "date": now_str,
                        "body": body
                    }
                    t["messages"].append(new_msg)
                    t["last_updated"] = time.time()
                    with open(self.db_file, "w", encoding="utf-8") as f:
                        json.dump(db, f, indent=2)
                    return {"success": True, "message": new_msg}
        return {"success": False, "error": "Thread not found"}

    def handle_webhook(self, channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        from_handle = payload.get("from", "Unknown User")
        body = payload.get("body", "") or payload.get("text", "")

        with OpenReplyEngine._lock:
            with open(self.db_file, "r", encoding="utf-8") as f:
                db = json.load(f)

            matched_thread = None
            for t in db.get("threads", []):
                if t["lead_handle"].lower() == from_handle.lower() and t["channel"] == channel:
                    matched_thread = t
                    break

            if matched_thread:
                msg_id = f"m-{uuid.uuid4().hex[:6]}"
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                matched_thread["messages"].append({
                    "msg_id": msg_id,
                    "direction": "inbound",
                    "channel": channel,
                    "from": from_handle,
                    "to": "System Host",
                    "date": now_str,
                    "body": body
                })
                matched_thread["last_updated"] = time.time()
            else:
                new_thread = {
                    "thread_id": f"open-{uuid.uuid4().hex[:6]}",
                    "channel": channel,
                    "lead_name": from_handle.replace("@", "").capitalize(),
                    "lead_handle": from_handle,
                    "company": "Direct Lead",
                    "status": "New Inbound",
                    "intent": "Inquiry",
                    "last_updated": time.time(),
                    "messages": [
                        {
                            "msg_id": f"m-{uuid.uuid4().hex[:6]}",
                            "direction": "inbound",
                            "channel": channel,
                            "from": from_handle,
                            "to": "System Host",
                            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "body": body
                        }
                    ]
                }
                db["threads"].insert(0, new_thread)

            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)

        return {"success": True, "message": "Webhook processed successfully"}
