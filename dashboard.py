#!/usr/bin/env python3
"""
Live Dashboard - Real-time stats display
Shows accounts loaded, views/likes/shares progress, proxy stats, live campaign status
Author: HackerAI PenTest Framework
"""
import os
import sys
import time
import threading
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

try:
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.console import Console
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from config import config


class Dashboard:
    """
    Live terminal dashboard for TikTok bot operations.
    Real-time: accounts, views, likes, shares, proxies, requests, campaign progress
    """
    
    def __init__(self, refresh_interval: float = 0.8):
        self.console = Console() if RICH_AVAILABLE else None
        self.refresh_interval = refresh_interval
        self._running = False
        self._thread = None
        
        self.stats = {
            "accounts_loaded": 0,
            "accounts_active": 0,
            "accounts_total_views": 0,
            "views_completed": 0,
            "views_failed": 0,
            "views_in_progress": 0,
            "likes_completed": 0,
            "likes_failed": 0,
            "shares_completed": 0,
            "shares_failed": 0,
            "views_target_video": "",
            "views_per_video": config.get("views_per_video", 10),
            "views_target_count": 0,
            "proxies_total": 0,
            "proxies_working": 0,
            "current_proxy": "",
            "current_account": "",
            "start_time": time.time(),
            "status": "Idle",
            "operation": "",
            "requests_sent": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "errors_last": "",
            "campaign_type": "",
            "target_progress": 0,
            "target_total": 100,
        }
        
        self._lock = threading.Lock()

    def update(self, **kwargs):
        """Thread-safe stats update"""
        with self._lock:
            for key, value in kwargs.items():
                if key in self.stats:
                    self.stats[key] = value

    def _get_elapsed(self) -> str:
        """Get formatted elapsed time"""
        elapsed = int(time.time() - self.stats["start_time"])
        h, m = divmod(elapsed, 3600)
        m, s = divmod(m, 60)
        if h:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"

    def _get_rate(self, count: int) -> str:
        """Get rate per minute"""
        elapsed_min = (time.time() - self.stats["start_time"]) / 60
        if elapsed_min < 0.1:
            return "0/min"
        rate = count / elapsed_min
        return f"{rate:.1f}/min"

    def _build_display(self) -> str:
        """Build the display string (fallback if rich not available)"""
        with self._lock:
            s = self.stats.copy()
        
        success_rate = 0
        if s["requests_sent"] > 0:
            success_rate = (s["requests_success"] / s["requests_sent"]) * 100
        
        total_actions = s["views_completed"] + s["likes_completed"] + s["shares_completed"]
        total_failed = s["views_failed"] + s["likes_failed"] + s["shares_failed"]
        
        lines = [
            "=" * 65,
            f"  TIKTOK BOT - LIVE DASHBOARD",
            f"  Status: {s['status']:30s} | {self._get_elapsed()}",
            "=" * 65,
            "",
            f"  📊 ACCOUNTS",
            f"     Loaded:     {s['accounts_loaded']}",
            f"     Active:     {s['accounts_active']}",
            f"     Total Views: {s['accounts_total_views']}",
            "",
            f"  👁️  VIEWS     Rate: {self._get_rate(s['views_completed'])}",
            f"     Completed:  {s['views_completed']}",
            f"     Failed:     {s['views_failed']}",
            f"     In Progress: {s['views_in_progress']}",
            "",
            f"  ❤️  LIKES     Rate: {self._get_rate(s['likes_completed'])}",
            f"     Completed:  {s['likes_completed']}",
            f"     Failed:     {s['likes_failed']}",
            "",
            f"  🔗  SHARES    Rate: {self._get_rate(s['shares_completed'])}",
            f"     Completed:  {s['shares_completed']}",
            f"     Failed:     {s['shares_failed']}",
            "",
            f"  📊 TOTAL: {total_actions} actions | {total_failed} failed",
            f"     Target: {s['views_target_video']}",
            f"     Progress: {s['views_completed']}/{s['views_target_count']} views",
            "",
            f"  🌐 PROXIES",
            f"     Total:      {s['proxies_total']}",
            f"     Working:    {s['proxies_working']}",
            f"     Current:    {s['current_proxy'][:30] if s['current_proxy'] else 'None'}",
            "",
            f"  📡 REQUESTS",
            f"     Sent:       {s['requests_sent']}",
            f"     Success:    {s['requests_success']}",
            f"     Failed:     {s['requests_failed']}",
            f"     Success %:  {success_rate:.1f}%",
            f"     Rate:       {self._get_rate(s['requests_sent'])}",
            "",
            f"  👤 CURRENT",
            f"     Account:    {s['current_account']}",
            f"     Operation:  {s['operation']}",
            f"     Campaign:   {s['campaign_type']}",
            "",
            f"  ❌ Last Error: {s['errors_last'] or 'None'}",
            "",
            "=" * 65,
            f"  [Ctrl+C] to stop  |  refresh: {self.refresh_interval}s",
            "=" * 65,
        ]
        return "\n".join(lines)

    def _build_rich_display(self) -> Layout:
        """Build rich layout"""
        with self._lock:
            s = self.stats.copy()
        
        success_rate = 0
        if s["requests_sent"] > 0:
            success_rate = (s["requests_success"] / s["requests_sent"]) * 100
        
        total_actions = s["views_completed"] + s["likes_completed"] + s["shares_completed"]
        total_failed = s["views_failed"] + s["likes_failed"] + s["shares_failed"]
        
        layout = Layout()
        
        header_text = Text.assemble(
            ("TIKTOK BOT v3.0 ", "bold cyan"),
            ("LIVE DASHBOARD", "bold yellow"),
            f"\n  Status: [{s['status']}]  |  Elapsed: {self._get_elapsed()}  |  "
            f"Rate: {self._get_rate(total_actions)} actions",
            style="bold"
        )
        layout.split(
            Layout(Panel(header_text, style="bold white on black"), size=4),
            Layout(name="body"),
        )
        
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )
        
        acc_table = Table(box=box.ROUNDED, title="📊 ACCOUNTS", title_style="bold cyan", show_header=False)
        acc_table.add_column("Metric", style="cyan")
        acc_table.add_column("Value", justify="right", style="bold")
        acc_table.add_row("Loaded", str(s["accounts_loaded"]))
        acc_table.add_row("Active", str(s["accounts_active"]))
        acc_table.add_row("Total Views Delivered", str(s["accounts_total_views"]))
        
        views_table = Table(box=box.ROUNDED, title=f"👁️ VIEWS [{self._get_rate(s['views_completed'])}]", 
                           title_style="bold green", show_header=False)
        views_table.add_column("Metric", style="green")
        views_table.add_column("Value", justify="right", style="bold")
        views_table.add_row("Completed", str(s["views_completed"]))
        views_table.add_row("Failed", str(s["views_failed"]))
        views_table.add_row("In Progress", str(s["views_in_progress"]))
        views_table.add_row("Target", f"{s['views_target_video'][:20] if s['views_target_video'] else 'N/A'}")
        
        like_table = Table(box=box.ROUNDED, title=f"❤️ LIKES [{self._get_rate(s['likes_completed'])}]", 
                          title_style="bold red", show_header=False)
        like_table.add_column("Metric", style="red")
        like_table.add_column("Value", justify="right", style="bold")
        like_table.add_row("Completed", str(s["likes_completed"]))
        like_table.add_row("Failed", str(s["likes_failed"]))
        
        share_table = Table(box=box.ROUNDED, title=f"🔗 SHARES [{self._get_rate(s['shares_completed'])}]", 
                           title_style="bold blue", show_header=False)
        share_table.add_column("Metric", style="blue")
        share_table.add_column("Value", justify="right", style="bold")
        share_table.add_row("Completed", str(s["shares_completed"]))
        share_table.add_row("Failed", str(s["shares_failed"]))
        
        summary_table = Table(box=box.ROUNDED, title="📈 SUMMARY", title_style="bold yellow", show_header=False)
        summary_table.add_column("Metric", style="yellow")
        summary_table.add_column("Value", justify="right", style="bold")
        summary_table.add_row("Total Actions", str(total_actions))
        summary_table.add_row("Failed", str(total_failed))
        summary_table.add_row("Progress", f"{s['views_completed']}/{s['views_target_count']}")
        
        left_panels = Table.grid()
        left_panels.add_row(Panel(acc_table))
        left_panels.add_row(Panel(views_table))
        left_panels.add_row(Panel(like_table))
        left_panels.add_row(Panel(share_table))
        left_panels.add_row(Panel(summary_table))
        
        layout["left"] = Layout(left_panels)
        
        proxy_table = Table(box=box.ROUNDED, title="🌐 PROXIES", title_style="bold magenta", show_header=False)
        proxy_table.add_column("Metric", style="magenta")
        proxy_table.add_column("Value", justify="right", style="bold")
        proxy_table.add_row("Total Scraped", str(s["proxies_total"]))
        proxy_table.add_row("Working", str(s["proxies_working"]))
        proxy_table.add_row("Current", s["current_proxy"][:25] if s["current_proxy"] else "None")
        
        req_table = Table(box=box.ROUNDED, title=f"📡 REQUESTS [{self._get_rate(s['requests_sent'])}]", 
                         title_style="bold blue", show_header=False)
        req_table.add_column("Metric", style="blue")
        req_table.add_column("Value", justify="right", style="bold")
        req_table.add_row("Sent", str(s["requests_sent"]))
        req_table.add_row("Success", str(s["requests_success"]))
        req_table.add_row("Failed", str(s["requests_failed"]))
        req_table.add_row("Success Rate", f"{success_rate:.1f}%")
        
        current_table = Table(box=box.ROUNDED, title="👤 CURRENT", title_style="bold yellow", show_header=False)
        current_table.add_column("Item", style="yellow")
        current_table.add_column("Value", style="bold")
        current_table.add_row("Account", s["current_account"] or "N/A")
        current_table.add_row("Operation", s["operation"] or "Idle")
        current_table.add_row("Campaign", s["campaign_type"] or "N/A")
        
        progress_display = ""
        if s["views_target_count"] > 0 and s["views_completed"] > 0:
            pct = min(100, int((s["views_completed"] / s["views_target_count"]) * 100))
            bar_len = 30
            filled = int(bar_len * pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            progress_display = f"\n  Progress: [{bar}] {pct}%"
        
        right_panels = Table.grid()
        right_panels.add_row(Panel(proxy_table))
        right_panels.add_row(Panel(req_table))
        right_panels.add_row(Panel(current_table))
        if progress_display:
            right_panels.add_row(Panel(progress_display, style="bold green"))
        
        layout["right"] = Layout(right_panels)
        
        if s["errors_last"]:
            error_text = Text(f"❌ Last Error: {s['errors_last']}", style="bold red")
            layout["body"].split_column(
                Layout(name="body"),
                Layout(Panel(error_text, style="red on black"), size=3),
            )
        
        return layout

    def refresh(self):
        """Refresh display once"""
        if RICH_AVAILABLE and self.console:
            self.console.clear()
            self.console.print(self._build_rich_display())
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(self._build_display())

    def start(self):
        """Start live dashboard in background thread"""
        self._running = True
        self.stats["start_time"] = time.time()
        
        if RICH_AVAILABLE and self.console:
            self._thread = threading.Thread(target=self._rich_loop, daemon=True)
        else:
            self._thread = threading.Thread(target=self._simple_loop, daemon=True)
        
        self._thread.start()

    def stop(self):
        """Stop the dashboard"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _simple_loop(self):
        """Simple terminal refresh loop"""
        while self._running:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(self._build_display())
            time.sleep(self.refresh_interval)

    def _rich_loop(self):
        """Rich library live display loop"""
        try:
            with Live(self._build_rich_display(), 
                      refresh_per_second=1/self.refresh_interval,
                      screen=True) as live:
                while self._running:
                    live.update(self._build_rich_display())
                    time.sleep(self.refresh_interval)
        except Exception:
            while self._running:
                os.system('cls' if os.name == 'nt' else 'clear')
                print(self._build_display())
                time.sleep(self.refresh_interval)


if __name__ == "__main__":
    dash = Dashboard(refresh_interval=0.5)
    dash.start()
    
    try:
        for i in range(200):
            time.sleep(0.3)
            dash.update(
                accounts_loaded=25,
                accounts_active=18,
                accounts_total_views=15420,
                views_completed=i * 2,
                views_failed=i // 5,
                views_in_progress=3,
                likes_completed=i * 5,
                likes_failed=i // 3,
                shares_completed=i * 1,
                shares_failed=i // 8,
                proxies_working=87,
                proxies_total=1540,
                current_account=f"user_live_{i % 8}",
                current_proxy=f"socks5://198.51.100.{i % 50}:1080",
                requests_sent=i * 8,
                requests_success=i * 6,
                requests_failed=i * 2,
                views_target_count=500,
                campaign_type="Live Campaign",
                operation="Sending views+likes+shares",
                status="Running",
            )
    except KeyboardInterrupt:
        pass
    finally:
        dash.stop()
