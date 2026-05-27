#!/usr/bin/env python3
"""
TikTok Bot - Main Entry Point
Live dashboard menu interface for TikTok view bot operations.
Features: Account management, proxy management, view simulation,
          full SignerPy integration, live dashboard
Author: HackerAI PenTest Framework
"""
import os
import sys
import json
import time
import signal
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config, load_config, save_config, set_path
from bot import TikTokBot
from dashboard import Dashboard
from proxy_manager import ProxyManager

# Try to import rich for better UI
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
╔══════════════════════════════════════════════════════════════╗
║                    TikTok Bot v3.0                          ║
║          Full SignerPy Integration - Live Dashboard         ║
║              Author: HackerAI PenTest Framework             ║
╠══════════════════════════════════════════════════════════════╣
║  Features:                                                  ║
║  • SignerPy: x-gorgon(v1/v2/v3), x-argus, x-ladon          ║
║  • x-khronos, x-ss-stub, x-ss-req-ticket, x-token          ║
║  • SM3 hashing, Protobuf, Simon cipher, ChaCha20            ║
║  • TTEncrypt, edata encrypt/decrypt, trace_id               ║
║  • Live stream view simulation (TikTok API direct reqs)     ║
║  • Proxy scraping (12+ sources: HTTP/SOCKS4/SOCKS5)         ║
║  • Multi-threaded proxy checker with latency measurement    ║
║  • Round-robin & random proxy rotation                      ║
║  • Random UA, device-ID, IP spoofing per request            ║
║  • Auto captcha solve for Zefoy                             ║
║  • Live real-time stats dashboard                           ║
╚══════════════════════════════════════════════════════════════╝
"""

    def __init__(self):
        self.bot = TikTokBot()
        self.running = True
        
        # Load accounts on init
        self._load_accounts()
        
        # Signal handler
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n  [!] Interrupted. Stopping...")
        self.bot.stop()
        self.running = False
        sys.exit(0)

    def _load_accounts(self):
        """Load accounts and show count"""
        count = self.bot.load_accounts()
        print(f"\n  [*] Loaded {count} accounts from {config['accounts_path']}")
        if count == 0:
            print("  [!] No accounts found. Use option 2 to generate some.")

    def _print_header(self):
        """Print menu header"""
        if RICH_AVAILABLE and console:
            console.print(Panel(Text(self.BANNER.strip(), style="bold cyan"), 
                          box=box.DOUBLE_EDGE, style="bold"))
        else:
            print(self.BANNER)

    def _show_accounts(self):
        """Show loaded accounts"""
        accounts = self.bot.account_generator.load_accounts()
        sessions = self.bot.account_generator.load_sessions()
        devices = self.bot.account_generator.load_devices()
        
        if RICH_AVAILABLE and console:
            table = Table(title=f"📋 Accounts Loaded: {len(accounts)}", 
                         box=box.ROUNDED, title_style="bold cyan")
            table.add_column("#", style="dim")
            table.add_column("Username", style="cyan")
            table.add_column("Device ID", style="green")
            table.add_column("Session?", style="yellow")
            table.add_column("Device?", style="magenta")
            table.add_column("Views", justify="right")
            
            for i, acc in enumerate(accounts, 1):
                uname = acc.get("username", "?")
                did = acc.get("device_id", "?")
                did_short = did[:12] + "..." if len(did) > 12 else did
                has_session = "✓" if uname in sessions else "✗"
                has_device = "✓" if did in devices else "✗"
                views = str(acc.get("total_views", 0))
                
                table.add_row(str(i), uname, did_short, has_session, has_device, views)
            
            console.print(table)
        else:
            print(f"\n  📋 Accounts Loaded: {len(accounts)}")
            print(f"  {'='*60}")
            for i, acc in enumerate(accounts, 1):
                print(f"  {i:3d}. {acc.get('username','?'):20s} | views: {acc.get('total_views',0)}")
        
        # Summary stats
        total_views = sum(a.get("total_views", 0) for a in accounts)
        print(f"\n  [*] Total accounts: {len(accounts)}")
        print(f"  [*] Total sessions: {len(sessions)}")
        print(f"  [*] Total devices:  {len(devices)}")
        print(f"  [*] Total views delivered: {total_views}")

    def _generate_accounts_menu(self):
        """Generate new accounts"""
        print("\n  [*] Account Generation")
        print("  " + "-"*40)
        
        try:
            count = int(input("  Number of accounts to generate: ") or "10")
        except ValueError:
            print("  [!] Invalid input, using 10")
            count = 10
        
        prefix = input("  Username prefix (optional): ").strip()
        
        accounts = self.bot.account_generator.generate_account(count, prefix)
        print(f"\n  [✓] Generated {len(accounts)} accounts!")
        
        # Reload into bot
        self.bot.load_accounts()

    def _show_proxies(self):
        """Show proxy status"""
        proxy_stats = self.bot.proxy_manager.get_proxy_stats()
        
        print(f"\n  🌐 Proxy Status")
        print(f"  {'='*40}")
        print(f"  Total working:    {proxy_stats['total']}")
        print(f"  Avg latency:      {proxy_stats['avg_latency']:.0f}ms")
        print(f"  Min/Max latency:  {proxy_stats['min_latency']:.0f}ms / {proxy_stats['max_latency']:.0f}ms")
        
        types = proxy_stats.get('types', {})
        print(f"  Types: HTTP={types.get('http', 0)}, SOCKS4={types.get('socks4', 0)}, SOCKS5={types.get('socks5', 0)}")
        
        # Show sources breakdown
        sources = proxy_stats.get('sources', {})
        if sources:
            print(f"\n  Sources:")
            for src, count in sorted(sources.items(), key=lambda x: -x[1]):
                print(f"    {src}: {count}")

    def _manage_proxies_menu(self):
        """Proxy management submenu"""
        while True:
            print("\n  🌐 Proxy Manager")
            print("  " + "-"*40)
            print("  1. Scrape proxies from all sources")
            print("  2. Check working proxies")
            print("  3. Show proxy stats")
            print("  4. Load proxies from file")
            print("  5. Set rotation mode")
            print("  6. Back to main menu")
            
            choice = input("\n  Select: ").strip()
            
            if choice == "1":
                def prog(c, t, m):
                    print(f"\r  [*] {m} ({c}/{t})", end="")
                    sys.stdout.flush()
                count = self.bot.proxy_manager.scrape_proxies(prog)
                print(f"\n  [✓] Scraped {count} proxies")
                
            elif choice == "2":
                def prog(c, t, m):
                    print(f"\r  [*] {m}", end="")
                    sys.stdout.flush()
                count = self.bot.proxy_manager.check_proxies(prog)
                print(f"\n  [✓] Found {count} working proxies")
                self._show_proxies()
                
            elif choice == "3":
                self._show_proxies()
                
            elif choice == "4":
                path = input("  Path to proxy file: ").strip()
                if os.path.exists(path):
                    with open(path) as f:
                        for line in f:
                            line = line.strip()
                            if line and ":" in line:
                                parts = line.split(":")
                                if len(parts) >= 2:
                                    proxy_type = "http"
                                    if len(parts) >= 3 and parts[2].lower() in ["socks4", "socks5", "http", "https"]:
                                        proxy_type = parts[2].lower()
                                    self.bot.proxy_manager.proxies.append({
                                        "ip": parts[0], 
                                        "port": parts[1],
                                        "type": proxy_type,
                                        "source": "file"
                                    })
                    print(f"  [✓] Loaded proxies from {path}")
                else:
                    print(f"  [!] File not found: {path}")
                    
            elif choice == "5":
                mode = input("  Rotation mode (round_robin / random): ").strip().lower()
                if mode in ["round_robin", "random"]:
                    config["proxy_rotation"] = mode
                    save_config()
                    print(f"  [✓] Rotation mode set to: {mode}")
                else:
                    print("  [!] Invalid mode. Use 'round_robin' or 'random'")
                    
            elif choice == "6":
                break
            else:
                print("  [!] Invalid option")

    def _config_menu(self):
        """Configuration submenu"""
        while True:
            print("\n  ⚙️  Configuration")
            print("  " + "-"*40)
            print(f"  1. Accounts path:  {config['accounts_path']}")
            print(f"  2. Sessions path:  {config['sessions_path']}")
            print(f"  3. Devices path:   {config['devices_path']}")
            print(f"  4. Threads:        {config['threads']}")
            print(f"  5. View delay:     {config['view_delay_min']}-{config['view_delay_max']}s")
            print(f"  6. Views/account:  {config['views_per_account']}")
            print(f"  7. X-Gorgon ver:   {config['x_gorgon_version']}")
            print(f"  8. App ID:         {config['app_id']}")
            print(f"  9. App version:    {config['app_version']}")
            print(f"  10. Proxy check timeout: {config['proxy_check_timeout']}s")
            print(f"  11. Proxy check threads:  {config['proxy_check_threads']}")
            print(f"  12. Save & Back")
            
            choice = input("\n  Select: ").strip()
            
            if choice == "1":
                p = input(f"  New accounts path [{config['accounts_path']}]: ").strip()
                if p: 
                    config['accounts_path'] = p
                    Path(p).mkdir(parents=True, exist_ok=True)
            elif choice == "2":
                p = input(f"  New sessions path [{config['sessions_path']}]: ").strip()
                if p: 
                    config['sessions_path'] = p
                    Path(p).mkdir(parents=True, exist_ok=True)
            elif choice == "3":
                p = input(f"  New devices path [{config['devices_path']}]: ").strip()
                if p: 
                    config['devices_path'] = p
                    Path(p).mkdir(parents=True, exist_ok=True)
            elif choice == "4":
                v = input(f"  Threads [{config['threads']}]: ").strip()
                if v: config['threads'] = int(v)
            elif choice == "5":
                v = input(f"  Delay min [{config['view_delay_min']}]: ").strip()
                if v: config['view_delay_min'] = float(v)
                v = input(f"  Delay max [{config['view_delay_max']}]: ").strip()
                if v: config['view_delay_max'] = float(v)
            elif choice == "6":
                v = input(f"  Views per account [{config['views_per_account']}]: ").strip()
                if v: config['views_per_account'] = int(v)
            elif choice == "7":
                v = input("  X-Gorgon version (v1/8404, v2/8402, v3/4404): ").strip()
                if v in ["v1", "v2", "v3", "8404", "8402", "4404"]: 
                    config['x_gorgon_version'] = v
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
                save_config()
                print("  [✓] Configuration saved")
                break
            else:
                print("  [!] Invalid option")

    def _start_view_bot(self):
        """Start the view bot"""
        print("\n  👁️  View Bot Launcher")
        print("  " + "-"*40)
        
        # Check if we have accounts
        accounts = self.bot.account_generator.load_accounts()
        if not accounts:
            print("  [!] No accounts loaded. Generate some first (option 2).")
            return
        
        video_id = input("  Target video/live ID: ").strip()
        if not video_id:
            print("  [!] No video ID provided")
            return
        
        try:
            total = int(input("  Total views to send: ") or "100")
        except ValueError:
            print("  [!] Invalid number, using 100")
            total = 100
        
        try:
            threads = int(input(f"  Threads [{config['threads']}]: ") or str(config['threads']))
        except ValueError:
            threads = config['threads']
        
        is_live = input("  Is this a live stream? (y/N): ").strip().lower() == 'y'
        
        # Ensure we have proxies
        if self.bot.proxy_manager.get_working_count() == 0:
            print("\n  [!] No working proxies. Auto-scraping and checking...")
            auto = input("  Scrape proxies now? (Y/n): ").strip().lower()
            if auto != 'n':
                def prog(c, t, m):
                    print(f"\r  [*] {m}", end="")
                    sys.stdout.flush()
                self.bot.proxy_manager.scrape_proxies(prog)
                print()
                self.bot.proxy_manager.check_proxies(prog)
                print()
        
        # Start
        self.bot.start_views(video_id, total, threads, is_live)

    def _signerpy_diagnostic(self):
        """Run SignerPy diagnostic test"""
        print("\n  🔬 SignerPy Diagnostic")
        print("  " + "-"*40)
        
        try:
            import SignerPy
            print(f"  [✓] SignerPy version: {getattr(SignerPy, '__version__', 'unknown')}")
            
            # Test individual modules
            tests = []
            
            # sign module
            try:
                from SignerPy import sign
                result = sign(params="test=1", data="", cookies="")
                tests.append(("sign()", True))
            except Exception as e:
                tests.append(("sign()", False, str(e)))
            
            # trace_id
            try:
                from SignerPy import trace_id
                tid = trace_id()
                tests.append(("trace_id()", True, tid[:16]))
            except Exception as e:
                tests.append(("trace_id()", False, str(e)))
            
            # ttencrypt
            try:
                from SignerPy import ttencrypt
                enc = ttencrypt.Enc().encrypt("test_data")
                tests.append(("ttencrypt.Enc().encrypt()", True, enc[:16]))
            except Exception as e:
                tests.append(("ttencrypt.Enc().encrypt()", False, str(e)))
            
            # xtoken
            try:
                from SignerPy import xtoken
                tok = xtoken(url="https://api.tiktokv.com/feed/", device_id="123456789")
                tests.append(("xtoken()", True, str(tok)[:20] if tok else "None"))
            except Exception as e:
                tests.append(("xtoken()", False, str(e)))
            
            # edata encrypt/decrypt
            try:
                from SignerPy import edata
                enc = edata.encrypt("hello_tiktok")
                dec = edata.decrypt(enc)
                tests.append(("edata encrypt/decrypt", True, dec))
            except Exception as e:
                tests.append(("edata encrypt/decrypt", False, str(e)))
            
            # hosts
            try:
                from SignerPy import hosts
                hlist = hosts.host()
                tests.append(("hosts.host()", True, f"{len(hlist)} hosts"))
            except Exception as e:
                tests.append(("hosts.host()", False, str(e)))
            
            # encryption
            try:
                from SignerPy import encryption
                tests.append(("encryption module", True))
            except Exception as e:
                tests.append(("encryption module", False, str(e)))
            
            # Display results
            if RICH_AVAILABLE and console:
                table = Table(title="SignerPy Module Tests", box=box.ROUNDED)
                table.add_column("Module", style="cyan")
                table.add_column("Status", style="bold")
                table.add_column("Details", style="dim")
                
                for test in tests:
                    name = test[0]
                    status = "✓" if test[1] else "✗"
                    status_style = "green" if test[1] else "red"
                    detail = test[2] if len(test) > 2 else ""
                    table.add_row(name, f"[{status_style}]{status}[/]", detail)
                
                console.print(table)
            else:
                print(f"\n  {'Module':30s} {'Status':10s} Details")
                print(f"  {'-'*70}")
                for test in tests:
                    name = test[0]
                    status = "✓" if test[1] else "✗"
                    detail = test[2] if len(test) > 2 else ""
                    print(f"  {name:30s} {status:10s} {detail}")
            
            # Full signing test
            print("\n  [*] Full request signing test:")
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
                    if len(val) > 50:
                        val = val[:47] + "..."
                    print(f"      {k:25s}: {val}")
            
        except ImportError as e:
            print(f"  [✗] SignerPy not installed: {e}")
            print("  [*] Install: pip install SignerPy>=0.11.0")
            print("\n  [*] Falling back to built-in signature generation")
            
            # Test fallback
            from signer import TikTokSigner
            signer = TikTokSigner()
            headers = signer.sign_request(
                url="https://api.tiktokv.com/aweme/v1/feed/?aid=1233",
                data="", cookies=""
            )
            print(f"\n  [i] Fallback generated {len(headers)} headers:")
            for k, v in headers.items():
                if k.lower().startswith("x-"):
                    val = str(v)
                    if len(val) > 50:
                        val = val[:47] + "..."
                    print(f"      {k:25s}: {val}")

    def _show_dashboard(self):
        """Show live dashboard in standalone mode"""
        print("\n  [*] Starting live dashboard (Ctrl+C to stop)...\n")
        dash = Dashboard(refresh_interval=0.5)
        
        accounts = self.bot.account_generator.load_accounts()
        active_count = len([a for a in accounts if a.get("status") == "active"])
        total_views = sum(a.get("total_views", 0) for a in accounts)
        
        dash.stats.update(
            accounts_loaded=len(accounts),
            accounts_active=active_count,
            accounts_total_views=total_views,
            proxies_working=self.bot.proxy_manager.get_working_count(),
            proxies_total=len(self.bot.proxy_manager.proxies),
            views_completed=self.bot.stats["views_completed"],
            views_failed=self.bot.stats["views_failed"],
            requests_sent=self.bot.stats["requests_sent"],
            requests_success=self.bot.stats["requests_success"],
            requests_failed=self.bot.stats["requests_failed"],
            status="Dashboard Only",
        )
        dash.start()
        
        try:
            while True:
                time.sleep(1)
                # Keep updating stats
                dash.stats.update(
                    requests_sent=self.bot.stats["requests_sent"],
                    requests_success=self.bot.stats["requests_success"],
                    requests_failed=self.bot.stats["requests_failed"],
                )
        except KeyboardInterrupt:
            pass
        finally:
            dash.stop()
            print("\n  [✓] Dashboard stopped")

    def run(self):
        """Main menu loop"""
        while self.running:
            self._print_header()
            
            accounts = self.bot.account_generator.load_accounts()
            proxy_count = self.bot.proxy_manager.get_working_count()
            total_views = sum(a.get("total_views", 0) for a in accounts)
            
            # Status summary
            if RICH_AVAILABLE and console:
                status = Table.grid(padding=1)
                status.add_row(
                    Panel(f"📋 Accounts: {len(accounts)}", style="cyan"),
                    Panel(f"🌐 Proxies: {proxy_count}", style="green"),
                    Panel(f"👁️  Views: {self.bot.stats['views_completed']}", style="yellow"),
                    Panel(f"📊 Total: {total_views}", style="magenta"),
                )
                console.print(status)
                console.print()
            else:
                print(f"\n  📋 Accounts: {len(accounts)}  |  🌐 Proxies: {proxy_count}  |  "
                      f"👁️  Views: {self.bot.stats['views_completed']}  |  "
                      f"📊 Total Delivered: {total_views}\n")
            
            # Menu options
            print("  ┌─── MAIN MENU ──────────────────────────────┐")
            print("  │  1. Show loaded accounts                    │")
            print("  │  2. Generate accounts                       │")
            print("  │  3. Proxy manager                           │")
            print("  │  4. Start view bot                         │")
            print("  │  5. Start live stream views                │")
            print("  │  6. Configuration                          │")
            print("  │  7. Full SignerPy diagnostic               │")
            print("  │  8. Show real-time dashboard               │")
            print("  │  9. Exit                                   │")
            print("  └─────────────────────────────────────────────┘")
            
            choice = input("\n  Select: ").strip()
            
            if choice == "1":
                self._show_accounts()
                if self.running:
                    input("\n  Press Enter to continue...")
            elif choice == "2":
                self._generate_accounts_menu()
                if self.running:
                    input("\n  Press Enter to continue...")
            elif choice == "3":
                self._manage_proxies_menu()
            elif choice == "4":
                self._start_view_bot()
            elif choice == "5":
                self._start_view_bot()
            elif choice == "6":
                self._config_menu()
            elif choice == "7":
                self._signerpy_diagnostic()
                if self.running:
                    input("\n  Press Enter to continue...")
            elif choice == "8":
                self._show_dashboard()
            elif choice == "9":
                print("\n  [✓] Exiting...")
                self.running = False
            else:
                print("\n  [!] Invalid option")
                if self.running:
                    input("\n  Press Enter to continue...")


def main():
    """Entry point"""
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("  [*] Initializing TikTok Bot...")
    
    # Check SignerPy availability
    try:
        import SignerPy
        ver = getattr(SignerPy, '__version__', 'unknown')
        print(f"  [✓] SignerPy v{ver} detected - full signature support enabled\n")
    except ImportError:
        print("  [!] SignerPy not installed - using fallback signature methods")
        print("  [*] For full features: pip install SignerPy>=0.11.0\n")
    
    # Create default directories
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
        print("  [✓] Goodbye!\n")


if __name__ == "__main__":
    main()
