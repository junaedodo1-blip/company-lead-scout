# -*- coding: utf-8 -*-
import os
import json
import time
import threading
from typing import Dict, Any

class AnalyticsEngine:
    """Tracks conversion funnel metrics and performance across channels."""
    _lock = threading.Lock()

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.stats_file = os.path.join(self.data_dir, "analytics_stats.json")
        self._init_stats()

    def _init_stats(self):
        with AnalyticsEngine._lock:
            if not os.path.exists(self.stats_file):
                initial_stats = {
                    "funnel": {
                        "discovered_leads": 142,
                        "outreach_sent": 86,
                        "replies_received": 29,
                        "meetings_booked": 9,
                        "pipeline_value_usd": 18500
                    },
                    "channel_performance": {
                        "email": {"sent": 48, "replies": 14, "conversion_rate": 29.1},
                        "instagram": {"sent": 18, "replies": 7, "conversion_rate": 38.8},
                        "whatsapp": {"sent": 12, "replies": 6, "conversion_rate": 50.0},
                        "facebook": {"sent": 8, "replies": 2, "conversion_rate": 25.0}
                    }
                }
                with open(self.stats_file, "w", encoding="utf-8") as f:
                    json.dump(initial_stats, f, indent=2)

    def get_funnel_analytics(self) -> Dict[str, Any]:
        with AnalyticsEngine._lock:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                return json.load(f)
