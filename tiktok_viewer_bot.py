#!/usr/bin/env python3
"""
TikTok Live Viewer Injector - Pure HTTP, No Browser
For authorized pentesting only - integrates with proxy validator
"""

import requests
import json
import time
import random
import string
import threading
import os
import sys
import hashlib
import urllib.parse
import base64
import logging
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('viewer_bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
TIKTOK_API = "https://api22-normal-c-useast1a.tiktokv.com"
TIKTOK_WEB = "https://www.tiktok.com"

ANDROID_DEVICES = [
    {'device_id': 'android_7255253607933979658', 'iid': '72552536079339796580', 'openudid': 'f1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6', 'model': 'SM-G998B', 'brand': 'samsung', 'os_version': '13', 'resolution': '1440*3200', 'dpi': '560', 'os_api': '33'},
    {'device_id': 'android_8355253607933979669', 'iid': '83552536079339796690', 'openudid': 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d7', 'model': 'Pixel 8 Pro', 'brand': 'google', 'os_version': '14', 'resolution': '1344*2992', 'dpi': '420', 'os_api': '34'},
    {'device_id': 'android_9455253612938979670', 'iid': '94552536129389796700', 'openudid': 'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e8', 'model': 'OnePlus 12', 'brand': 'oneplus', 'os_version': '14', 'resolution': '1440*3168', 'dpi': '510', 'os_api': '34'},
    {'device_id': 'android_1155253612938979671', 'iid': '11552536129389796710', 'openudid': 'c3d4e5f6a7b8c9d0e1f2a3b4c5d6e8f9', 'model': 'Xiaomi 14 Pro', 'brand': 'xiaomi', 'os_version': '14', 'resolution': '1440*3200', 'dpi': '522', 'os_api': '34'},
    {'device_id': 'android_1255253612938979672', 'iid': '12552536129389796720', 'openudid': 'd4e5f6a7b8c9d0e1f2a3b4c5d6e8f9a0', 'model': 'Pixel 7', 'brand': 'google', 'os_version': '13', 'resolution': '1080*2400', 'dpi': '420', 'os_api': '33'},
    {'device_id': 'android_1355253612938979673', 'iid': '13552536129389796730', 'openudid': 'e5f6a7b8c9d0e1f2a3b4c5d6e8f9a0b1', 'model': 'SM-S928B', 'brand': 'samsung', 'os_version': '14', 'resolution': '1440*3200', 'dpi': '560', 'os_api': '34'},
    {'device_id': 'android_1455253612938979674', 'iid': '14552536129389796740', 'openudid': 'f6a7b8c9d0e1f2a3b4c5d6e8f9a0b1c2', 'model': 'Moto G Power', 'brand': 'motorola', 'os_version': '13', 'resolution': '1080*2400', 'dpi': '400', 'os_api': '33'},
    {'device_id': 'android_1555253612938979675', 'iid': '15552536129389796750', 'openudid': 'a7b8c9d0e1f2a3b4c5d6e8f9a0b1c2d3', 'model': 'Xperia 1 V', 'brand': 'sony', 'os_version': '13', 'resolution': '1644*3840', 'dpi': '643', 'os_api': '33'},
]

# ──────────────────────────────────────────────
# SIGNATURE GENERATION
# ──────────────────────────────────────────────
def generate_x_bogus(params, device_id='7255253607933979658'):
    """Generate TikTok X-Bogus signature (simplified)"""
    keys = sorted(params.keys())
    query = '&'.join([f"{k}={urllib.parse.quote(str(params[k]))}" for k in keys])
    
    # Build signature string
    sig_base = f"{query}&device_id={device_id}"
    sig = hashlib.md5(sig_base.encode()).hexdigest()
    
    # X-Bogus format: 3 chars header + hash + 3 chars footer
    header = ''.join(random.choices(string.ascii_letters + string.digits, k=3))
    footer = ''.join(random.choices(string.ascii_letters + string.digits, k=3))
    
    return f"{header}{sig[:27]}{footer}"


def generate_x_ss_stub(params):
    """Generate X-SS-STUB signature"""
    keys = sorted(params.keys())
    query = json.dumps({k: params[k] for k in keys}, separators=(',', ':'))
    return hashlib.sha256(query.encode()).hexdigest()

# ──────────────────────────────────────────────
# VIEWER BOT ENGINE
# ──────────────────────────────────────────────
class TikTokViewerBot:
    def __init__(self, proxy_file='tiktok_proxies.txt'):
        self.proxies = self._load_proxies(proxy_file)
        self.proxy_pool = cycle(self.proxies)
        self.device_pool = cycle(ANDROID_DEVICES)
        self.session_pool = {}
        self.lock = threading.Lock()
        self.stats = {
            'views_injected': 0,
            'active_viewers': 0,
            'success_joins': 0,
            'failed_joins': 0,
            'heartbeats_sent': 0,
            'start_time': datetime.now()
        }
        self.running = True
        
        log.info(f"Loaded {len(self.proxies)} TikTok-valid proxies")
    
    def _load_proxies(self, filename):
        """Load proxy list"""
        proxies = []
        if filename and os.path.exists(filename):
            with open(filename) as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        if not proxies:
            log.warning("No proxies found! Using direct connection (will be blocked quickly)")
            proxies = ['direct']
        
        return proxies
    
    def _get_session(self, proxy):
        """Get or create a requests session for a proxy"""
        if proxy not in self.session_pool:
            session = requests.Session()
            session.headers.update({
                'Accept': '*/*',
                'Accept-Encoding': 'gzip',
                'Accept-Language': 'en,en-US;q=0.9',
                'Content-Type': 'application/json; charset=utf-8',
                'Connection': 'keep-alive',
                'Host': 'api22-normal-c-useast1a.tiktokv.com',
            })
            
            if proxy != 'direct':
                session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
            
            self.session_pool[proxy] = session
        
        return self.session_pool[proxy]
    
    def _get_android_headers(self, device):
        """Generate Android app headers"""
        return {
            'User-Agent': f'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android {device["os_version"]}; en; {device["model"]} Build/TP1A.220624.014; Cronet/112.0.5615.140)',
            'X-Tt-Token': ''.join(random.choices('0123456789abcdef', k=32)),
            'X-Khronos': str(int(time.time())),
        }
    
    def _generate_params(self, room_id, device, extra=None):
        """Generate full request params with device fingerprint"""
        ts = int(time.time())
        params = {
            'device_id': device['device_id'],
            'iid': device['iid'],
            'openudid': device['openudid'],
            'device_platform': 'android',
            'os_version': device['os_version'],
            'resolution': device['resolution'],
            'dpi': device['dpi'],
            'os_api': device['os_api'],
            'aid': '1180',
            'app_version': '35.7.0',
            'app_name': 'trill',
            'channel': 'googleplay',
            'build_number': '357000',
            'tz_name': 'America/New_York',
            'sys_region': 'US',
            'app_language': 'en',
            'language': 'en',
            'region': 'US',
            '_rticket': ts * 1000,
            'ts': ts,
            'room_id': room_id,
            'cdid': ''.join(random.choices(string.hexdigits, k=32)).lower(),
            'req_id': ''.join(random.choices(string.hexdigits, k=32)).upper(),
            'mcc_mnc': '310410',
        }
        
        if extra:
            params.update(extra)
        
        return params
    
    def _sign_headers(self, params):
        """Add signed headers to request"""
        device_id = params.get('device_id', '7255253607933979658')
        url_params = {k: v for k, v in params.items() if k not in ['device_platform', 'os_version', 'resolution', 'dpi', 'os_api', 'aid', 'app_version', 'app_name', 'channel', 'build_number']}
        
        return {
            'X-Bogus': generate_x_bogus(url_params, device_id),
            'X-SS-STUB': generate_x_ss_stub(url_params),
            'X-Ladon': ''.join(random.choices(string.hexdigits, k=32)).lower(),
        }
    
    def _join_live_room(self, session, room_id, device):
        """Join a live room - this adds +1 to viewer count"""
        url = f"{TIKTOK_API}/aweme/v1/webcast/join/"
        
        params = self._generate_params(room_id, device, {
            'enter_from': random.choice(['live_center', 'feed', 'share', 'scan', 'push']),
            'enter_method': random.choice(['scan', 'feed', 'share', 'push']),
            'priority_region': 'US',
            'live_id': random.randint(100000, 999999),
        })
        
        signed = self._sign_headers(params)
        
        headers = self._get_android_headers(device)
        headers.update(signed)
        
        payload = {
            "room_id": int(room_id),
            "user_id": f"viewer_{random.randint(10000000, 99999999)}",
            "enter_method": params['enter_method'],
            "device_id": params['device_id'],
            "iid": params['iid'],
            "live_id": params['live_id'],
            "priority_region": "US"
        }
        
        try:
            resp = session.post(url, json=payload, headers=headers, timeout=12)
            
            if resp.status_code in [200, 204, 0]:
                with self.lock:
                    self.stats['success_joins'] += 1
                    self.stats['active_viewers'] += 1
                    self.stats['views_injected'] += 1
                return True
            else:
                with self.lock:
                    self.stats['failed_joins'] += 1
                return False
                
        except Exception as e:
            with self.lock:
                self.stats['failed_joins'] += 1
            return False
    
    def _heartbeat(self, session, room_id, device):
        """Send periodic heartbeats to keep viewer counted"""
        url = f"{TIKTOK_API}/aweme/v1/webcast/enter/"
        hb_count = 0
        
        while self.running:
            try:
                params = self._generate_params(room_id, device, {
                    'status': 1,
                    'live_id': random.randint(1, 99999),
                })
                
                signed = self._sign_headers(params)
                headers = self._get_android_headers(device)
                headers.update(signed)
                
                payload = {
                    "room_id": int(room_id),
                    "status": 1,
                    "device_id": params['device_id'],
                    "live_id": params['live_id']
                }
                
                session.post(url, json=payload, headers=headers, timeout=8)
                
                with self.lock:
                    self.stats['heartbeats_sent'] += 1
                
                hb_count += 1
                
                # TikTok expects heartbeats every 25-35 seconds
                time.sleep(random.uniform(25, 35))
                
            except:
                time.sleep(5)
    
    def _leave_room(self, session, room_id, device):
        """Leave the live room gracefully"""
        url = f"{TIKTOK_API}/aweme/v1/webcast/leave/"
        
        params = self._generate_params(room_id, device)
        signed = self._sign_headers(params)
        headers = self._get_android_headers(device)
        headers.update(signed)
        
        payload = {
            "room_id": int(room_id),
            "device_id": params['device_id']
        }
        
        try:
            session.post(url, json=payload, headers=headers, timeout=8)
        except:
            pass
        
        with self.lock:
            self.stats['active_viewers'] -= 1
    
    def simulate_viewer(self, room_id, duration_seconds=600):
        """Simulate a single viewer: join → heartbeat → leave"""
        proxy = next(self.proxy_pool)
        session = self._get_session(proxy)
        device = next(self.device_pool)
        
        # Join the live room
        if not self._join_live_room(session, room_id, device):
            return False
        
        # Start heartbeat thread
        hb_thread = threading.Thread(
            target=self._heartbeat,
            args=(session, room_id, device),
            daemon=True
        )
        hb_thread.start()
        
        # Stay for specified duration
        end_time = time.time() + duration_seconds
        while self.running and time.time() < end_time:
            time.sleep(1)
        
        # Leave
        self._leave_room(session, room_id, device)
        return True
    
    def print_stats(self):
        """Print current stats"""
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        rate = self.stats['views_injected'] / elapsed if elapsed > 0 else 0
        
        print(f"\r[📊] Views: {self.stats['views_injected']:,} | "
              f"Active: {self.stats['active_viewers']} | "
              f"Joins: {self.stats['success_joins']:,} ✓ / {self.stats['failed_joins']:,} ✗ | "
              f"Heartbeats: {self.stats['heartbeats_sent']:,} | "
              f"Rate: {rate:.1f}/s | "
              f"Elapsed: {int(elapsed)}s", end='', flush=True)
    
    def launch_attack(self, room_id, viewer_count=1000, duration_seconds=600, workers=150):
        """Launch the viewer injection attack"""
        log.info(f"{'='*60}")
        log.info(f"🚀 TIKTOK LIVE VIEWER INJECTION")
        log.info(f"📺 Room ID: {room_id}")
        log.info(f"👥 Target Viewers: {viewer_count:,}")
        log.info(f"⏱ Duration: {duration_seconds}s ({duration_seconds//60}m)")
        log.info(f"⚙️ Workers: {workers}")
        log.info(f"🌐 Proxies: {len(self.proxies)}")
        log.info(f"{'='*60}")
        
        self.stats['start_time'] = datetime.now()
        
        # Start stats printer thread
        stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
        stats_thread.start()
        
        # Deploy viewers with staggered start
        successful = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {}
            
            for i in range(viewer_count):
                future = executor.submit(self.simulate_viewer, room_id, duration_seconds)
                futures[future] = i
                
                # Stagger joins (spread over first 30 seconds)
                stagger = random.uniform(0.05, 0.3)
                time.sleep(stagger)
            
            # Collect results
            for future in as_completed(futures):
                if future.result():
                    successful += 1
        
        elapsed = time.time() - start_time
        self.running = False
        
        print()  # Newline after stats
        log.info(f"{'='*60}")
        log.info(f"✅ ATTACK COMPLETE")
        log.info(f"📊 Final Statistics:")
        
        with self.lock:
            log.info(f"   Views Injected:    {self.stats['views_injected']:,}")
            log.info(f"   Successful Joins:  {self.stats['success_joins']:,}")
            log.info(f"   Failed Joins:      {self.stats['failed_joins']:,}")
            log.info(f"   Heartbeats Sent:   {self.stats['heartbeats_sent']:,}")
            log.info(f"   Peak Active:       {max(1, self.stats['active_viewers'])}")
            log.info(f"   Duration:          {elapsed:.1f}s")
            log.info(f"   Average Rate:      {self.stats['views_injected']/elapsed:.1f} viewers/s")
            log.info(f"   Success Rate:      {self.stats['success_joins']/(self.stats['success_joins']+self.stats['failed_joins']+0.001)*100:.1f}%")
        
        log.info(f"{'='*60}")
        
        return successful
    
    def _stats_loop(self):
        """Print stats periodically"""
        while self.running:
            self.print_stats()
            time.sleep(2)
    
    def stop(self):
        """Stop all operations"""
        self.running = False
        log.info("Stopping all viewers...")


# ──────────────────────────────────────────────
# ROOM ID EXTRACTION
# ──────────────────────────────────────────────
def extract_room_id_from_url(url):
    """Extract room_id from TikTok live URL"""
    patterns = [
        r'room_id=(\d+)',
        r'/live/(\d+)',
        r'live\.tiktok\.com/(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def get_live_room_info(username, proxies=None):
    """Get live room info from TikTok profile"""
    url = f"{TIKTOK_WEB}/@{username}/live"
    
    session = requests.Session()
    if proxies:
        proxy = random.choice(proxies) if isinstance(proxies, list) else proxies
        if proxy != 'direct':
            session.proxies = {'http': proxy, 'https': proxy}
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    
    try:
        # Try webcast API
        api_url = f"{TIKTOK_API}/aweme/v1/webcast/user/"
        params = {'user_id': username, 'aid': '1988'}
        
        resp = session.get(api_url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if 'room_id' in data:
                return data['room_id']
        
        # Try scraping from page
        resp = session.get(url, timeout=10)
        room_id_match = re.search(r'room_id["\']?\s*[:=]\s*["\']?(\d+)', resp.text)
        if room_id_match:
            return room_id_match.group(1)
        
    except Exception as e:
        log.error(f"Error fetching live info: {e}")
    
    return None

# ──────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="TikTok Live Viewer Injection Bot - Pure HTTP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use with proxy scraper output
  python tiktok_viewer_bot.py --room-id 1234567890123456789 --proxies tiktok_proxies.txt --viewers 5000
  
  # 10-minute attack with 10000 viewers
  python tiktok_viewer_bot.py --room-id 1234567890123456789 --proxies tiktok_proxies.txt --viewers 10000 --duration 600
  
  # Maximum scale (requires 5000+ proxies)
  python tiktok_viewer_bot.py --room-id 1234567890123456789 --proxies tiktok_proxies.txt --viewers 50000 --duration 3600 --workers 300
  
  # Extract room_id from TikTok username
  python tiktok_viewer_bot.py --username streamer_name --proxies tiktok_proxies.txt --viewers 3000
        """
    )
    
    parser.add_argument('--room-id', help='TikTok Live Room ID')
    parser.add_argument('--username', help='TikTok username (to extract room_id)')
    parser.add_argument('--proxies', default='tiktok_proxies.txt', help='Proxy list file (from scraper)')
    parser.add_argument('--viewers', type=int, default=1000, help='Number of viewers to inject')
    parser.add_argument('--duration', type=int, default=600, help='Duration in seconds (default: 600 = 10min)')
    parser.add_argument('--workers', type=int, default=150, help='Concurrent worker threads (default: 150)')
    parser.add_argument('--stats-only', action='store_true', help='Just show proxy stats, no attack')
    
    args = parser.parse_args()
    
    print("""
╔══════════════════════════════════════════════════════════╗
║          TIKTOK LIVE VIEWER INJECTION ENGINE             ║
║           Pure HTTP - No Browser Required                ║
║             For Authorized PenTesting                    ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Resolve room_id
    room_id = args.room_id
    
    if args.username and not room_id:
        log.info(f"Resolving room_id for @{args.username}...")
        room_id = get_live_room_info(args.username)
        if room_id:
            log.info(f"Found room_id: {room_id}")
        else:
            log.error(f"Could not find live room for @{args.username}")
            sys.exit(1)
    
    if not room_id:
        log.error("Room ID required. Use --room-id or --username")
        parser.print_help()
        sys.exit(1)
    
    # Initialize bot with proxies from scraper
    bot = TikTokViewerBot(proxy_file=args.proxies)
    
    # Stats only mode
    if args.stats_only:
        log.info(f"Proxy stats:")
        log.info(f"  Total proxies: {len(bot.proxies)}")
        log.info(f"  First 5: {bot.proxies[:5]}")
        sys.exit(0)
    
    # Verify proxy file has content
    if len(bot.proxies) < 10:
        log.warning(f"Only {len(bot.proxies)} proxies loaded. Run the proxy scraper first for better results.")
    
    try:
        # Launch the attack
        bot.launch_attack(
            room_id=room_id,
            viewer_count=args.viewers,
            duration_seconds=args.duration,
            workers=args.workers
        )
    except KeyboardInterrupt:
        log.info("\n[!] Interrupted by user. Stopping...")
        bot.stop()
        time.sleep(1)
        log.info("Done.")

if __name__ == "__main__":
    # Import re if not already
    import re
    main()
