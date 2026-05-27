#!/usr/bin/env python3
"""
TikTok Bot - Main Entry Point
Full featured menu: view bot, live likes/shares, campaign mode,
proxy manager with 18 sources, TikTok endpoint testing, live dashboard
Author: HackerAI PenTest Framework
"""
import os
import sys
import json
import time
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import config, load_config, save_config, set_path
from bot import TikTokBot
from dashboard import Dashboard
from proxy_manager import ProxyManager

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, IntPrompt, Confirm
    from rich import box
    from rich.text import Text
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


class Menu:
    """Interactive menu system for TikTok Bot"""

    BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║                    TikTok Bot v3.0                              ║
║          Full SignerPy - Live Dashboard - Campaign Mode         ║
║              Author: HackerAI PenTest Framework                 ║
╠══════════════════════════════════════════════════════════════════╣
║  FEATURES:                                                      ║
║  • Live Stream: VIEW + LIKE (❤️) + SHARE (🔗)                   ║
║  • Full Campaign: combine views, likes, shares naturally        ║
║  • SignerPy: x-gorgon(v1/v2/v3), x-argus, x-ladon, x-khronos   ║
║  • SM3, Protobuf, Simon cipher, ChaCha20, TTEncrypt, edata     ║
║  • Proxy: 18+ sources, 500-thread checker, TikTok endpoint test ║
║  • Account gen with realistic device profiles + sessions        ║
║  • Real-time rich dashboard with rates & progress bar           ║
╚══════════════════════════════════════════════════════════════════╝
"""

    def __init__(self):
        self.bot = TikTokBot()
        self.running = True
        
        self._load_accounts()
        
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, sig, frame):
        print("\n\n  [!] Interrupted. Stopping...")
        self.bot.stop()
        self.running = False
        sys.exit(0)

    def _load_accounts(self):
        count = self.bot.load_accounts()
        print(f"\n  [*] Loaded {count} accounts from {config['accounts_path']}")
        if count == 0:
            print("  [!] No accounts found. Use option 2.")

    def _print_header(self):
        if RICH_AVAILABLE and console:
            console.print(Panel(Text(self.BANNER.strip(), style="bold cyan"), 
                          box=box.DOUBLE_EDGE, style="bold"))
        else:
            print(self.BANNER)

    def _show_accounts(self):
        """Show all loaded accounts with detailed status"""
        accounts = self.bot.account_generator.load_accounts()
        sessions = self.bot.account_generator.load_sessions()
        devices = self.bot.account_generator.load_devices()
        
        if RICH_AVAILABLE and console:
            table = Table(title=f"📋 Accounts Loaded: {len(accounts)}", 
                         box=box.ROUNDED, title_style="bold cyan")
            table.add_column("#", style="dim", width=3)
            table.add_column("Username", style="cyan", width=20)
            table.add_column("Device ID", style="green", width=16)
            table.add_column("Session", style="yellow", width=4)
            table.add_column("Device", style="magenta", width=4)
            table.add_column("Views", justify="right", width=8)
            table.add_column("Status", width=8)
            
            for i, acc in enumerate(accounts, 1):
                uname = acc.get("username", "?")
                did = acc.get("device_id", "?")
                did_short = did[:12] + ".." if len(did) > 12 else did
                has_session = "✓" if uname in sessions else "✗"
                has_device = "✓" if did in devices else "✗"
                views = str(acc.get("total_views", 0))
                status = acc.get("status", "unknown")
                
                style = "green" if status == "active" else "red"
                table.add_row(str(i), uname, did_short, has_session, has_device, views, 
                             f"[{style}]{status}[/]")
            
            console.print(table)
        else:
            print(f"\n  📋 Accounts Loaded: {len(accounts)}")
            print(f"  {'='*70}")
            for i, acc in enumerate(accounts, 1):
                print(f"  {i:3d}. {acc.get('username','?'):20s} | "
                      f"views: {acc.get('total_views',0):5d} | "
                      f"status: {acc.get('status','?')}")
        
        total_views = sum(a.get("total_views", 0) for a in accounts)
        active = sum(1 for a in accounts if a.get("status") == "active")
        print(f"\n  [*] Total: {len(accounts)} | Active: {active} | Views: {total_views}")
        print(f"  [*] Sessions: {len(sessions)} | Devices: {len(devices)}")

    def _generate_accounts_menu(self):
        """Generate new accounts with options"""
        print("\n  [*] Account Generation")
        print("  " + "-"*50)
        
        try:
            count = int(input("  Number of accounts to generate [10]: ") or "10")
        except ValueError:
            count = 10
        
        prefix = input("  Username prefix (optional): ").strip()
        
        print(f"  [*] Generating {count} accounts...")
        accounts = self.bot.account_generator.generate_account(count, prefix)
        
        self.bot.load_accounts()
        
        print(f"\n  [✓] Generated {len(accounts)} accounts!")
        print(f"      Accounts -> {config['accounts_path']}")
        print(f"      Sessions  -> {config['sessions_path']}")
        print(f"      Devices   -> {config['devices_path']}")

    def _show_proxies(self):
        """Show detailed proxy stats"""
        proxy_stats = self.bot.proxy_manager.get_proxy_stats()
        
        print(f"\n  🌐 Proxy Status")
        print(f"  {'='*50}")
        print(f"  Total working:    {proxy_stats['total']}")
        print(f"  Avg latency:      {proxy_stats['avg_latency']:.0f}ms")
        print(f"  Median latency:   {proxy_stats['median_latency']:.0f}ms")
        print(f"  Min/Max latency:  {proxy_stats['min_latency']:.0f}ms / {proxy_stats['max_latency']:.0f}ms")
        
        types = proxy_stats.get('types', {})
        print(f"  Types: HTTP={types.get('http', 0)}, SOCKS4={types.get('socks4', 0)}, SOCKS5={types.get('socks5', 0)}")
        
        sources = proxy_stats.get('sources', {})
        if sources:
            print(f"\n  Sources:")
            for src, count in sorted(sources.items(), key=lambda x: -x[1])[:10]:
                print(f"    {src}: {count}")

    def _manage_proxies_menu(self):
        """Full proxy management submenu"""
        while True:
            print("\n  🌐 Proxy Manager")
            print("  " + "-"*50)
            print("  1.  Scrape proxies (18+ sources)")
            print("  2.  Fast check (500 threads)")
            print("  3.  Ultra-fast check (asyncio 200 concurrent)")
            print("  4.  Show proxy stats")
            print("  5.  Load proxies from file")
            print("  6.  Test top proxies on TikTok endpoints")
            print("  7.  Set rotation mode")
            print("  8.  Save proxies to file")
            print("  9.  Clear working proxies")
            print("  10. Back to main menu")
            
            choice = input("\n  Select: ").strip()
            
            if choice == "1":
                def prog(c, t, m):
                    print(f"\r  [*] {m} ({c}/{t})", end="")
                    sys.stdout.flush()
                count = self.bot.proxy_manager.scrape_proxies(prog)
                print(f"\n  [✓] Scraped {count} unique proxies")
                
            elif choice == "2":
                def prog(c, t, m):
                    print(f"\r  [*] {m}", end="")
                    sys.stdout.flush()
                timeout = int(input("  Timeout (seconds) [3]: ") or "3")
                threads = int(input("  Thread count [500]: ") or "500")
                count = self.bot.proxy_manager.check_proxies(prog, threads, timeout)
                self._show_proxies()
                
            elif choice == "3":
                print("  [*] Starting asyncio-based ultra-fast checker...")
                def prog(c, t, m):
                    print(f"\r  [*] {m}", end="")
                    sys.stdout.flush()
                count = self.bot.proxy_manager.check_proxies_asyncio(prog)
                self._show_proxies()
                
            elif choice == "4":
                self._show_proxies()
                
            elif choice == "5":
                path = input("  Path to proxy file: ").strip()
                if os.path.exists(path):
                    loaded = 0
                    with open(path) as f:
                        for line in f:
                            line = line.strip()
                            if line and ":" in line:
                                parts = line.split(":")
                                if len(parts) >= 2:
                                    proxy_type = "http"
                                    if len(parts) >= 3 and parts[2].lower() in ["socks4", "socks5", "http"]:
                                        proxy_type = parts[2].lower()
                                    self.bot.proxy_manager.proxies.append({
                                        "ip": parts[0], 
                                        "port": parts[1],
                                        "type": proxy_type,
                                        "source": "file"
                                    })
                                    loaded += 1
                    print(f"  [✓] Loaded {loaded} proxies from {path}")
                else:
                    print(f"  [!] File not found: {path}")
                    
            elif choice == "6":
                max_test = int(input("  Number of top proxies to test [10]: ") or "10")
                results = self.bot.proxy_manager.test_all_proxies_on_tiktok(max_test)
                tiktok_ok = sum(1 for r in results if r.get("all_tiktok_ok"))
                print(f"\n  [*] TikTok-compatible: {tiktok_ok}/{len(results)}")
                
            elif choice == "7":
                print("\n  Rotation modes:")
                print("    round_robin - Cycle through proxies in order")
                print("    random      - Pick random proxy each time")
                print("    fastest     - Always use lowest latency proxy")
                mode = input("  Mode (round_robin/random/fastest): ").strip().lower()
                if mode in ["round_robin", "random", "fastest"]:
                    config["proxy_rotation"] = mode
                    save_config()
                    print(f"  [✓] Rotation mode: {mode}")
                else:
                    print("  [!] Invalid mode")
                    
            elif choice == "8":
                self.bot.proxy_manager.save_working_proxies()
                print(f"  [✓] Saved {len(self.bot.proxy_manager.working_proxies)} working proxies")
                
            elif choice == "9":
                self.bot.proxy_manager.working_proxies = []
                print("  [✓] Working proxies cleared")
                    
            elif choice == "10":
                break

    def _start_view_bot(self):
        """Start video view bot"""
        print("\n  👁️  Video View Bot")
        print("  " + "-"*50)
        
        accounts = self.bot.account_generator.load_accounts()
        if not accounts:
            print("  [!] No accounts loaded. Generate some first.")
            return
        
        video_id = input("  Target video ID: ").strip()
        if not video_id:
            print("  [!] No video ID")
            return
        
        try:
            total = int(input("  Total views to send [100]: ") or "100")
        except ValueError:
            total = 100
        
        try:
            threads = int(input(f"  Threads [{config['threads']}]: ") or str(config['threads']))
        except ValueError:
            threads = config['threads']
        
        if self.bot.proxy_manager.get_working_count() == 0:
            print("\n  [!] No working proxies. Auto-scraping...")
            auto = input("  Auto-scrape and check? (Y/n): ").strip().lower()
            if auto != 'n':
                def prog(c, t, m):
                    print(f"\r  [*] {m}", end="")
                    sys.stdout.flush()
                self.bot.proxy_manager.scrape_proxies(prog)
                print()
                self.bot.proxy_manager.check_proxies(prog, 300, 3)
                print()
        
        self.bot.start_views(video_id, total, threads, is_live=False)

    def _start_live_actions_menu(self, action_type="campaign"):
        """Start live stream actions with full options"""
        print(f"\n  🎯 Live Stream - {action_type.upper()}")
        print("  " + "-"*50)
        
        accounts = self.bot.account_generator.load_accounts()
        if not accounts:
            print("  [!] No accounts loaded. Generate some first.")
            return
        
        room_id = input("  Live room ID: ").strip()
        if not room_id:
            print("  [!] No room ID provided")
            return
        
        print(f"  [*] Accounts available: {len(accounts)}")
        print(f"  [*] Working proxies: {self.bot.proxy_manager.get_working_count()}")
        
        if self.bot.proxy_manager.get_working_count() == 0:
            print("\n  [!] No working proxies.")
            if input("  Auto-scrape and check? (Y/n): ").strip().lower() != 'n':
                def prog(c, t, m):
                    print(f"\r  [*] {m}", end="")
                    sys.stdout.flush()
                self.bot.proxy_manager.scrape_proxies(prog)
                print()
                self.bot.proxy_manager.check_proxies(prog, 300, 3)
                print()
        
        if action_type == "view":
            try:
                total = int(input("  Total live entries: ") or "100")
            except ValueError:
                total = 100
            try:
                threads = int(input(f"  Threads [{config['threads']}]: ") or str(config['threads']))
            except ValueError:
                threads = config['threads']
            self.bot.start_views(room_id, total, threads, is_live=True)
            
        elif action_type == "like":
            try:
                total = int(input("  Total likes to send [200]: ") or "200")
            except ValueError:
                total = 200
            try:
                threads = int(input(f"  Threads [{config['threads']}]: ") or str(config['threads']))
            except ValueError:
                threads = min(config['threads'], total)
            self.bot.start_live_likes(room_id, total, threads)
            
        elif action_type == "share":
            try:
                total = int(input("  Total shares to send [100]: ") or "100")
            except ValueError:
                total = 100
            try:
                threads = int(input(f"  Threads [{config['threads']}]: ") or str(config['threads']))
            except ValueError:
                threads = min(config['threads'], total)
            self.bot.start_live_shares(room_id, total, threads)
            
        elif action_type == "campaign":
            print("\n  🎯 Full Live Campaign")
            print("  Natural proportions: views with occasional likes + shares")
            print("  " + "-"*40)
            
            try:
                views = int(input("  Total views [100]: ") or "100")
            except ValueError:
                views = 100
            
            print("  Like/share frequency (0.0 to 1.0):")
            print("    0.3 = 30% chance per view to also like")
            try:
                like_prob = float(input("  Like probability [0.3]: ") or "0.3")
            except ValueError:
                like_prob = 0.3
            try:
                share_prob = float(input("  Share probability [0.1]: ") or "0.1")
            except ValueError:
                share_prob = 0.1
            try:
                threads = int(input(f"  Threads [{config['threads']}]: ") or str(config['threads']))
            except ValueError:
                threads = config['threads']
            
            self.bot.start_live_campaign(room_id, views, like_prob, share_prob, threads)

    def _signerpy_diagnostic(self):
        """Run full SignerPy diagnostic"""
        print("\n  🔬 SignerPy Full Diagnostic")
        print("  " + "-"*50)
        
        try:
            import SignerPy
            ver = getattr(SignerPy, '__version__', 'unknown')
            print(f"  [✓] SignerPy version: {ver}")
            
            tests = []
            
            try:
                from SignerPy import sign
                result = sign(params="test=1", data="", cookies="")
                tests.append(("sign()", True, "OK"))
            except Exception as e:
                tests.append(("sign()", False, str(e)[:30]))
            
            try:
                from SignerPy import trace_id
                tid = trace_id()
                tests.append(("trace_id()", True, tid[:16]))
            except Exception as e:
                tests.append(("trace_id()", False, str(e)[:30]))
            
            try:
                from SignerPy import ttencrypt
                enc = ttencrypt.Enc().encrypt("test_data")
                tests.append(("ttencrypt.Enc()", True, str(enc[:12])))
            except Exception as e:
                tests.append(("ttencrypt.Enc()", False, str(e)[:30]))
            
            try:
                from SignerPy import xtoken
                tok = xtoken(url="https://api.tiktokv.com/feed/", device_id="123456789")
                tests.append(("xtoken()", True, str(tok)[:20] if tok else "None"))
            except Exception as e:
                tests.append(("xtoken()", False, str(e)[:30]))
            
            try:
                from SignerPy import edata
                enc = edata.encrypt("hello_tiktok")
                dec = edata.decrypt(enc)
                tests.append(("edata enc/dec", True, dec))
            except Exception as e:
                tests.append(("edata enc/dec", False, str(e)[:30]))
            
            try:
                from SignerPy import hosts
                hlist = hosts.host()
                tests.append(("hosts.host()", True, f"{len(hlist)} hosts"))
            except Exception as e:
                tests.append(("hosts.host()", False, str(e)[:30]))
            
            if RICH_AVAILABLE and console:
                table = Table(title="SignerPy Module Tests", box=box.ROUNDED)
                table.add_column("Module", style="cyan")
                table.add_column("Status", style="bold")
                table.add_column("Result", style="dim")
                
                for test in tests:
                    name = test[0]
                    passed = test[1]
                    detail = test[2] if len(test) > 2 else ""
                    status = "✓" if passed else "✗"
                    s_style = "green" if passed else "red"
                    table.add_row(name, f"[{s_style}]{status}[/]", detail)
                
                console.print(table)
            else:
                print(f"\n  {'Module':25s} {'Status':8s} Result")
                print(f"  {'-'*60}")
                for test in tests:
                    status = "✓" if test[1] else "✗"
                    detail = test[2] if len(test) > 2 else ""
                    print(f"  {test[0]:25s} {status:8s} {detail}")
            
            print("\n  [*] Full request signing demo:")
            from signer import TikTokSigner
            signer = TikTokSigner()
            headers = signer.sign_request(
                url="https://api.tiktokv.com/aweme/v1/feed/?aid=1233",
                data="", cookies=""
            )
            print(f"  [✓] Generated {len(headers)} signature headers:")
            for k, v in headers.items():
                if k.lower().startswith("x-"):
                    val = str(v)
                    if len(val) > 45:
                        val = val[:42] + "..."
                    print(f"      {k:25s}: {val}")
            
            print("\n  [*] Live stream like header test:")
            like_headers = signer.sign_request(
                url="https://api.tiktokv.com/aweme/v1/live/like/?room_id=123&aid=1233",
                data='{"room_id":"123","like_count":5}', 
                cookies="sessionid=test"
            )
            for k, v in like_headers.items():
                if k.lower().startswith("x-"):
                    val = str(v)
                    if len(val) > 45:
                        val = val[:42] + "..."
                    print(f"      {k:25s}: {val}")
            
        except ImportError as e:
            print(f"  [✗] SignerPy not installed: {e}")
            print("  [*] Install: pip install SignerPy>=0.11.0")
            print("\n  [*] Using fallback signature generation")
            
            from signer import TikTokSigner
            signer = TikTokSigner()
            headers = signer.sign_request(
                url="https://api.tiktokv.com/aweme/v1/feed/?aid=1233"
            )
            print(f"  [i] Fallback generated {len(headers)} headers")

    def _show_dashboard(self):
        """Show standalone live dashboard"""
        print("\n  [*] Starting live dashboard (Ctrl+C to stop)...\n")
        dash = Dashboard(refresh_interval=0.5)
        
        accounts = self.bot.account_generator.load_accounts()
        active_count = len([a for a in accounts if a.get("status") == "active"])
        total_views_delivered = sum(a.get("total_views", 0) for a in accounts)
        
        dash.stats.update(
            accounts_loaded=len(accounts),
            accounts_active=active_count,
            accounts_total_views=total_views_delivered,
            proxies_working=self.bot.proxy_manager.get_working_count(),
            proxies_total=len(self.bot.proxy_manager.proxies),
            views_completed=self.bot.stats["views_completed"],
            views_failed=self.bot.stats["views_failed"],
            likes_completed=self.bot.stats["likes_completed"],
            likes_failed=self.bot.stats["likes_failed"],
            shares_completed=self.bot.stats["shares_completed"],
            shares_failed=self.bot.stats["shares_failed"],
            requests_sent=self.bot.stats["requests_sent"],
            requests_success=self.bot.stats["requests_success"],
            requests_failed=self.bot.stats["requests_failed"],
            status="Dashboard Only",
        )
        dash.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            dash.stop()
            print("\n  [✓] Dashboard stopped")

    def _config_menu(self):
        """Full configuration submenu"""
        while True:
            print("\n  ⚙️  Configuration")
            print("  " + "-"*50)
            print(f"  1.  Accounts path:  {config['accounts_path']}")
            print(f"  2.  Sessions path:  {config['sessions_path']}")
            print(f"  3.  Devices path:   {config['devices_path']}")
            print(f"  4.  Threads:        {config['threads']}")
            print(f"  5.  View delay:     {config['view_delay_min']}-{config['view_delay_max']}s")
            print(f"  6.  Views/account:  {config['views_per_account']}")
            print(f"  7.  X-Gorgon ver:   {config['x_gorgon_version']}")
            print(f"  8.  App ID:         {config['app_id']}")
            print(f"  9.  App version:    {config['app_version']}")
            print(f"  10. Proxy check timeout: {config['proxy_check_timeout']}s")
            print(f"  11. Proxy check threads:  {config['proxy_check_threads']}")
            print(f"  12. Proxy rotation:       {config['proxy_rotation']}")
            print(f"  13. Auto-scrape proxies:  {config['auto_scrape_proxies']}")
            print(f"  14. Proxy test URL:       {config.get('proxy_test_url', 'http://httpbin.org/ip')}")
            print(f"  15. Save & Back")
            
            choice = input("\n  Select: ").strip()
            
            if choice == "1":
                p = input(f"  New path [{config['accounts_path']}]: ").strip()
                if p: config['accounts_path'] = p; Path(p).mkdir(parents=True, exist_ok=True)
            elif choice == "2":
                p = input(f"  New path [{config['sessions_path']}]: ").strip()
                if p: config['sessions_path'] = p; Path(p).mkdir(parents=True, exist_ok=True)
            elif choice == "3":
                p = input(f"  New path [{config['devices_path']}]: ").strip()
                if p: config['devices_path'] = p; Path(p).mkdir(parents=True, exist_ok=True)
            elif choice == "4":
                v = input(f"  Threads [{config['threads']}]: ").strip()
                if v: config['threads'] = int(v)
            elif choice == "5":
                v = input(f"  Delay min [{config['view_delay_min']}]: ").strip()
                if v: config['view_delay_min'] = float(v)
                v = input(f"  Delay max [{config['view_delay_max']}]: ").strip()
                if v: config['view_delay_max'] = float(v)
            elif choice == "6":
                v = input(f"  Views/account [{config['views_per_account']}]: ").strip()
                if v: config['views_per_account'] = int(v)
            elif choice == "7":
                v = input("  Version (v1/8404, v2/8402, v3/4404): ").strip()
                if v in ["v1","v2","v3","8404","8402","4404"]: config['x_gorgon_version'] = v
            elif choice == "8":
                v = input(f"  App ID [{config['app_id']}]: ").strip()
                if v: config['app_id'] = int(v)
            elif choice == "9":
                v = input(f"  App version [{config['app_version']}]: ").strip()
                if v: config['app_version'] = v
            elif choice == "10":
                v = input(f"  Timeout [{config['proxy_check_timeout']}]: ").strip()
                if v: config['proxy_check_timeout'] = int(v)
            elif choice == "11":
                v = input(f"  Threads [{config['proxy_check_threads']}]: ").strip()
                if v: config['proxy_check_threads'] = int(v)
            elif choice == "12":
                v = input("  Mode (round_robin/random/fastest): ").strip().lower()
                if v in ["round_robin","random","fastest"]: config['proxy_rotation'] = v
            elif choice == "13":
                v = input("  Auto-scrape? (true/false): ").strip().lower()
                if v in ["true","false"]: config['auto_scrape_proxies'] = v == "true"
            elif choice == "14":
                v = input(f"  URL [{config.get('proxy_test_url', 'http://httpbin.org/ip')}]: ").strip()
                if v: config['proxy_test_url'] = v
            elif choice == "15":
                save_config()
                print("  [✓] Configuration saved")
                break

    def _tools_menu(self):
        """Tools and utilities submenu"""
        while True:
            proxy_count = self.bot.proxy_manager.get_working_count()
            
            print("\n  🛠️  Tools & Utilities")
            print("  " + "-"*50)
            print(f"  1.  Test single proxy on TikTok")
            print(f"  2.  Test all working proxies on TikTok ({proxy_count})")
            print(f"  3.  Show accounts summary")
            print(f"  4.  Export accounts to CSV")
            print(f"  5.  Clear all stats")
            print(f"  6.  Back to main menu")
            
            choice = input("\n  Select: ").strip()
            
            if choice == "1":
                ip = input("  Proxy IP: ").strip()
                port = input("  Port: ").strip()
                ptype = input("  Type (http/socks4/socks5) [http]: ").strip() or "http"
                
                proxy = {"ip": ip, "port": port, "type": ptype}
                print(f"\n  [*] Testing {ptype}://{ip}:{port} on TikTok endpoints...\n")
                results = self.bot.proxy_manager.test_proxy_on_tiktok(proxy)
                
                for endpoint, result in results.items():
                    ep_name = endpoint.split("/")[3] if len(endpoint.split("/")) > 3 else endpoint[:35]
                    if result.get("status") == "ok":
                        print(f"  [✓] {ep_name:30s} {result['latency_ms']:.0f}ms (HTTP {result['http_code']})")
                    else:
                        print(f"  [✗] {ep_name:30s} {result.get('error', 'failed')}")
                
            elif choice == "2":
                max_test = int(input("  How many proxies to test [20]: ") or "20")
                results = self.bot.proxy_manager.test_all_proxies_on_tiktok(max_test)
                tiktok_ok = sum(1 for r in results if r.get("all_tiktok_ok"))
                print(f"\n  [*] TikTok-compatible proxies: {tiktok_ok}/{len(results)}")
                
            elif choice == "3":
                self._show_accounts()
                
            elif choice == "4":
                accounts = self.bot.account_generator.load_accounts()
                csv_path = input("  Output CSV path [accounts_export.csv]: ").strip() or "accounts_export.csv"
                with open(csv_path, 'w') as f:
                    f.write("username,email,device_id,total_views,status,created_at\n")
                    for a in accounts:
                        f.write(f"{a.get('username','')},{a.get('email','')},{a.get('device_id','')},"
                               f"{a.get('total_views',0)},{a.get('status','')},{a.get('created_at','')}\n")
                print(f"  [✓] Exported {len(accounts)} accounts to {csv_path}")
                
            elif choice == "5":
                self.bot.stats = {k: 0 for k in self.bot.stats}
                print("  [✓] All stats cleared")
                
            elif choice == "6":
                break

    def run(self):
        """Main menu loop"""
        while self.running:
            self._print_header()
            
            accounts = self.bot.account_generator.load_accounts()
            proxy_count = self.bot.proxy_manager.get_working_count()
            total_views_delivered = sum(a.get("total_views", 0) for a in accounts)
            
            if RICH_AVAILABLE and console:
                status = Table.grid(padding=1)
                status.add_row(
                    Panel(f"📋 Accounts: {len(accounts)}", style="cyan"),
                    Panel(f"🌐 Proxies: {proxy_count}", style="green"),
                    Panel(f"👁️  Views: {self.bot.stats['views_completed']}", style="yellow"),
                    Panel(f"❤️  Likes: {self.bot.stats['likes_completed']}", style="red"),
                    Panel(f"🔗  Shares: {self.bot.stats['shares_completed']}", style="blue"),
                    Panel(f"📊 Total: {total_views_delivered}", style="magenta"),
                )
                console.print(status)
                console.print()
            else:
                print(f"\n  📋 Accounts: {len(accounts)}  |  🌐 Proxies: {proxy_count}  |  "
                      f"👁️  Views: {self.bot.stats['views_completed']}  |  "
                      f"❤️  Likes: {self.bot.stats['likes_completed']}  |  "
                      f"🔗  Shares: {self.bot.stats['shares_completed']}  |  "
                      f"📊 Total Views: {total_views_delivered}\n")
            
            print("  ┌─── MAIN MENU ────────────────────────────────────┐")
            print("  │  📋  1. Show loaded accounts                     │")
            print("  │  🆕  2. Generate accounts                        │")
            print("  │  🌐  3. Proxy manager (18 sources)               │")
            print("  │  ─────────────────────────────────────────────── │")
            print("  │  👁️   4. Start video view bot                    │")
            print("  │  🎥  5. Start live stream views                  │")
            print("  │  ❤️   6. Send live stream LIKES                   │")
            print("  │  🔗  7. Send live stream SHARES                  │")
            print("  │  🎯  8. FULL LIVE CAMPAIGN (views+likes+shares)  │")
            print("  │  ─────────────────────────────────────────────── │")
            print("  │  🛠️   9. Tools & utilities                       │")
            print("  │  ⚙️  10. Configuration                           │")
            print("  │  🔬 11. SignerPy full diagnostic                 │")
            print("  │  📊 12. Show real-time dashboard                 │")
            print("  │  ─────────────────────────────────────────────── │")
            print("  │  🚪 13. Exit                                     │")
            print("  └──────────────────────────────────────────────────┘")
            
            choice = input("\n  Select [1-13]: ").strip()
            
            if choice == "1":
                self._show_accounts()
                if self.running: input("\n  Press Enter...")
                
            elif choice == "2":
                self._generate_accounts_menu()
                if self.running: input("\n  Press Enter...")
                
            elif choice == "3":
                self._manage_proxies_menu()
                
            elif choice == "4":
                self._start_view_bot()
                
            elif choice == "5":
                self._start_live_actions_menu("view")
                
            elif choice == "6":
                self._start_live_actions_menu("like")
                
            elif choice == "7":
                self._start_live_actions_menu("share")
                
            elif choice == "8":
                self._start_live_actions_menu("campaign")
                
            elif choice == "9":
                self._tools_menu()
                
            elif choice == "10":
                self._config_menu()
                
            elif choice == "11":
                self._signerpy_diagnostic()
                if self.running: input("\n  Press Enter...")
                
            elif choice == "12":
                self._show_dashboard()
                
            elif choice == "13":
                print("\n  [✓] Exiting. Goodbye!")
                self.running = False
                
            else:
                print("\n  [!] Invalid option")
                if self.running: input("\n  Press Enter...")


def main():
    """Entry point"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("  [*] Initializing TikTok Bot v3.0...")
    
    try:
        import SignerPy
        ver = getattr(SignerPy, '__version__', 'unknown')
        print(f"  [✓] SignerPy v{ver} - full signature support\n")
    except ImportError:
        print("  [!] SignerPy not installed - using fallback signatures")
        print("  [*] pip install SignerPy>=0.11.0\n")
    
    for d in [config['accounts_path'], config['sessions_path'], config['devices_path']]:
        Path(d).mkdir(parents=True, exist_ok=True)
    
    menu = Menu()
    
    try:
        menu.run()
    except KeyboardInterrupt:
        print("\n\n  [!] Interrupted by user")
    except Exception as e:
        print(f"\n  [!] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("  [✓] Bot stopped. Goodbye!\n")


if __name__ == "__main__":
    main()
