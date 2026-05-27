#!/usr/bin/env python3
"""
Proxy Manager - Scraping, Checking, Rotation
Features: 18+ sources, asyncio multi-threaded checker (500+ threads),
          latency measurement, round-robin & random & fastest rotation,
          save/load working proxies, TikTok endpoint testing
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
import asyncio
from urllib.request import urlopen, Request, ProxyHandler, build_opener, install_opener
from urllib.error import URLError
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import config


class ProxyManager:
    """
    Full proxy management with scraping, checking, and rotation.
    
    Features:
    - 18+ proxy sources (HTTP/SOCKS4/SOCKS5)
    - 500-thread ThreadPoolExecutor checker
    - Asyncio-based ultra-fast checker (200 concurrent)
    - Latency measurement in ms
    - Round-robin, random & fastest rotation modes
    - Auto-save/load working proxies
    - TikTok endpoint testing for live compatibility
    """

    PROXY_SOURCES = [
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
        "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt",
        "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks4/data.txt",
        "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt",
        "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.txt",
        "https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list.txt",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    ]

    TIKTOK_TEST_ENDPOINTS = [
        "https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/?aid=1233",
        "https://www.tiktok.com/",
        "https://api19-normal-c-useast1a.tiktokv.com/aweme/v1/hot/search/list/",
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
                        if line and ":" in line:
                            parts = line.split(",")
                            ip_port = parts[0].split(":")
                            ptype = parts[1] if len(parts) > 1 else "http"
                            if ptype not in ["http", "socks4", "socks5"]:
                                ptype = "http"
                            proxy = {
                                "ip": ip_port[0],
                                "port": ip_port[1] if len(ip_port) > 1 else "80",
                                "type": ptype,
                                "latency": float(parts[2]) if len(parts) > 2 else 0,
                                "source": "file"
                            }
                            self.working_proxies.append(proxy)
                if self.working_proxies:
                    self._loaded_from_file = True
                    print(f"  [✓] Loaded {len(self.working_proxies)} working proxies from file")
            except Exception as e:
                print(f"  [!] Error loading proxies file: {e}")

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

    def _validate_ip(self, ip: str) -> bool:
        """Quick IP validation"""
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        for p in parts:
            try:
                num = int(p)
                if num < 0 or num > 255:
                    return False
            except ValueError:
                return False
        first = int(parts[0])
        if first in (10, 127) or first == 192 and int(parts[1]) == 168:
            return False
        if first == 172 and 16 <= int(parts[1]) <= 31:
            return False
        return True

    def scrape_proxies(self, progress_callback: Optional[Callable] = None, 
                       max_sources: int = 19) -> int:
        """
        Scrape proxies from up to 19 sources.
        
        Args:
            progress_callback: Callable(current_source, total_sources)
            max_sources: Number of sources to scrape
        
        Returns:
            Number of unique proxies scraped
        """
        all_proxies = []
        seen = set()
        
        sources = self.PROXY_SOURCES[:max_sources]
        total_sources = len(sources)
        
        for i, url in enumerate(sources):
            try:
                if progress_callback:
                    progress_callback(i + 1, total_sources)
                
                req = Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/plain, */*",
                    "Connection": "keep-alive",
                })
                resp = urlopen(req, timeout=15)
                data = resp.read().decode('utf-8', errors='ignore')
                
                found = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})', data)
                
                url_lower = url.lower()
                if "socks5" in url_lower:
                    proxy_type = "socks5"
                elif "socks4" in url_lower:
                    proxy_type = "socks4"
                else:
                    proxy_type = "http"
                
                for ip, port in found:
                    if self._validate_ip(ip) and 80 <= int(port) <= 65535:
                        key = f"{ip}:{port}"
                        if key not in seen:
                            seen.add(key)
                            all_proxies.append({
                                "ip": ip,
                                "port": port,
                                "type": proxy_type,
                                "source": f"src_{i+1}"
                            })
            except Exception:
                continue

        self.proxies = all_proxies
        print(f"\n  [✓] Scraped {len(all_proxies)} unique proxies from {total_sources} sources")
        return len(all_proxies)

    def check_proxies(self, progress_callback: Optional[Callable] = None,
                      max_workers: int = 500, timeout: int = 3) -> int:
        """
        Ultra-fast multi-threaded proxy checker using ThreadPoolExecutor.
        
        Args:
            progress_callback: Callable(working_count, total_proxies)
            max_workers: Maximum concurrent checks (default: 500)
            timeout: Timeout in seconds per proxy (default: 3)
        
        Returns:
            Number of working proxies found
        """
        test_url = config.get("proxy_test_url", "http://httpbin.org/ip")
        actual_timeout = timeout or config.get("proxy_check_timeout", 3)
        actual_workers = min(max_workers, config.get("proxy_check_threads", 500))
        
        to_check = list(self.proxies) if self.proxies else []
        if self.working_proxies:
            existing_keys = {f"{p['ip']}:{p['port']}:{p['type']}" for p in to_check}
            for p in self.working_proxies:
                key = f"{p['ip']}:{p['port']}:{p['type']}"
                if key not in existing_keys:
                    to_check.append(p)
                    existing_keys.add(key)
        
        if not to_check:
            return 0

        total = len(to_check)
        working = []
        checked_lock = threading.Lock()
        checked_count = [0]

        def check_single(proxy: Dict) -> Optional[Dict]:
            proxy_url = f"{proxy['type']}://{proxy['ip']}:{proxy['port']}"
            start = time.time()
            try:
                proxy_handler = ProxyHandler({'http': proxy_url, 'https': proxy_url})
                opener = build_opener(proxy_handler)
                opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Linux; Android 13; Pixel 7)')]
                resp = opener.open(test_url, timeout=actual_timeout)
                resp.read()
                latency = (time.time() - start) * 1000
                proxy['latency'] = round(latency, 1)
                return proxy
            except Exception:
                return None

        print(f"\n  [*] Checking {total} proxies with {actual_workers} workers (timeout: {actual_timeout}s)...")
        
        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            futures = {executor.submit(check_single, p): p for p in to_check}
            
            last_report = [0]
            for future in as_completed(futures):
                with checked_lock:
                    checked_count[0] += 1
                    current = checked_count[0]
                
                result = future.result()
                if result:
                    with checked_lock:
                        working.append(result)
                
                if current - last_report[0] >= 50 or (result and len(working) % 5 == 0):
                    last_report[0] = current
                    if progress_callback:
                        progress_callback(len(working), total)

        working.sort(key=lambda x: x.get('latency', 9999))
        self.working_proxies = working
        self.save_working_proxies()
        
        avg_lat = sum(p.get('latency', 0) for p in working) / max(len(working), 1)
        print(f"\n  [✓] Found {len(working)} working proxies (avg latency: {avg_lat:.0f}ms)")
        return len(working)

    def check_proxies_asyncio(self, progress_callback: Optional[Callable] = None,
                              concurrency: int = 200, timeout: int = 3) -> int:
        """
        Asyncio-based proxy checker for maximum speed.
        Falls back to threaded checker if aiohttp is not installed.
        
        Args:
            progress_callback: Callable(working_count, total_proxies)
            concurrency: Maximum concurrent connections (default: 200)
            timeout: Timeout per proxy (default: 3)
        
        Returns:
            Number of working proxies
        """
        try:
            import aiohttp
        except ImportError:
            print("  [!] aiohttp not installed, falling back to threaded checker")
            return self.check_proxies(progress_callback, 300, timeout)

        to_check = list(self.proxies) if self.proxies else []
        if self.working_proxies:
            existing_keys = {f"{p['ip']}:{p['port']}:{p['type']}" for p in to_check}
            for p in self.working_proxies:
                key = f"{p['ip']}:{p['port']}:{p['type']}"
                if key not in existing_keys:
                    to_check.append(p)
                    existing_keys.add(key)
        
        if not to_check:
            return 0

        total = len(to_check)
        working = []
        working_lock = asyncio.Lock()
        progress = [0]
        last_report = [0]
        semaphore = asyncio.Semaphore(concurrency)

        async def check_single(session: aiohttp.ClientSession, proxy: Dict) -> Optional[Dict]:
            proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
            start = time.time()
            async with semaphore:
                try:
                    async with session.get(
                        "http://httpbin.org/ip",
                        proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                        headers={"User-Agent": "Mozilla/5.0"}
                    ) as resp:
                        await resp.read()
                        latency = (time.time() - start) * 1000
                        proxy['latency'] = round(latency, 1)
                        return proxy
                except Exception:
                    return None
                finally:
                    async with working_lock:
                        progress[0] += 1

        async def run():
            connector = aiohttp.TCPConnector(limit=concurrency, limit_per_host=10)
            timeout_obj = aiohttp.ClientTimeout(total=timeout + 1)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj) as session:
                tasks = [check_single(session, p) for p in to_check]
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    if result:
                        async with working_lock:
                            working.append(result)
                    if progress_callback and progress[0] - last_report[0] >= 100:
                        last_report[0] = progress[0]
                        progress_callback(len(working), total)

        try:
            asyncio.run(run())
        except Exception as e:
            print(f"  [!] Asyncio error: {e}")
            return self.check_proxies(progress_callback, 300, timeout)

        working.sort(key=lambda x: x.get('latency', 9999))
        self.working_proxies = working
        self.save_working_proxies()
        
        avg_lat = sum(p.get('latency', 0) for p in working) / max(len(working), 1)
        print(f"\n  [✓] Asyncio check: {len(working)} working proxies (avg latency: {avg_lat:.0f}ms)")
        return len(working)

    def test_proxy_on_tiktok(self, proxy: Optional[Dict] = None) -> Dict[str, any]:
        """Test a proxy specifically against TikTok endpoints"""
        if proxy is None:
            proxy = self.get_proxy()
        if not proxy:
            return {"error": "No proxy available"}
        
        proxy_url = f"{proxy['type']}://{proxy['ip']}:{proxy['port']}"
        results = {}
        
        for endpoint in self.TIKTOK_TEST_ENDPOINTS:
            start = time.time()
            try:
                proxy_handler = ProxyHandler({'http': proxy_url, 'https': proxy_url})
                opener = build_opener(proxy_handler)
                opener.addheaders = [
                    ('User-Agent', 'com.zhiliaoapp.musically/31.5.2 (Linux; U; Android 13; en_US)'),
                    ('Accept', 'application/json'),
                ]
                resp = opener.open(endpoint, timeout=8)
                resp.read()
                latency = (time.time() - start) * 1000
                results[endpoint] = {
                    "status": "ok",
                    "latency_ms": round(latency, 1),
                    "http_code": resp.getcode()
                }
            except Exception as e:
                results[endpoint] = {
                    "status": "failed",
                    "error": str(e)[:60],
                    "latency_ms": round((time.time() - start) * 1000, 1)
                }
        return results

    def test_all_proxies_on_tiktok(self, max_proxies: int = 10) -> List[Dict]:
        """Test top N working proxies against TikTok endpoints"""
        if not self.working_proxies:
            return []
        
        test_set = self.working_proxies[:min(max_proxies, len(self.working_proxies))]
        results = []
        
        print(f"\n  [*] Testing {len(test_set)} proxies on TikTok endpoints...")
        
        for i, proxy in enumerate(test_set):
            result = self.test_proxy_on_tiktok(proxy)
            endpoint_results = {}
            all_ok = True
            
            for ep, ep_result in result.items():
                if "tiktok" in ep:
                    ep_name = ep.split("/")[3] if len(ep.split("/")) > 3 else ep[:30]
                    endpoint_results[ep_name] = ep_result.get("status", "failed")
                    if ep_result.get("status") != "ok":
                        all_ok = False
            
            entry = {
                "proxy": f"{proxy['ip']}:{proxy['port']}",
                "type": proxy['type'],
                "latency": proxy.get('latency', 0),
                "all_tiktok_ok": all_ok,
                "endpoints": endpoint_results,
            }
            results.append(entry)
            
            status = "✓" if all_ok else "✗"
            print(f"    {i+1}. {entry['proxy']:20s} [{entry['type']:6s}] "
                  f"lat: {entry['latency']:.0f}ms  {status}")
        
        return results

    def get_proxy(self) -> Optional[Dict]:
        """Get next proxy based on rotation mode"""
        if not self.working_proxies:
            return None
        
        mode = config.get("proxy_rotation", "round_robin")
        
        with self._lock:
            if mode == "random":
                return random.choice(self.working_proxies)
            elif mode == "fastest":
                return self.working_proxies[0] if self.working_proxies else None
            else:
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
        """Get detailed proxy statistics"""
        if not self.working_proxies:
            return {"total": 0, "avg_latency": 0, "sources": {}, "types": {}}
        
        src_counts = {}
        for p in self.working_proxies:
            src = p.get('source', 'unknown')
            src_counts[src] = src_counts.get(src, 0) + 1
        
        latencies = [p.get('latency', 0) for p in self.working_proxies if p.get('latency', 0) > 0]
        
        type_counts = {"http": 0, "socks4": 0, "socks5": 0}
        for p in self.working_proxies:
            t = p.get('type', 'http')
            if t in type_counts:
                type_counts[t] += 1
        
        latencies_sorted = sorted(latencies)
        
        return {
            "total": len(self.working_proxies),
            "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
            "min_latency": latencies_sorted[0] if latencies_sorted else 0,
            "max_latency": latencies_sorted[-1] if latencies_sorted else 0,
            "median_latency": latencies_sorted[len(latencies_sorted)//2] if latencies_sorted else 0,
            "sources": src_counts,
            "types": type_counts,
                         }
