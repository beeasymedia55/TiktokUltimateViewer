#!/usr/bin/env python3
"""
TikTok Bot - Core Engine
Handles view simulation, account rotation, proxy management, request signing
Features: Live stream view/like/share simulation, video views, full SignerPy integration,
          campaign mode with natural action proportions
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
from typing import Optional, Dict, List, Callable, Tuple
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
    Features: Live stream view/like/share simulation, video views, account rotation,
              proxy rotation, full request signing, real-time dashboard, campaign mode
    """

    # TikTok API endpoints
    API_ENDPOINTS = {
        "feed": "/aweme/v1/feed/",
        "live_enter": "/aweme/v1/live/enter/",
        "live_like": "/aweme/v1/live/like/",
        "live_share": "/aweme/v1/live/share/",
        "live_gift": "/aweme/v1/live/gift/",
        "live_comment": "/aweme/v1/live/comment/",
        "live_room": "/aweme/v1/live/room/",
        "live_heartbeat": "/aweme/v1/live/heartbeat/",
        "stats": "/aweme/v1/aweme/stats/",
        "user_info": "/aweme/v1/user/",
        "login": "/passport/auth/login/",
        "device_register": "/passport/device/register/",
    }

    # Live action burst sizes (matching real TikTok app behavior)
    LIVE_LIKE_COUNT_MIN = 1
    LIVE_LIKE_COUNT_MAX = 5
    LIVE_SHARE_COUNT_MIN = 1
    LIVE_SHARE_COUNT_MAX = 3

    def __init__(self, dashboard: Optional[Dashboard] = None):
        self.dashboard = dashboard or Dashboard()
        self.proxy_manager = ProxyManager()
        self.account_generator = None
        
        from Generate import AccountGenerator
        self.account_generator = AccountGenerator()
        
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
            "likes_completed": 0,
            "likes_failed": 0,
            "shares_completed": 0,
            "shares_failed": 0,
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
                              use_proxy: bool = True,
                              custom_headers: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a signed request to TikTok API.
        Uses full signature generation via SignerPy with all headers:
        x-gorgon, x-argus, x-ladon, x-khronos, x-ss-stub, x-ss-req-ticket, x-token
        """
        device_id = None
        session_token = None
        cookies = ""
        
        if account:
            device_id = account.get("device_id")
            session_token = account.get("session_token")
            session = self.load_account_sessions(account.get("username", ""))
            if session:
                cookies = session.get("cookie", "")

        # Generate all signatures
        signer = TikTokSigner(device_id=device_id)
        headers = signer.sign_request(url, data=body, cookies=cookies, method=method)
        
        if custom_headers:
            headers.update(custom_headers)
        
        if session_token:
            headers["X-Session-Token"] = session_token
        
        # Proxy
        proxies = None
        if use_proxy:
            proxy_url = self.proxy_manager.get_proxy_url()
            if proxy_url:
                proxies = {"http": proxy_url, "https": proxy_url}
                if self.dashboard:
                    self.dashboard.update(current_proxy=proxy_url)

        try:
            with self._lock:
                self.stats["requests_sent"] += 1
            
            if method == "GET":
                resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            else:
                resp = requests.post(url, headers=headers, data=body, proxies=proxies, timeout=15)
            
            status_code = resp.status_code
            
            if status_code == 200:
                with self._lock:
                    self.stats["requests_success"] += 1
                return resp.json()
            elif status_code == 429:
                # Rate limited - back off
                with self._lock:
                    self.stats["requests_failed"] += 1
                if self.dashboard:
                    self.dashboard.update(errors_last="Rate limited (429)")
                time.sleep(random.uniform(5, 10))
                return None
            else:
                with self._lock:
                    self.stats["requests_failed"] += 1
                if self.dashboard:
                    self.dashboard.update(errors_last=f"HTTP {status_code}")
                return None
                
        except requests.RequestException as e:
            with self._lock:
                self.stats["requests_failed"] += 1
            if self.dashboard:
                err_msg = str(e)[:60]
                self.dashboard.update(errors_last=err_msg)
            return None

    def _build_base_params(self, account: Optional[Dict] = None) -> Dict:
        """Build standard base parameters for TikTok API requests"""
        device_id = account.get("device_id", "0") if account else "0"
        
        return {
            "aid": config.get("app_id", 1233),
            "app_name": "musically_go",
            "device_platform": config.get("device_platform", "android"),
            "os_api": "29",
            "os_version": "12",
            "ssmix": "a",
            "manifest_version_code": "2023000000",
            "dpi": random.choice([420, 440, 480, 500, 512]),
            "carrier_region": "US",
            "ac": random.choice(["wifi", "4g", "5g"]),
            "channel": "googleplay",
            "update_version_code": "2023000000",
            "app_type": "normal",
            "tz_name": random.choice(["America/New_York", "America/Los_Angeles", "America/Chicago"]),
            "account_region": "US",
            "sys_region": "US",
            "app_language": "en",
            "language": "en",
            "timezone_offset": random.choice(["-14400", "-18000", "-21600", "-25200", "-28800"]),
            "device_id": device_id,
            "version_code": "310502",
            "resolution": random.choice(["1440*3088", "1080*2400", "1440*3120", "1440*3216"]),
        }

    # ============================================================
    # VIDEO VIEW
    # ============================================================

    def simulate_view(self, video_id: str, account: Optional[Dict] = None) -> bool:
        """Simulate a view on a TikTok video via /aweme/v1/aweme/stats/ with stats_type=1"""
        if account and self.dashboard:
            self.dashboard.update(current_account=account.get("username", "unknown"))
        
        base_host = random.choice(TikTokSigner().get_api_hosts())
        params = self._build_base_params(account)
        
        query_string = urlencode(params)
        url = f"https://{base_host}/aweme/v1/aweme/stats/?{query_string}"
        
        payload = json.dumps({
            "item_id": video_id,
            "stats_type": 1,
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

    # ============================================================
    # VIDEO LIKE
    # ============================================================

    def simulate_video_like(self, video_id: str, account: Optional[Dict] = None) -> bool:
        """Like a video via /aweme/v1/aweme/stats/ with stats_type=2"""
        if account and self.dashboard:
            self.dashboard.update(current_account=account.get("username", "unknown"))
        
        base_host = random.choice(TikTokSigner().get_api_hosts())
        params = self._build_base_params(account)
        
        query_string = urlencode(params)
        url = f"https://{base_host}/aweme/v1/aweme/stats/?{query_string}"
        
        payload = json.dumps({
            "item_id": video_id,
            "stats_type": 2,
            "source": 0,
            "sec_user_id": "",
            "author_id": "",
        })
        
        result = self._make_signed_request(url, method="POST", body=payload, account=account)
        
        if result:
            with self._lock:
                self.stats["likes_completed"] += 1
            return True
        
        with self._lock:
            self.stats["likes_failed"] += 1
        return False

    # ============================================================
    # VIDEO SHARE
    # ============================================================

    def simulate_video_share(self, video_id: str, account: Optional[Dict] = None) -> bool:
        """Share a video via /aweme/v1/aweme/stats/ with stats_type=3"""
        if account and self.dashboard:
            self.dashboard.update(current_account=account.get("username", "unknown"))
        
        base_host = random.choice(TikTokSigner().get_api_hosts())
        params = self._build_base_params(account)
        
        query_string = urlencode(params)
        url = f"https://{base_host}/aweme/v1/aweme/stats/?{query_string}"
        
        payload = json.dumps({
            "item_id": video_id,
            "stats_type": 3,
            "source": random.randint(0, 7),
            "sec_user_id": "",
            "author_id": "",
        })
        
        result = self._make_signed_request(url, method="POST", body=payload, account=account)
        
        if result:
            with self._lock:
                self.stats["shares_completed"] += 1
            return True
        
        with self._lock:
            self.stats["shares_failed"] += 1
        return False

    # ============================================================
    # LIVE STREAM ENTER (VIEW)
    # ============================================================

    def simulate_live_view(self, room_id: str, account: Optional[Dict] = None) -> bool:
        """
        Enter a live stream via /aweme/v1/live/enter/
        This makes the account appear as a viewer in the live room.
        Required before likes/shares can be sent.
        """
        if account and self.dashboard:
            self.dashboard.update(current_account=account.get("username", "unknown"))
        
        base_host = random.choice(TikTokSigner().get_api_hosts())
        params = self._build_base_params(account)
        params.update({
            "room_id": room_id,
            "live_id": 1,
            "orientation": random.choice([0, 90, 180]),
            "enter_from": random.choice(["homepage_hot", "following_live", "hashtag_live", "search_live"]),
            "scene": "live_room",
            "type": "enter",
        })
        
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

    # ============================================================
    # LIVE STREAM HEARTBEAT (keep connection alive)
    # ============================================================

    def simulate_live_heartbeat(self, room_id: str, account: Optional[Dict] = None) -> bool:
        """
        Send heartbeat to maintain live room connection.
        This prevents TikTok from removing the viewer from the room.
        """
        base_host = random.choice(TikTokSigner().get_api_hosts())
        params = self._build_base_params(account)
        params.update({
            "room_id": room_id,
            "live_id": 1,
        })
        
        query_string = urlencode(params)
        url = f"https://{base_host}/aweme/v1/live/heartbeat/?{query_string}"
        
        payload = json.dumps({
            "room_id": room_id,
            "heartbeat_duration": random.randint(5, 15),
        })
        
        result = self._make_signed_request(url, method="POST", body=payload, account=account)
        return result is not None

    # ============================================================
    # LIVE STREAM LIKE (❤️)
    # ============================================================

    def simulate_live_like(self, room_id: str, account: Optional[Dict] = None,
                           like_count: Optional[int] = None) -> bool:
        """
        Send likes to a live stream via /aweme/v1/live/like/
        
        TikTok live likes are sent as bursts. The endpoint accepts:
        - like_count: Number of likes to send in one request (1-5)
        - Real TikTok app sends 1-5 likes per request
        
        Args:
            room_id: The live room ID
            account: Account dict with device_id, session, etc.
            like_count: Number of likes (1-5). Random if None.
        
        Returns:
            True if successful
        """
        if account and self.dashboard:
            self.dashboard.update(current_account=account.get("username", "unknown"))
        
        if like_count is None:
            like_count = random.randint(self.LIVE_LIKE_COUNT_MIN, self.LIVE_LIKE_COUNT_MAX)
        
        base_host = random.choice(TikTokSigner().get_api_hosts())
        params = self._build_base_params(account)
        params.update({
            "room_id": room_id,
            "live_id": 1,
        })
        
        query_string = urlencode(params)
        url = f"https://{base_host}/aweme/v1/live/like/?{query_string}"
        
        payload = json.dumps({
            "room_id": room_id,
            "like_count": like_count,
            "source": random.randint(0, 2),
            "trigger": random.randint(0, 2),
        })
        
        result = self._make_signed_request(url, method="POST", body=payload, account=account)
        
        if result:
            with self._lock:
                self.stats["likes_completed"] += like_count
            if self.dashboard:
                self.dashboard.update(likes_completed=self.stats["likes_completed"])
            return True
        
        with self._lock:
            self.stats["likes_failed"] += 1
        return False

    # ============================================================
    # LIVE STREAM SHARE (🔗)
    # ============================================================

    def simulate_live_share(self, room_id: str, account: Optional[Dict] = None,
                            share_count: Optional[int] = None) -> bool:
        """
        Share a live stream via /aweme/v1/live/share/
        
        TikTok supports sharing to multiple platforms:
        0 = Copy link, 1 = Feed, 2 = WhatsApp, 3 = Instagram,
        4 = Twitter, 5 = SMS, 6 = Messenger, 7 = Snapchat
        
        Args:
            room_id: The live room ID
            account: Account dict
            share_count: Number of shares (1-3). Random if None.
        
        Returns:
            True if successful
        """
        if account and self.dashboard:
            self.dashboard.update(current_account=account.get("username", "unknown"))
        
        if share_count is None:
            share_count = random.randint(self.LIVE_SHARE_COUNT_MIN, self.LIVE_SHARE_COUNT_MAX)
        
        share_types = [0, 1, 2, 3, 4, 5, 6, 7]
        
        base_host = random.choice(TikTokSigner().get_api_hosts())
        params = self._build_base_params(account)
        params.update({
            "room_id": room_id,
            "live_id": 1,
        })
        
        query_string = urlencode(params)
        url = f"https://{base_host}/aweme/v1/live/share/?{query_string}"
        
        payload = json.dumps({
            "room_id": room_id,
            "share_count": share_count,
            "share_type": random.choice(share_types),
            "source": "homepage_hot",
        })
        
        result = self._make_signed_request(url, method="POST", body=payload, account=account)
        
        if result:
            with self._lock:
                self.stats["shares_completed"] += share_count
            if self.dashboard:
                self.dashboard.update(shares_completed=self.stats["shares_completed"])
            return True
        
        with self._lock:
            self.stats["shares_failed"] += 1
        return False

    # ============================================================
    # COMBINED LIVE ACTIONS (Like + Share + View loop)
    # ============================================================

    def perform_live_actions(self, room_id: str, account: Optional[Dict] = None,
                             actions: str = "all") -> Dict[str, bool]:
        """
        Perform a combination of live stream actions.
        Simulates natural user behavior: enter room -> like -> share
        
        Args:
            room_id: Live room ID
            account: Account to use
            actions: Comma-separated: "view", "like", "share" or "all"
        
        Returns:
            Dict with results per action type
        """
        results = {}
        actions_list = ["view", "like", "share"] if actions == "all" else [a.strip() for a in actions.split(",")]
        
        for action in actions_list:
            if action == "view":
                results["view"] = self.simulate_live_view(room_id, account)
                if results["view"]:
                    # Send heartbeat to stay connected
                    self.simulate_live_heartbeat(room_id, account)
                time.sleep(random.uniform(1.0, 3.0))
            elif action == "like":
                # Send multiple like bursts for natural behavior
                bursts = random.randint(1, 3)
                for b in range(bursts):
                    results["like"] = self.simulate_live_like(room_id, account)
                    time.sleep(random.uniform(0.3, 1.5))
            elif action == "share":
                results["share"] = self.simulate_live_share(room_id, account)
                time.sleep(random.uniform(1.0, 3.0))
            
            # Small delay between different action types
            time.sleep(random.uniform(1.0, 3.0))
        
        return results

    # ============================================================
    # WORKER THREADS
    # ============================================================

    def _view_worker(self, video_id: str, view_count: int):
        """Worker for video views"""
        while self._running and view_count > 0:
            account = self.get_next_account()
            if not account:
                time.sleep(1)
                continue
            
            with self._lock:
                self.stats["views_in_progress"] += 1
            
            success = self.simulate_view(video_id, account)
            
            with self._lock:
                self.stats["views_in_progress"] -= 1
            
            if success:
                view_count -= 1
                self._update_dashboard()
            
            delay = random.uniform(
                config.get("view_delay_min", 3),
                config.get("view_delay_max", 8)
            )
            time.sleep(delay)

    def _live_view_worker(self, room_id: str, view_count: int):
        """Worker for live stream views with natural like/share behavior"""
        while self._running and view_count > 0:
            account = self.get_next_account()
            if not account:
                time.sleep(1)
                continue
            
            with self._lock:
                self.stats["views_in_progress"] += 1
            
            # Enter the live room
            success = self.simulate_live_view(room_id, account)
            
            if success:
                view_count -= 1
                
                # Send heartbeat to stay connected
                self.simulate_live_heartbeat(room_id, account)
                
                # Natural behavior: 40% chance to like while watching
                if random.random() < 0.4:
                    self.simulate_live_like(room_id, account, random.randint(1, 3))
                    time.sleep(random.uniform(0.5, 2.0))
                
                # 15% chance to share while watching
                if random.random() < 0.15:
                    self.simulate_live_share(room_id, account, random.randint(1, 2))
                    time.sleep(random.uniform(0.5, 2.0))
                
                # 10% chance to like again before leaving
                if random.random() < 0.1:
                    self.simulate_live_like(room_id, account, random.randint(1, 2))
            
            with self._lock:
                self.stats["views_in_progress"] -= 1
            
            if success:
                self._update_dashboard()
            
            delay = random.uniform(
                config.get("view_delay_min", 3),
                config.get("view_delay_max", 8)
            )
            time.sleep(delay)

    def _live_like_worker(self, room_id: str, like_target: int):
        """Worker for sending live stream likes"""
        while self._running and like_target > 0:
            account = self.get_next_account()
            if not account:
                time.sleep(1)
                continue
            
            like_count = min(
                random.randint(self.LIVE_LIKE_COUNT_MIN, self.LIVE_LIKE_COUNT_MAX),
                like_target
            )
            
            success = self.simulate_live_like(room_id, account, like_count)
            
            if success:
                like_target -= like_count
                self._update_dashboard()
            
            delay = random.uniform(1.0, 3.0)
            time.sleep(delay)

    def _live_share_worker(self, room_id: str, share_target: int):
        """Worker for sending live stream shares"""
        while self._running and share_target > 0:
            account = self.get_next_account()
            if not account:
                time.sleep(1)
                continue
            
            share_count = min(
                random.randint(self.LIVE_SHARE_COUNT_MIN, self.LIVE_SHARE_COUNT_MAX),
                share_target
            )
            
            success = self.simulate_live_share(room_id, account, share_count)
            
            if success:
                share_target -= share_count
                self._update_dashboard()
            
            delay = random.uniform(2.0, 5.0)
            time.sleep(delay)

    def _campaign_worker(self, room_id: str, view_target: int,
                          like_prob: float, share_prob: float):
        """Worker for full campaign: views + likes + shares in natural proportions"""
        while self._running and view_target > 0:
            account = self.get_next_account()
            if not account:
                time.sleep(1)
                continue
            
            # Enter live
            if self.simulate_live_view(room_id, account):
                view_target -= 1
                
                # Send heartbeat
                self.simulate_live_heartbeat(room_id, account)
                
                # Like with probability
                if random.random() < like_prob:
                    self.simulate_live_like(room_id, account, random.randint(1, 5))
                    time.sleep(random.uniform(0.3, 1.5))
                
                # Share with probability
                if random.random() < share_prob:
                    self.simulate_live_share(room_id, account, random.randint(1, 2))
                    time.sleep(random.uniform(0.3, 1.5))
                
                self._update_dashboard()
            
            delay = random.uniform(
                config.get("view_delay_min", 3),
                config.get("view_delay_max", 8)
            )
            time.sleep(delay)

    # ============================================================
    # ORCHESTRATION
    # ============================================================

    def start_views(self, video_id: str, total_views: int, 
                    threads: int = None, is_live: bool = False):
        """Start video or live stream view simulation"""
        if self._running:
            print("  [!] Bot is already running")
            return
        
        thread_count = threads or config.get("threads", 5)
        views_per_thread = max(1, total_views // thread_count)
        
        self._running = True
        target_type = "live" if is_live else "video"
        
        if self.dashboard:
            self.dashboard.update(
                status="Running",
                views_target_video=video_id,
                views_target_count=total_views,
                operation=f"Sending {total_views} {target_type} views via {thread_count} threads",
                campaign_type=f"{target_type.upper()} Views"
            )
            self.dashboard.start()
        
        print(f"\n  [*] Starting {thread_count} threads for {total_views} {target_type} views")
        print(f"  [*] Target: {video_id}")
        print(f"  [*] Accounts loaded: {len(self._accounts)}")
        print(f"  [*] Proxies working: {self.proxy_manager.get_working_count()}")
        print(f"\n  [!] Dashboard active - press Ctrl+C to stop\n")
        
        self._threads = []
        worker_fn = self._live_view_worker if is_live else self._view_worker
        for i in range(thread_count):
            t = threading.Thread(
                target=worker_fn,
                args=(video_id, views_per_thread),
                daemon=True
            )
            t.start()
            self._threads.append(t)
        
        try:
            while any(t.is_alive() for t in self._threads):
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  [!] Stopping bot...")
        finally:
            self.stop()

    def start_live_likes(self, room_id: str, total_likes: int, threads: int = None):
        """Start sending likes to a live stream"""
        if self._running:
            print("  [!] Bot is already running")
            return
        
        thread_count = threads or min(config.get("threads", 5), total_likes)
        likes_per_thread = max(1, total_likes // thread_count)
        
        self._running = True
        
        if self.dashboard:
            self.dashboard.update(
                status="Running - Likes",
                views_target_video=room_id,
                views_target_count=total_likes,
                operation=f"Sending {total_likes} likes via {thread_count} threads",
                campaign_type="LIVE LIKES"
            )
            self.dashboard.start()
        
        print(f"\n  [*] Starting {thread_count} threads for {total_likes} live likes")
        print(f"  [*] Room ID: {room_id}")
        print(f"  [*] Accounts: {len(self._accounts)} | Proxies: {self.proxy_manager.get_working_count()}")
        
        self._threads = []
        for i in range(thread_count):
            t = threading.Thread(
                target=self._live_like_worker,
                args=(room_id, likes_per_thread),
                daemon=True
            )
            t.start()
            self._threads.append(t)
        
        try:
            while any(t.is_alive() for t in self._threads):
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  [!] Stopping...")
        finally:
            self.stop()

    def start_live_shares(self, room_id: str, total_shares: int, threads: int = None):
        """Start sending shares to a live stream"""
        if self._running:
            print("  [!] Bot is already running")
            return
        
        thread_count = threads or min(config.get("threads", 5), total_shares)
        shares_per_thread = max(1, total_shares // thread_count)
        
        self._running = True
        
        if self.dashboard:
            self.dashboard.update(
                status="Running - Shares",
                views_target_video=room_id,
                views_target_count=total_shares,
                operation=f"Sending {total_shares} shares via {thread_count} threads",
                campaign_type="LIVE SHARES"
            )
            self.dashboard.start()
        
        print(f"\n  [*] Starting {thread_count} threads for {total_shares} live shares")
        print(f"  [*] Room ID: {room_id}")
        print(f"  [*] Accounts: {len(self._accounts)} | Proxies: {self.proxy_manager.get_working_count()}")
        
        self._threads = []
        for i in range(thread_count):
            t = threading.Thread(
                target=self._live_share_worker,
                args=(room_id, shares_per_thread),
                daemon=True
            )
            t.start()
            self._threads.append(t)
        
        try:
            while any(t.is_alive() for t in self._threads):
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  [!] Stopping...")
        finally:
            self.stop()

    def start_live_campaign(self, room_id: str, total_views: int, 
                            like_prob: float = 0.3,
                            share_prob: float = 0.1,
                            threads: int = None):
        """
        Start a full live campaign: views + likes + shares in natural proportions.
        
        This is the most effective mode for live streams because it simulates
        real user behavior: enter room, watch for a bit, like occasionally, share rarely.
        
        Args:
            room_id: Live room ID
            total_views: Number of view entries
            like_prob: Probability of liking during a view (0.0 - 1.0)
            share_prob: Probability of sharing during a view (0.0 - 1.0)
            threads: Number of threads
        """
        if self._running:
            print("  [!] Bot is already running")
            return
        
        thread_count = threads or config.get("threads", 5)
        views_per_thread = max(1, total_views // thread_count)
        
        self._running = True
        
        estimated_likes = int(total_views * like_prob * 2)  # x2 because each like sends 1-5
        estimated_shares = int(total_views * share_prob)
        
        if self.dashboard:
            self.dashboard.update(
                status="Running - Campaign",
                views_target_video=room_id,
                views_target_count=total_views,
                operation=f"Campaign: {total_views} views + likes + shares",
                campaign_type=f"FULL CAMPAIGN (est. {estimated_likes} likes, {estimated_shares} shares)"
            )
            self.dashboard.start()
        
        print(f"\n  {'='*55}")
        print(f"  🎯 FULL LIVE CAMPAIGN")
        print(f"  {'='*55}")
        print(f"  Room ID:     {room_id}")
        print(f"  Views:       {total_views}")
        print(f"  Est. Likes:  {estimated_likes}  (prob: {like_prob:.0%})")
        print(f"  Est. Shares: {estimated_shares}  (prob: {share_prob:.0%})")
        print(f"  Threads:     {thread_count}")
        print(f"  Accounts:    {len(self._accounts)}")
        print(f"  Proxies:     {self.proxy_manager.get_working_count()}")
        print(f"  {'='*55}")
        print(f"\n  [!] Dashboard active - press Ctrl+C to stop\n")
        
        self._threads = []
        for i in range(thread_count):
            t = threading.Thread(
                target=self._campaign_worker,
                args=(room_id, views_per_thread, like_prob, share_prob),
                daemon=True
            )
            t.start()
            self._threads.append(t)
        
        try:
            while any(t.is_alive() for t in self._threads):
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  [!] Stopping campaign...")
        finally:
            self.stop()

    def stop(self):
        """Stop all bot operations"""
        self._running = False
        
        for t in self._threads:
            t.join(timeout=3)
        
        self._threads.clear()
        
        if self.dashboard:
            self.dashboard.update(status="Stopped")
            self.dashboard.stop()
        
        self._print_final_stats()

    def _update_dashboard(self):
        """Thread-safe dashboard update"""
        if self.dashboard:
            with self._lock:
                self.dashboard.update(
                    views_completed=self.stats["views_completed"],
                    views_failed=self.stats["views_failed"],
                    likes_completed=self.stats["likes_completed"],
                    likes_failed=self.stats["likes_failed"],
                    shares_completed=self.stats["shares_completed"],
                    shares_failed=self.stats["shares_failed"],
                    requests_sent=self.stats["requests_sent"],
                    requests_success=self.stats["requests_success"],
                    requests_failed=self.stats["requests_failed"],
                    accounts_total_views=sum(a.get("total_views", 0) for a in self._accounts),
                )

    def _print_final_stats(self):
        """Print final statistics"""
        success_rate = 0
        if self.stats["requests_sent"] > 0:
            success_rate = (self.stats["requests_success"] / self.stats["requests_sent"]) * 100
        
        print(f"\n  {'='*55}")
        print(f"  📊 FINAL STATISTICS")
        print(f"  {'='*55}")
        print(f"  👁️  Views:     {self.stats['views_completed']} completed, {self.stats['views_failed']} failed")
        print(f"  ❤️  Likes:     {self.stats['likes_completed']} completed, {self.stats['likes_failed']} failed")
        print(f"  🔗  Shares:    {self.stats['shares_completed']} completed, {self.stats['shares_failed']} failed")
        print(f"  📡  Requests:  {self.stats['requests_sent']} sent, {self.stats['requests_success']} success, {self.stats['requests_failed']} failed")
        print(f"  📊  Rate:      {success_rate:.1f}% success")
        print(f"  {'='*55}")

    def setup_proxies(self, auto_scrape: bool = None):
        """Initialize proxy pool"""
        if auto_scrape is None:
            auto_scrape = config.get("auto_scrape_proxies", True)
        
        if auto_scrape:
            print("\n  [*] Scraping proxies from 18+ sources...")
            
            def scrape_progress(current, total, msg):
                print(f"\r  [*] {msg} ({current}/{total})", end="")
                sys.stdout.flush()
            
            self.proxy_manager.scrape_proxies(progress_callback=scrape_progress)
            
            if self.proxy_manager.proxies:
                print(f"\n  [*] Checking {len(self.proxy_manager.proxies)} proxies...")
                
                def check_progress(current, total, msg):
                    print(f"\r  [*] {msg}", end="")
                    sys.stdout.flush()
                
                self.proxy_manager.check_proxies(progress_callback=check_progress)
        
        if self.dashboard:
            proxy_stats = self.proxy_manager.get_proxy_stats()
            self.dashboard.update(
                proxies_total=proxy_stats["total"],
                proxies_working=proxy_stats["total"],
            )
        
        return self.proxy_manager.get_working_count()
