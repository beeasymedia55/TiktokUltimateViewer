#!/usr/bin/env python3
"""
Proxy Manager - Scraping, Checking, Rotation
Features: 12+ sources, multi-threaded checker, latency measurement,
          round-robin & random rotation, save/load working proxies
Author: HackerAI PenTest Framework
"""
import re
import os
import sys
import time
import json
import random
import threading
import queue
from urllib.request import urlopen, Request, ProxyHandler, build_opener, install_opener
from urllib.error import URLError
from datetime import datetime
from typing import Optional, List, Dict, Tuple

from config import config


class ProxyManager:
    """Full proxy management with scraping, checking, and rotation"""

    PROXY_SOURCES = [
        # HTTP/SOCKS proxy lists
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000&country=all",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
        "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies_http.txt",
        "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies_socks4.txt",
        "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies_socks5.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    ]

    def __init__(self):
        self.proxies: List[Dict] = []
        self.working_proxies: List[Dict] = []
        self._index = 0
        self._lock = threading.Lock()
        self._loaded_from_file = False
        self._load_working()

    def _load_working(self):
        """Load previously saved working proxies"""
        wpf = config.get("working_proxies_file")
        if wpf and os.path.exists(wpf):
            try:
                with open(wpf, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            parts = line.split(",")
                            proxy = {
                                "ip": parts[0].split(":")[0] if ":" in parts[0] else parts[0],
                                "port": parts[0].split(":")[1] if ":" in parts[0] else "80",
                                "type": parts[1] if len(parts) > 1 else "http",
                                "latency": float(parts[2]) if len(parts) > 2 else 0,
                                "source": "file"
                            }
                            self.working_proxies.append(proxy)
                if self.working_proxies:
                    self._loaded_from_file = True
                    print(f"  [✓] Loaded {len(self.working_proxies)} working proxies from file")
            except Exception as e:
                pass

    def save_working_proxies(self):
        """Save working proxies to file"""
        wpf = config.get("working_proxies_file")
        if not wpf:
            return
        try:
            with open(wpf, 'w') as f:
                for p in self.working_proxies:
                    f.write(f"{p['ip']}:{p['port']},{p['type']},{p.get('latency', 0)}\n")
        except Exception as e:
            print(f"  [!] Failed to save proxies: {e}")

    def scrape_proxies(self, progress_callback=None) -> int:
        """Scrape proxies from all sources"""
        all_proxies = []
        seen = set()

        for i, url in enumerate(self.PROXY_SOURCES):
            try:
                if progress_callback:
                    progress_callback(i + 1, len(self.PROXY_SOURCES), f"Scraping source {i+1}")
                
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                resp = urlopen(req, timeout=10)
                data = resp.read().decode('utf-8', errors='ignore')
                
                # Extract IP:Port patterns
                found = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)', data)
                
                # Determine proxy type from URL
                proxy_type = "http"
                if "socks4" in url.lower():
                    proxy_type = "socks4"
                elif "socks5" in url.lower():
                    proxy_type = "socks5"
                
                for ip, port in found:
                    key = f"{ip}:{port}"
                    if key not in seen:
                        seen.add(key)
                        all_proxies.append({
                            "ip": ip,
                            "port": port,
                            "type": proxy_type,
                            "source": f"source_{i+1}"
                        })
                        
            except Exception as e:
                continue

        self.proxies = all_proxies
        print(f"\n  [✓] Scraped {len(all_proxies)} proxies from {len(self.PROXY_SOURCES)} sources")
        return len(all_proxies)

    def check_proxies(self, progress_callback=None) -> int:
        """Multi-threaded proxy checker with latency measurement"""
        test_url = "http://httpbin.org/ip"
        timeout = config.get("proxy_check_timeout", 5)
        max_threads = config.get("proxy_check_threads", 50)
        
        to_check = self.proxies if not self.working_proxies else self.proxies + self.working_proxies
        working = []
        checked = set()
        
        if not to_check:
            return 0

        result_queue = queue.Queue()
        work_queue = queue.Queue()
        
        for p in to_check:
            key = f"{p['ip']}:{p['port']}:{p['type']}"
            if key not in checked:
                checked.add(key)
                work_queue.put(p)

        total = work_queue.qsize()
        
        def checker():
            while True:
                try:
                    proxy = work_queue.get_nowait()
                except queue.Empty:
                    break
                
                proxy_url = f"{proxy['type']}://{proxy['ip']}:{proxy['port']}"
                start = time.time()
                
                try:
                    handler = ProxyHandler({proxy['type']: proxy_url})
                    opener = build_opener(handler)
                    install_opener(opener)
                    
                    resp = urlopen(test_url, timeout=timeout)
                    resp.read()
                    latency = (time.time() - start) * 1000  # ms
                    
                    proxy['latency'] = latency
                    result_queue.put(proxy)
                    
                except Exception:
                    pass

        threads = []
        for _ in range(min(max_threads, total)):
            t = threading.Thread(target=checker, daemon=True)
            t.start()
            threads.append(t)

        # Collect results
        last_count = 0
        while any(t.is_alive() for t in threads) or not result_queue.empty():
            try:
                proxy = result_queue.get_nowait()
                working.append(proxy)
                if progress_callback and len(working) > last_count:
                    last_count = len(working)
                    progress_callback(len(working), total, f"Working: {len(working)}/{total}")
            except queue.Empty:
                time.sleep(0.1)

        for t in threads:
            t.join()

        # Drain remaining
        while not result_queue.empty():
            working.append(result_queue.get_nowait())

        # Sort by latency
        working.sort(key=lambda x: x.get('latency', 9999))
        
        self.working_proxies = working
        self.save_working_proxies()
        
        print(f"\n  [✓] Found {len(working)} working proxies (avg latency: {sum(p.get('latency',0) for p in working)/max(len(working),1):.0f}ms)")
        return len(working)

    def get_proxy(self) -> Optional[Dict]:
        """Get next proxy based on rotation mode"""
        if not self.working_proxies:
            return None
        
        mode = config.get("proxy_rotation", "round_robin")
        
        with self._lock:
            if mode == "random":
                return random.choice(self.working_proxies)
            else:  # round_robin
                proxy = self.working_proxies[self._index % len(self.working_proxies)]
                self._index += 1
                return proxy

    def get_proxy_url(self) -> Optional[str]:
        """Get proxy as URL string"""
        proxy = self.get_proxy()
        if proxy:
            return f"{proxy['type']}://{proxy['ip']}:{proxy['port']}"
        return None

    def get_working_count(self) -> int:
        """Get count of working proxies"""
        return len(self.working_proxies)

    def get_proxy_stats(self) -> Dict:
        """Get proxy statistics"""
        if not self.working_proxies:
            return {"total": 0, "avg_latency": 0, "sources": {}}
        
        src_counts = {}
        for p in self.working_proxies:
            src = p.get('source', 'unknown')
            src_counts[src] = src_counts.get(src, 0) + 1
        
        latencies = [p.get('latency', 0) for p in self.working_proxies if p.get('latency', 0) > 0]
        
        return {
            "total": len(self.working_proxies),
            "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
            "min_latency": min(latencies) if latencies else 0,
            "max_latency": max(latencies) if latencies else 0,
            "sources": src_counts,
            "types": {
                "http": sum(1 for p in self.working_proxies if p['type'] == 'http'),
                "socks4": sum(1 for p in self.working_proxies if p['type'] == 'socks4'),
                "socks5": sum(1 for p in self.working_proxies if p['type'] == 'socks5'),
            }
              }
