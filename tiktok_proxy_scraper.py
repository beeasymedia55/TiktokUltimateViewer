#!/usr/bin/env python3
"""
TikTok-Optimized Proxy Scraper & Validator
Scrapes free proxy sources, validates against TikTok API
For authorized pentesting only
"""

import requests
import threading
import time
import random
import json
import re
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from bs4 import BeautifulSoup
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('proxy_scraper.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
TIKTOK_TEST_URL = "https://api22-normal-c-useast1a.tiktokv.com/aweme/v1/webcast/join/"
TIKTOK_TIMEOUT = 10
MAX_WORKERS = 50
OUTPUT_FILE = "tiktok_proxies.txt"

# TikTok user agents for validation
TIKTOK_UAS = [
    'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 13; en; SM-G998B Build/TP1A.220624.014; Cronet/112.0.5615.140)',
    'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 14; en; Pixel 8 Pro Build/UP1A.230905.011; Cronet/112.0.5615.140)',
    'Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36'
]

# ──────────────────────────────────────────────
# PROXY SCRAPER SOURCES
# ──────────────────────────────────────────────
class ProxyScraper:
    def __init__(self):
        self.proxies_found = set()
        self.proxies_valid = []
        self.lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_geonode(self):
        """Scrape from geonode.com"""
        try:
            log.info("[GeoNode] Scraping...")
            urls = [
                "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc",
                "https://proxylist.geonode.com/api/proxy-list?limit=500&page=2&sort_by=lastChecked&sort_type=desc",
                "https://proxylist.geonode.com/api/proxy-list?limit=500&page=3&sort_by=lastChecked&sort_type=desc"
            ]
            
            for url in urls:
                try:
                    resp = self.session.get(url, timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        for proxy in data.get('data', []):
                            ip = proxy.get('ip', '')
                            port = proxy.get('port', '')
                            protocols = proxy.get('protocols', ['http'])
                            if ip and port:
                                for proto in protocols:
                                    self.proxies_found.add(f"{proto}://{ip}:{port}")
                except:
                    continue
            
            log.info(f"[GeoNode] Found {len(self.proxies_found) if self.proxies_found else 0} proxies")
        except Exception as e:
            log.error(f"[GeoNode] Error: {e}")
    
    def scrape_proxyscrape(self):
        """Scrape from proxyscrape.com"""
        try:
            log.info("[ProxyScrape] Scraping...")
            urls = [
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000&country=all",
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
                "https://api.proxyscrape.com/?request=getproxies&proxytype=http&timeout=10000&country=all&ssl=yes&anonymity=anonymous"
            ]
            
            for url in urls:
                try:
                    resp = self.session.get(url, timeout=15)
                    if resp.status_code == 200:
                        text = resp.text.strip()
                        for line in text.split('\n'):
                            line = line.strip()
                            if line and ':' in line:
                                if not line.startswith('http'):
                                    self.proxies_found.add(f"http://{line}")
                                else:
                                    self.proxies_found.add(line)
                except:
                    continue
            
            log.info(f"[ProxyScrape] Found {len(self.proxies_found) if self.proxies_found else 0} total proxies")
        except Exception as e:
            log.error(f"[ProxyScrape] Error: {e}")
    
    def scrape_free_proxy_list(self):
        """Scrape from free-proxy-list.net"""
        try:
            log.info("[FreeProxyList] Scraping...")
            resp = self.session.get("https://free-proxy-list.net/", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                table = soup.find('table', {'id': 'proxylisttable'})
                if table:
                    rows = table.find_all('tr')[1:]  # skip header
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 7:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            https = cols[6].text.strip()
                            if ip and port:
                                proto = 'https' if https == 'yes' else 'http'
                                self.proxies_found.add(f"{proto}://{ip}:{port}")
            
            log.info(f"[FreeProxyList] Scraped")
        except Exception as e:
            log.error(f"[FreeProxyList] Error: {e}")
    
    def scrape_sslproxies(self):
        """Scrape from sslproxies.org"""
        try:
            log.info("[SSLProxies] Scraping...")
            resp = self.session.get("https://www.sslproxies.org/", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                table = soup.find('table', {'id': 'proxylisttable'})
                if table:
                    rows = table.find_all('tr')[1:]
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            if ip and port:
                                self.proxies_found.add(f"https://{ip}:{port}")
            
            log.info(f"[SSLProxies] Scraped")
        except Exception as e:
            log.error(f"[SSLProxies] Error: {e}")
    
    def scrape_proxynova(self):
        """Scrape from proxynova.com"""
        try:
            log.info("[ProxyNova] Scraping...")
            for page in range(1, 4):
                try:
                    resp = self.session.get(
                        f"https://www.proxynova.com/proxy-server-list/",
                        params={'page': page},
                        timeout=15
                    )
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        for tr in soup.find_all('tr'):
                            tds = tr.find_all('td')
                            if len(tds) >= 2:
                                ip_el = tds[0].find('abbr')
                                if ip_el:
                                    ip = ip_el.get('title', '').strip()
                                else:
                                    ip = tds[0].text.strip()
                                port = tds[1].text.strip()
                                if ip and port and re.match(r'\d+\.\d+\.\d+\.\d+', ip):
                                    self.proxies_found.add(f"http://{ip}:{port}")
                except:
                    continue
            
            log.info(f"[ProxyNova] Scraped")
        except Exception as e:
            log.error(f"[ProxyNova] Error: {e}")
    
    def scrape_hidemy_name(self):
        """Scrape from hidemy.name"""
        try:
            log.info("[HideMyName] Scraping...")
            resp = self.session.get("https://hidemy.name/en/proxy-list/", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')[1:]
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            if ip and port:
                                self.proxies_found.add(f"http://{ip}:{port}")
            
            log.info(f"[HideMyName] Scraped")
        except Exception as e:
            log.error(f"[HideMyName] Error: {e}")
    
    def scrape_us_proxy(self):
        """Scrape from us-proxy.org"""
        try:
            log.info("[US-Proxy] Scraping...")
            resp = self.session.get("https://www.us-proxy.org/", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                table = soup.find('table', {'id': 'proxylisttable'})
                if table:
                    rows = table.find_all('tr')[1:]
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            if ip and port:
                                self.proxies_found.add(f"http://{ip}:{port}")
            
            log.info(f"[US-Proxy] Scraped")
        except Exception as e:
            log.error(f"[US-Proxy] Error: {e}")
    
    def scrape_openproxy_space(self):
        """Scrape from openproxy.space"""
        try:
            log.info("[OpenProxy.Space] Scraping...")
            resp = self.session.get("https://openproxy.space/list/http", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for ip_list in data.values():
                    if isinstance(ip_list, list):
                        for entry in ip_list:
                            ip = entry.get('ip', entry if ':' not in entry else entry.split(':')[0])
                            port = entry.get('port', entry.split(':')[1] if ':' in entry else '')
                            if ip and port:
                                self.proxies_found.add(f"http://{ip}:{port}")
            log.info(f"[OpenProxy.Space] Scraped")
        except Exception as e:
            log.info(f"[OpenProxy.Space] No data or error (expected)")
    
    def scrape_advanced_name(self):
        """Scrape from advanced.name (freeproxy)"""
        try:
            log.info("[Advanced.Name] Scraping...")
            resp = self.session.get("https://advanced.name/freeproxy?page=1", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for div in soup.find_all('div', class_='proxy-list'):
                    items = div.find_all('div', class_='proxy-item')
                    for item in items:
                        ip_el = item.find('div', class_='ip')
                        port_el = item.find('div', class_='port')
                        if ip_el and port_el:
                            ip = ip_el.text.strip()
                            port = port_el.text.strip()
                            if ip and port:
                                self.proxies_found.add(f"http://{ip}:{port}")
            log.info(f"[Advanced.Name] Scraped")
        except Exception as e:
            log.info(f"[Advanced.Name] Error (expected)")
    
    def scrape_proxy_list_download(self):
        """Scrape from proxy-list.download"""
        try:
            log.info("[ProxyList.Download] Scraping...")
            urls = [
                "https://www.proxy-list.download/api/v1/get?type=http",
                "https://www.proxy-list.download/api/v1/get?type=https",
                "https://www.proxy-list.download/api/v1/get?type=socks4",
                "https://www.proxy-list.download/api/v1/get?type=socks5"
            ]
            
            for url in urls:
                try:
                    resp = self.session.get(url, timeout=15)
                    if resp.status_code == 200:
                        text = resp.text.strip()
                        for line in text.split('\n'):
                            line = line.strip()
                            if ':' in line:
                                if '://' in line:
                                    self.proxies_found.add(line)
                                else:
                                    proto = url.split('=')[-1].replace('http', 'http').replace('https', 'https')
                                    self.proxies_found.add(f"{proto}://{line}")
                except:
                    continue
            
            log.info(f"[ProxyList.Download] Scraped")
        except Exception as e:
            log.info(f"[ProxyList.Download] Error (expected)")
    
    def scrape_github_sources(self):
        """Scrape from various GitHub proxy lists"""
        log.info("[GitHub] Scraping proxy lists...")
        
        github_urls = [
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTP_RAW.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
            "https://raw.githubusercontent.com/elliottophellia/proxy-list/main/http.txt",
            "https://raw.githubusercontent.com/elliottophellia/proxy-list/main/socks4.txt",
            "https://raw.githubusercontent.com/elliottophellia/proxy-list/main/socks5.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy_list.txt"
        ]
        
        for url in github_urls:
            try:
                resp = self.session.get(url, timeout=20)
                if resp.status_code == 200:
                    text = resp.text.strip()
                    count = 0
                    for line in text.split('\n'):
                        line = line.strip()
                        if ':' in line and len(line) < 30:
                            if '://' not in line:
                                # Determine protocol from URL
                                if 'socks5' in url.lower() or 'socks5' in url.lower():
                                    self.proxies_found.add(f"socks5://{line}")
                                elif 'socks4' in url.lower():
                                    self.proxies_found.add(f"socks4://{line}")
                                elif 'https' in url.lower():
                                    self.proxies_found.add(f"https://{line}")
                                else:
                                    self.proxies_found.add(f"http://{line}")
                                count += 1
                    log.info(f"[GitHub] {url.split('/')[-1]}: {count} proxies")
            except:
                continue
    
    def scrape_all(self):
        """Run all scrapers concurrently"""
        scrapers = [
            self.scrape_geonode,
            self.scrape_proxyscrape,
            self.scrape_free_proxy_list,
            self.scrape_sslproxies,
            self.scrape_proxynova,
            self.scrape_hidemy_name,
            self.scrape_us_proxy,
            self.scrape_openproxy_space,
            self.scrape_advanced_name,
            self.scrape_proxy_list_download,
            self.scrape_github_sources
        ]
        
        threads = []
        for scraper in scrapers:
            t = threading.Thread(target=scraper)
            t.start()
            threads.append(t)
            time.sleep(0.5)  # Rate limiting
        
        for t in threads:
            t.join()
        
        log.info(f"\n[+] Total unique proxies scraped: {len(self.proxies_found):,}")
        return list(self.proxies_found)

# ──────────────────────────────────────────────
# TIKTOK PROXY VALIDATOR
# ──────────────────────────────────────────────
class TikTokProxyValidator:
    def __init__(self, proxies):
        self.proxies = proxies
        self.valid_proxies = []
        self.valid_lock = threading.Lock()
        self.checked = 0
        self.check_lock = threading.Lock()
        self.session = requests.Session()
        
        # Test headers that mimic TikTok Android
        self.test_headers = {
            'User-Agent': random.choice(TIKTOK_UAS),
            'Accept': '*/*',
            'Accept-Encoding': 'gzip',
            'Accept-Language': 'en,en-US;q=0.9',
            'Content-Type': 'application/json',
            'Connection': 'keep-alive',
            'X-Khronos': str(int(time.time()))
        }
    
    def test_proxy(self, proxy):
        """Test if proxy works with TikTok"""
        try:
            # Parse proxy string
            if '://' in proxy:
                proto = proxy.split('://')[0]
                addr = proxy.split('://')[1]
            else:
                proto = 'http'
                addr = proxy
            
            proxies = {
                'http': f"{proto}://{addr}",
                'https': f"{proto}://{addr}"
            }
            
            # Test 1: Basic connectivity to TikTok
            test_url = "https://www.tiktok.com/"
            resp = self.session.get(
                test_url,
                proxies=proxies,
                headers=self.test_headers,
                timeout=TIKTOK_TIMEOUT,
                allow_redirects=True
            )
            
            if resp.status_code not in [200, 302, 403]:
                return None
            
            # Test 2: Try TikTok API endpoint
            api_url = "https://api22-normal-c-useast1a.tiktokv.com/aweme/v1/webcast/room/"
            test_params = {'room_id': '1', 'aid': '1988'}
            
            resp2 = self.session.get(
                api_url,
                proxies=proxies,
                params=test_params,
                headers=self.test_headers,
                timeout=TIKTOK_TIMEOUT
            )
            
            if resp2.status_code in [200, 204, 400, 401, 403]:
                # Even 400+ means TikTok responded (not blocked)
                with self.valid_lock:
                    self.valid_proxies.append({
                        'proxy': proxy,
                        'protocol': proto,
                        'response_code': resp2.status_code,
                        'response_time': resp.elapsed.total_seconds(),
                        'tested_at': datetime.now().isoformat()
                    })
                return proxy
            
            return None
            
        except requests.exceptions.ProxyError:
            return None
        except requests.exceptions.ConnectTimeout:
            return None
        except requests.exceptions.ReadTimeout:
            return None
        except Exception:
            return None
    
    def test_proxy_wrapper(self, proxy):
        """Wrapper with progress tracking"""
        result = self.test_proxy(proxy)
        
        with self.check_lock:
            self.checked += 1
            checked = self.checked
            total = len(self.proxies)
            
            if checked % 50 == 0 or checked == total:
                pct = (checked / total) * 100
                valid_count = len(self.valid_proxies)
                rate = (valid_count / checked) * 100 if checked > 0 else 0
                log.info(f"Progress: {checked}/{total} ({pct:.1f}%) | Valid: {valid_count} ({rate:.1f}%)")
        
        return result
    
    def validate_all(self, max_workers=MAX_WORKERS):
        """Validate all proxies against TikTok"""
        log.info(f"\n[*] Validating {len(self.proxies):,} proxies against TikTok...")
        log.info(f"[*] Workers: {max_workers}")
        log.info(f"[*] Timeout: {TIKTOK_TIMEOUT}s")
        
        start = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.test_proxy_wrapper, proxy): proxy 
                for proxy in self.proxies
            }
            
            for future in as_completed(futures):
                future.result()
        
        elapsed = time.time() - start
        valid = len(self.valid_proxies)
        log.info(f"\n[✔] Validation complete in {elapsed:.1f}s")
        log.info(f"[✔] Valid TikTok proxies: {valid}/{len(self.proxies)} ({valid/len(self.proxies)*100:.1f}%)")
        
        return self.valid_proxies
    
    def save_results(self, filename=OUTPUT_FILE):
        """Save valid proxies to file"""
        if not self.valid_proxies:
            log.warning("No valid proxies to save")
            return
        
        # Save as plain list (for direct use in bot)
        with open(filename, 'w') as f:
            for p in self.valid_proxies:
                f.write(f"{p['proxy']}\n")
        
        # Save detailed JSON
        json_file = filename.replace('.txt', '_detailed.json')
        with open(json_file, 'w') as f:
            json.dump(self.valid_proxies, f, indent=2)
        
        log.info(f"\n[✔] Saved {len(self.valid_proxies)} proxies to:")
        log.info(f"    • {filename} (plain list)")
        log.info(f"    • {json_file} (detailed JSON)")
        
        # Summary stats
        protocols = {}
        codes = {}
        for p in self.valid_proxies:
            proto = p['protocol']
            protocols[proto] = protocols.get(proto, 0) + 1
            code = p['response_code']
            codes[code] = codes.get(code, 0) + 1
        
        log.info(f"\n[+] Protocol breakdown:")
        for proto, count in sorted(protocols.items()):
            log.info(f"    {proto}: {count}")
        
        log.info(f"\n[+] Response codes:")
        for code, count in sorted(codes.items()):
            log.info(f"    {code}: {count}")

# ──────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ──────────────────────────────────────────────
def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║       TIKTOK PROXY SCRAPER & VALIDATOR v2.0              ║
║   Scrapes 15+ sources → Validates vs TikTok API          ║
║   For authorized pentesting only                        ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Phase 1: Scrape
    log.info("[Phase 1] Scraping proxy sources...")
    log.info("Sources: GeoNode, ProxyScrape, FreeProxyList, SSLProxies,")
    log.info("         ProxyNova, HideMyName, US-Proxy, OpenProxy.Space,")
    log.info("         Advanced.Name, ProxyList.Download, 20x GitHub repos")
    
    scraper = ProxyScraper()
    all_proxies = scraper.scrape_all()
    
    if not all_proxies:
        log.error("No proxies scraped from any source!")
        sys.exit(1)
    
    # Deduplicate
    all_proxies = list(set(all_proxies))
    log.info(f"\n[✔] Total unique proxies: {len(all_proxies):,}")
    
    # Phase 2: Validate
    log.info("\n[Phase 2] Validating proxies against TikTok...")
    log.info("Testing connectivity to TikTok.com + API endpoints")
    log.info("This may take several minutes...")
    
    validator = TikTokProxyValidator(all_proxies)
    valid = validator.validate_all(max_workers=MAX_WORKERS)
    
    # Phase 3: Save
    if valid:
        validator.save_results(OUTPUT_FILE)
        
        log.info(f"\n{'='*60}")
        log.info(f"✅ READY FOR DEPLOYMENT")
        log.info(f"   {len(valid)} TikTok-validated proxies")
        log.info(f"   Saved to: {OUTPUT_FILE}")
        log.info(f"{'='*60}")
    else:
        log.warning("\n[!] No valid proxies found for TikTok!")
        log.warning("    Try running again or use residential proxies")
        log.warning("    Note: Free proxies have low success rate with TikTok")

if __name__ == "__main__":
    main()
