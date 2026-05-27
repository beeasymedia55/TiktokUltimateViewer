#!/usr/bin/env python3
"""
TikTok Bot - Core Engine
Handles view simulation, account rotation, proxy management, request signing
Author: HackerAI PenTest Framework
"""
import os
import sys
import json
import time
import random
import threading
import queue
import requests
from datetime import datetime
from typing import Optional, Dict, List, Callable
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).parent))
from config import config
from signer import TikTokSigner
from proxy_manager import ProxyManager
from dashboard import Dashboard


class TikTokBot:
    """
    Core TikTok bot engine.
    Features: Live stream view simulation, account rotation, proxy rotation,
              full request signing, real-time dashboard
    """

    # TikTok API endpoints
    API_ENDPOINTS = {
        "feed": "/aweme/v1/feed/",
        "live": "/aweme/v1/live/",
        "view": "/aweme/v1/aweme/stats/",
        "user_info": "/aweme/v1/user/",
        "login": "/passport/auth/login/",
        "device_register": "/passport/device/register/",
    }

    def __init__(self, dashboard: Optional[Dashboard] = None):
        self.dashboard = dashboard or Dashboard()
        self.proxy_manager = ProxyManager()
        self.account_generator = None
        
        # Load account generator lazily
        from Generate import AccountGenerator
        self.account_generator = AccountGenerator()
        
        # State
        self._running = False
        self._threads = []
        self._task_queue = queue.Queue()
        self._accounts = []
        self._account_index = 0
        self._lock = threading.Lock()
        
        # Stats
        self.stats = {
            "views_completed": 0,
            "views_failed": 0,
            "views_in_progress": 0,
            "requests_sent": 0,
            "requests_success": 0,
            "requests_failed": 0,
        }

    def load_accounts(self) -> int:
        """Load all accounts from the accounts directory"""
        self._accounts = self.account_generator.load_accounts()
        count = len(self._accounts)
        if self.dashboard:
            self.dashboard.update(accounts_loaded=count)
        return count

    def get_next_account(self) -> Optional[Dict]:
        """Get next account in round-robin fashion"""
        with self._lock:
            if not self._accounts:
                return None
            acc = self._accounts[self._account_index % len(self._accounts)]
            self._account_index += 1
            return acc

    def load_account_sessions(self, username: str) -> Optional[Dict]:
        """Load session data for a specific account"""
        sessions = self.account_generator.load_sessions()
        return sessions.get(username)

    def load_device(self, device_id: str) -> Optional[Dict]:
        """Load device profile"""
        devices = self.account_generator.load_devices()
        return devices.get(device_id)

    def _make_signed_request(self, url: str, method: str = "GET",
                              body: str = "", account: Optional[Dict] = None,
                              use_proxy: bool = True) -> Optional[Dict]:
        """
        Make a signed request to TikTok API.
        Uses full signature generation via SignerPy.
        """
        # Get account details
        device_id = None
        session_token = None
        cookies = ""
        
        if account:
            device_id = account.get("device_id")
            session_token = account.get("session_token")
            session = self.load_account_sessions(account.get("username", ""))
            if session:
                cookies = session.get("cookie", "")

        # Generate signatures
        signer = TikTokSigner(device_id=device_id)
        headers = signer.sign_request(url, data=body, cookies=cookies, method=method)
        
        # Add auth headers
        if session_token:
            headers["X-Session-Token"] = session_token
        
        # Proxy setup
        proxies = None
        if use_proxy:
            proxy_url = self.proxy_manager.get_proxy_url()
            if proxy_url:
                proxies = {"http": proxy_url, "https": proxy_url}
                if self.dashboard:
                    self.dashboard.update(current_proxy=proxy_url)

        # Make request
        try:
            with self._lock:
                self.stats["requests_sent"] += 1
            
            if method == "GET":
                resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            else:
                resp = requests.post(url, headers=headers, data=body, proxies=proxies, timeout=15)
            
            if resp.status_code == 200:
                with self._lock:
                    self.stats["requests_success"] += 1
                return resp.json()
            else:
                with self._lock:
                    self.stats["requests_failed"] += 1
                if self.dashboard:
                    self.dashboard.update(errors_last=f"HTTP {resp.status_code}")
                return None
                
        except requests.RequestException as e:
            with self._lock:
                self.stats["requests_failed"] += 1
            if self.dashboard:
                self.dashboard.update(errors_last=str(e)[:50])
            return None

    def simulate_view(self, video_id: str, account: Optional[Dict] = None) -> bool:
        """
        Simulate a view on a TikTok video.
        Uses the /aweme/v1/aweme/stats/ endpoint with full signatures.
        """
        if account:
            if self.dashboard:
                self.dashboard.update(current_account=account.get("username", "unknown"))
        
        # Build the stats URL
        base_host = random.choice(signer.get_api_hosts())
        params = {
            "aid": config.get("app_id", 1233),
            "app_name": "musically_go",
            "device_platform": config.get("device_platform", "android"),
            "os_api": "29",
            "os_version": "12",
            "ssmix": "a",
            "manifest_version_code": "2023000000",
            "dpi": 480,
            "carrier_region": "US",
            "ac": "wifi",
            "channel": "googleplay",
            "update_version_code": "2023000000",
            "app_type": "normal",
            "tz_name": "America/New_York",
            "account_region": "US",
            "sys_region": "US",
            "app_language": "en",
            "language": "en",
            "timezone_offset": "-14400",
            "device_id": account.get("device_id", "0") if account else "0",
            "version_code": "310502",
            "resolution": "1440*3088",
        }
        
        query_string = urlencode(params)
        url = f"https://{base_host}/aweme/v1/aweme/stats/?{query_string}"
        
        # View payload
        payload = json.dumps({
            "item_id": video_id,
            "stats_type": 1,  # 1 = view
            "source": 0,
            "sec_user_id": "",
            "author_id": "",
        })
        
        result = self._make_signed_request(url, method="POST", body=payload, account=account)
        
        if result:
            with self._lock:
                self.stats["views_completed"] += 1
                if account:
                    account["total_views"] = account.get("total_views", 0) + 1
            return True
        
        with self._lock:
            self.stats["views_failed"] += 1
        return False

    def simulate_live_view(self, room_id: str, account: Optional[Dict] = None) -> bool:
        """
        Simulate a live stream view via TikTok API direct requests.
        Uses the live endpoint with full signature generation.
        """
        if account and self.dashboard:
            self.dashboard.update(current_account=account.get("username", "unknown"))
        
        base_host = random.choice(TikTokSigner().get_api_hosts())
        params = {
            "aid": config.get("app_id", 1233),
            "device_id": account.get("device_id", "0") if account else "0",
            "room_id": room_id,
            "live_id": 1,
            "orientation": 0,
        }
        
        query_string = urlencode(params)
        url = f"https://{base_host}/aweme/v1/live/enter/?{query_string}"
        
        result = self._make_signed_request(url, account=account)
        
        if result:
            with self._lock:
                self.stats["views_completed"] += 1
            return True
        
        with self._lock:
            self.stats["views_failed"] += 1
        return False

    def _worker(self, video_id: str, view_count: int, is_live: bool = False):
        """Worker thread for sending views"""
        while self._running and view_count > 0:
            account = self.get_next_account()
            if not account:
                time.sleep(1)
                continue
            
            with self._lock:
                self.stats["views_in_progress"] += 1
            
            if is_live:
                success = self.simulate_live_view(video_id, account)
            else:
                success = self.simulate_view(video_id, account)
            
            with self._lock:
                self.stats["views_in_progress"] -= 1
            
            if success:
                view_count -= 1
                
                # Update dashboard
                if self.dashboard:
                    self.dashboard.update(
                        views_completed=self.stats["views_completed"],
                        views_failed=self.stats["views_failed"],
                        requests_sent=self.stats["requests_sent"],
                        requests_success=self.stats["requests_success"],
                        requests_failed=self.stats["requests_failed"],
                        accounts_total_views=sum(a.get("total_views", 0) for a in self._accounts),
                    )
            
            # Delay between views
            delay = random.uniform(
                config.get("view_delay_min", 3),
                config.get("view_delay_max", 8)
            )
            time.sleep(delay)

    def start_views(self, video_id: str, total_views: int, 
                    threads: int = None, is_live: bool = False):
        """
        Start view simulation across multiple threads.
        
        Args:
            video_id: TikTok video ID or live room ID
            total_views: Total number of views to send
            threads: Number of concurrent threads (default: from config)
            is_live: If True, uses live stream endpoint
        """
        if self._running:
            print("  [!] Bot is already running")
            return
        
        thread_count = threads or config.get("threads", 5)
        views_per_thread = max(1, total_views // thread_count)
        
        self._running = True
        
        # Update dashboard
        if self.dashboard:
            self.dashboard.update(
                status="Running",
                views_target_video=video_id,
                views_target_count=total_views,
                operation=f"Sending {total_views} views via {thread_count} threads"
            )
            self.dashboard.start()
        
        print(f"\n  [*] Starting {thread_count} threads for {total_views} views")
        print(f"  [*] Target: {video_id}")
        print(f"  [*] Accounts loaded: {len(self._accounts)}")
        print(f"  [*] Proxies working: {self.proxy_manager.get_working_count()}")
        print(f"\n  [!] Dashboard active - press Ctrl+C to stop\n")
        
        # Start worker threads
        self._threads = []
        for i in range(thread_count):
            t = threading.Thread(
                target=self._worker,
                args=(video_id, views_per_thread, is_live),
                daemon=True
            )
            t.start()
            self._threads.append(t)
        
        try:
            # Monitor threads
            while any(t.is_alive() for t in self._threads):
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  [!] Stopping bot...")
        finally:
            self.stop()

    def stop(self):
        """Stop all bot operations"""
        self._running = False
        
        # Wait for threads to finish
        for t in self._threads:
            t.join(timeout=3)
        
        self._threads.clear()
        
        # Stop dashboard
        if self.dashboard:
            self.dashboard.update(status="Stopped")
            self.dashboard.stop()
        
        print(f"\n  [✓] Bot stopped")
        print(f"      Views completed: {self.stats['views_completed']}")
        print(f"      Views failed:    {self.stats['views_failed']}")
        print(f"      Requests sent:   {self.stats['requests_sent']}")

    def setup_proxies(self, auto_scrape: bool = None):
        """Initialize proxy pool"""
        if auto_scrape is None:
            auto_scrape = config.get("auto_scrape_proxies", True)
        
        if auto_scrape:
            print("\n  [*] Scraping proxies from 12+ sources...")
            
            def scrape_progress(current, total, msg):
                print(f"\r  [*] {msg} ({current}/{total})", end="")
            
            self.proxy_manager.scrape_proxies(progress_callback=scrape_progress)
            
            if self.proxy_manager.proxies:
                print(f"\n  [*] Checking {len(self.proxy_manager.proxies)} proxies...")
                
                def check_progress(current, total, msg):
                    print(f"\r  [*] {msg}", end="")
                
                self.proxy_manager.check_proxies(progress_callback=check_progress)
        
        # Update dashboard
        if self.dashboard:
            proxy_stats = self.proxy_manager.get_proxy_stats()
            self.dashboard.update(
                proxies_total=proxy_stats["total"],
                proxies_working=proxy_stats["total"],
            )
        
        return self.proxy_manager.get_working_count()
