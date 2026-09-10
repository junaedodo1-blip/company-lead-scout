# -*- coding: utf-8 -*-
import os
import time
import requests
import threading

class KeepAliveEngine:
    """Automated 24/7 server heartbeat engine to prevent Render container sleep & cold starts."""

    def __init__(self, target_url: str = None, ping_interval_seconds: int = 600):
        self.target_url = target_url or os.getenv("RENDER_EXTERNAL_URL", "https://company-lead-scout-2.onrender.com/api/health")
        self.interval = ping_interval_seconds
        self.running = False
        self._thread = None

    def _ping_loop(self):
        print(f"[KeepAliveEngine 24/7] Started automated heartbeat loop for {self.target_url} (Every {self.interval}s)")
        # Wait 30s before first ping to allow app startup
        time.sleep(30)

        while self.running:
            try:
                url = self.target_url if "/api/health" in self.target_url else f"{self.target_url.rstrip('/')}/api/health"
                resp = requests.get(url, timeout=10)
                print(f"[KeepAliveEngine 24/7 Heartbeat]: Pinged {url} -> Status {resp.status_code}")
            except Exception as e:
                print(f"[KeepAliveEngine 24/7 Note]: {e}")

            time.sleep(self.interval)

    def start(self):
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._ping_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self.running = False
