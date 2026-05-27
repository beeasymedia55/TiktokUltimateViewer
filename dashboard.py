#!/usr/bin/env python3
"""
Live Dashboard - Real-time stats display
Shows accounts loaded, current operations, proxy stats, views/likes/shares progress
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
    Shows real-time stats: accounts loaded, proxy status, views/likes/shares delivered, etc.
    """
    
    def __init__(self, refresh_interval: float = 1.0):
        self.console = Console() if RICH_AVAILABLE else None
        self.refresh_interval = refresh_interval
        self._running = False
        self._thread = None
        
        # Stats that get updated externally
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

    def _build_display(self) -> str:
        """Build the display string (fallback if rich not available)"""
        with self._lock:
            s = self.stats.copy()
        
        success_rate = 0
        if s["requests_sent"] > 0:
            success_rate = (s["requests_success"] / s["requests_sent"]) * 100
        
        lines = [
            "=" * 60,
            f"  TIKTOK BOT - LIVE DASHBOARD",
            f"  Status: {s['status']} | Elapsed: {self._get_elapsed()}",
            "=" * 60,
            "",
            f"  📊 ACCOUNTS",
            f"     Loaded:     {s['accounts_loaded']}",
            f"     Active:     {s['accounts_active']}",
            f"     Total Views: {s['accounts_total_views']}",
            "",
            f"  👁️  VIEWS",
            f"     Completed:  {s['views_completed']}",
            f"     Failed:     {s['views_failed']}",
            f"     In Progress: {s['views_in_progress']}",
            f"     Target:     {s['views_target_video']} ({s['views_target_count']} views)",
            "",
            f"  ❤️  LIKES",
            f"     Completed:  {s['likes_completed']}",
            f"     Failed:     {s['likes_failed']}",
            "",
            f"  🔗  SHARES",
            f"     Completed:  {s['shares_completed']}",
            f"     Failed:     {s['shares_failed']}",
            "",
            f"  🌐 PROXIES",
            f"     Total:      {s['proxies_total']}",
            f"     Working:    {s['proxies_working']}",
            f"     Current:    {s['current_proxy']}",
            "",
            f"  📡 REQUESTS",
            f"     Sent:       {s['requests_sent']}",
            f"     Success:    {s['requests_success']}",
            f"     Failed:     {s['requests_failed']}",
            f"     Success %:  {success_rate:.1f}%",
            "",
            f"  👤 CURRENT",
            f"     Account:    {s['current_account']}",
            f"     Operation:  {s['operation']}",
            "",
            f"  ❌ Last Error: {s['errors_last'] or 'None'}",
            "",
            "=" * 60,
            f"  Press [Ctrl+C] to stop gracefully",
            "=" * 60,
        ]
        return "\n".join(lines)

    def _build_rich_display(self) -> Layout:
        """Build rich layout (with rich library)"""
        with self._lock:
            s = self.stats.copy()
        
        success_rate = 0
        if s["requests_sent"] > 0:
            success_rate = (s["requests_success"] / s["requests_sent"]) * 100
        
        layout = Layout()
        
        # Header
        header_text = Text.assemble(
            ("TIKTOK BOT ", "bold cyan"),
            ("- LIVE DASHBOARD", "bold yellow"),
            f"\n  Status: {s['status']} | Elapsed: {self._get_elapsed()}",
            style="bold"
        )
        layout.split(
            Layout(Panel(header_text, style="bold white on black"), size=5),
            Layout(name="body"),
        )
        
        # Body with tables
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )
        
        # Left panel - Accounts, Views, Likes, Shares
        acc_table = Table(box=box.ROUNDED, title="📊 ACCOUNTS", title_style="bold cyan")
        acc_table.add_column("Metric", style="cyan")
        acc_table.add_column("Value", justify="right")
        acc_table.add_row("Loaded", str(s["accounts_loaded"]))
        acc_table.add_row("Active", str(s["accounts_active"]))
        acc_table.add_row("Total Views Delivered", str(s["accounts_total_views"]))
        
        views_table = Table(box=box.ROUNDED, title="👁️ VIEWS", title_style="bold green")
        views_table.add_column("Metric", style="green")
        views_table.add_column("Value", justify="right")
        views_table.add_row("Completed", str(s["views_completed"]))
        views_table.add_row("Failed", str(s["views_failed"]))
        views_table.add_row("In Progress", str(s["views_in_progress"]))
        views_table.add_row("Target Video", s["views_target_video"] or "N/A")
        views_table.add_row("Target Count", str(s["views_target_count"]))
        
        like_table = Table(box=box.ROUNDED, title="❤️ LIKES", title_style="bold red")
        like_table.add_column("Metric", style="red")
        like_table.add_column("Value", justify="right")
        like_table.add_row("Completed", str(s["likes_completed"]))
        like_table.add_row("Failed", str(s["likes_failed"]))
        
        share_table = Table(box=box.ROUNDED, title="🔗 SHARES", title_style="bold blue")
        share_table.add_column("Metric", style="blue")
        share_table.add_column("Value", justify="right")
        share_table.add_row("Completed", str(s["shares_completed"]))
        share_table.add_row("Failed", str(s["shares_failed"]))
        
        left_panels = Table.grid()
        left_panels.add_row(Panel(acc_table, style="bold"))
        left_panels.add_row(Panel(views_table, style="bold"))
        left_panels.add_row(Panel(like_table, style="bold"))
        left_panels.add_row(Panel(share_table, style="bold"))
        
        layout["left"] = Layout(left_panels)
        
        # Right panel - Proxies, Requests, Current
        proxy_table = Table(box=box.ROUNDED, title="🌐 PROXIES", title_style="bold magenta")
        proxy_table.add_column("Metric", style="magenta")
        proxy_table.add_column("Value", justify="right")
        proxy_table.add_row("Total", str(s["proxies_total"]))
        proxy_table.add_row("Working", str(s["proxies_working"]))
        proxy_table.add_row("Current", s["current_proxy"] or "None")
        
        req_table = Table(box=box.ROUNDED, title="📡 REQUESTS", title_style="bold blue")
        req_table.add_column("Metric", style="blue")
        req_table.add_column("Value", justify="right")
        req_table.add_row("Sent", str(s["requests_sent"]))
        req_table.add_row("Success", str(s["requests_success"]))
        req_table.add_row("Failed", str(s["requests_failed"]))
        req_table.add_row("Success Rate", f"{success_rate:.1f}%")
        
        current_table = Table(box=box.ROUNDED, title="👤 CURRENT", title_style="bold yellow")
        current_table.add_column("Item", style="yellow")
        current_table.add_column("Value")
        current_table.add_row("Account", s["current_account"] or "N/A")
        current_table.add_row("Operation", s["operation"] or "Idle")
        
        right_panels = Table.grid()
        right_panels.add_row(Panel(proxy_table, style="bold"))
        right_panels.add_row(Panel(req_table, style="bold"))
        right_panels.add_row(Panel(current_table, style="bold"))
        
        layout["right"] = Layout(right_panels)
        
        # Error section at bottom
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
    dash = Dashboard(refresh_interval=1.0)
    dash.start()
    
    try:
        for i in range(100):
            time.sleep(0.5)
            dash.update(
                accounts_loaded=10,
                accounts_active=5 + (i % 3),
                views_completed=i,
                views_failed=i // 10,
                likes_completed=i * 3,
                likes_failed=i // 5,
                shares_completed=i * 2,
                shares_failed=i // 8,
                proxies_working=25,
                current_account=f"user_{i % 5}",
                requests_sent=i * 3,
                requests_success=i * 2,
                requests_failed=i,
            )
    except KeyboardInterrupt:
        pass
    finally:
        dash.stop()
