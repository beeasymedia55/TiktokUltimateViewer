import asyncio  
import aiohttp  
import aiohttp_socks  
import random  
import time  
import logging  
import os  
import requests  
from bs4 import BeautifulSoup  
from dataclasses import dataclass, field, asdict  
from typing import List, Optional, Dict  
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query  
from fastapi.staticfiles import StaticFiles  
from fastapi.responses import HTMLResponse, FileResponse  
import uvicorn  
import re  
  
# --- 1. Data Models ---  
@dataclass  
class Proxy:  
    id: str  
    url: str  
    health: bool = False  
    last_check: float = field(default_factory=time.time)  
    fail_count: int = 0  
    max_fails: int = 3  
    source: str = "manual"  
    location: str = ""  # Optional: Store location for better proxy selection  
  
@dataclass  
class LiveTarget:  
    room_id: str = ""  
    owner_uid: str = ""  
    room_url: str = ""  
    is_live: bool = False  
    title: str = ""  
  
@dataclass  
class Stats:  
    views_sent: int = 0  
    views_failed: int = 0  
    active_campaign: bool = False  
    current_room: str = ""  
    views_target: int = 0  
    views_remaining: int = 0  
    start_time: float = 0  
    current_target: LiveTarget = field(default_factory=LiveTarget)  
  
# --- 2. Proxy Scrapers ---  
class ProxyScraper:  
    SOURCES = [  
        "https://spys.me/spys-one-proxylist/",  
        "https://spys.me/spys-one-proxylist-2/",  
        "https://spys.me/spys-one-proxylist-3/",  
        "https://free-proxy-list.com/",  
        "https://proxyNova.com/"  
    ]  
  
    @staticmethod  
    async def scrape_all(session: aiohttp.ClientSession) -> List[str]:  
        """Scrape from all sources"""  
        tasks = [  
            ProxyScraper._scrape_spys(session),  
            ProxyScraper._scrape_freeproxylist(session),  
            ProxyScraper._scrape_proxynova(session),  
            ProxyScraper._scrape_proxy_scrape(session)  
        ]  
        results = await asyncio.gather(*tasks)  
        proxies = []  
        for proxy_list in results:  
            proxies.extend(proxy_list)  
        # Remove duplicates  
        return list(set(proxies))  
  
    @staticmethod  
    async def _scrape_spys(session: aiohttp.ClientSession) -> List[str]:  
        urls = [  
            "https://spys.me/spys-one-proxylist/",  
            "https://spys.me/spys-one-proxylist-2/",  
            "https://spys.me/spys-one-proxylist-3/"  
        ]  
        proxies = []  
        for url in urls:  
            try:  
                async with session.get(url, timeout=10) as resp:  
                    if resp.status == 200:  
                        text = await resp.text()  
                        soup = BeautifulSoup(text, 'html.parser')  
                        table = soup.find('table', {'id': 'spy0'})  
                        if table:  
                            for row in table.find_all('tr')[1:]:  
                                cells = row.find_all('td')  
                                if len(cells) >= 2:  
                                    ip = cells[0].text.strip()  
                                    port = cells[1].text.strip()  
                                    protocol = cells[-1].text.strip()  
                                    proxies.append(f"{protocol.lower()}://{ip}:{port}")  
            except Exception as e:  
                logging.error(f"Spys scrape error: {e}")  
        return proxies  
  
    @staticmethod  
    async def _scrape_freeproxylist(session: aiohttp.ClientSession) -> List[str]:  
        url = "https://free-proxy-list.com/"  
        try:  
            async with session.get(url, timeout=10) as resp:  
                if resp.status == 200:  
                    text = await resp.text()  
                    soup = BeautifulSoup(text, 'html.parser')  
                    table = soup.find('table', class_='table')  
                    if table:  
                        for row in table.find_all('tr')[1:]:  
                            cells = row.find_all('td')  
                            if len(cells) >= 2:  
                                ip = cells[0].text.strip()  
                                port = cells[1].text.strip()  
                                proxies.append(f"http://{ip}:{port}")  
        except Exception as e:  
            logging.error(f"FreeProxyList scrape error: {e}")  
        return proxies  
  
    @staticmethod  
    async def _scrape_proxynova(session: aiohttp.ClientSession) -> List[str]:  
        url = "https://proxyNova.com/"  
        try:  
            async with session.get(url, timeout=10) as resp:  
                if resp.status == 200:  
                    text = await resp.text()  
                    soup = BeautifulSoup(text, 'html.parser')  
                    # Adjust selector based on actual HTML structure  
                    proxies = []  
                    for row in soup.find_all('tr'):  
                        cells = row.find_all('td')  
                        if len(cells) >= 2:  
                            ip = cells[0].text.strip()  
                            port = cells[1].text.strip()  
                            proxies.append(f"http://{ip}:{port}")  
                    return proxies  
        except Exception as e:  
            logging.error(f"ProxyNova scrape error: {e}")  
        return []  
  
    @staticmethod  
    async def _scrape_proxy_scrape(session: aiohttp.ClientSession) -> List[str]:  
        url = "https://api.proxyscrape.com/v2/free/get-proxies?timeout=5000&protocol=http"  
        try:  
            async with session.get(url, timeout=10) as resp:  
                if resp.status == 200:  
                    text = await resp.text()  
                    return [f"http://{line.strip()}" for line in text.splitlines() if line.strip()]  
        except Exception as e:  
            logging.error(f"ProxyScrape error: {e}")  
        return []  
  
# --- 3. TikTok Live URL Parser ---  
class TikTokLiveParser:  
    @staticmethod  
    async def parse_live_url(url: str) -> Optional[LiveTarget]:  
        """Parse a TikTok Live URL and return room details"""  
        # Extract room ID from URL  
        # Example: https://www.tiktok.com/@user/live/1234567890  
        match = re.search(r'/live/(\d+)', url)  
        if not match:  
            return None  
          
        room_id = match.group(1)  
          
        # Fetch room details via API  
        api_url = f"https://live.tiktok.com/api/v2/{room_id}/info"  
        try:  
            async with aiohttp.ClientSession() as session:  
                async with session.get(api_url, timeout=10) as resp:  
                    if resp.status == 200:  
                        data = await resp.json()  
                        if data.get('status') == 200:  
                            room_data = data.get('roomData', {})  
                            owner_data = room_data.get('owner', {})  
                            return LiveTarget(  
                                room_id=room_id,  
                                owner_uid=owner_data.get('uid', ''),  
                                room_url=url,  
                                is_live=True,  
                                title=room_data.get('title', '')  
                            )  
        except Exception as e:  
            logging.error(f"Failed to parse live URL: {e}")  
          
        return None  
  
# --- 4. Core Logic ---  
class ProxyManager:  
    def __init__(self):  
        self.proxies: List[Proxy] = []  
        self.lock = asyncio.Lock()  
        self.scraper_running = False  
        self.testing_running = False  
  
    def add_proxy(self, url: str, source: str = "manual") -> str:  
        proxy_id = f"{hash(url) % 1000000}"  
        if not any(p.url == url for p in self.proxies):  
            self.proxies.append(Proxy(id=proxy_id, url=url, source=source))  
            return proxy_id  
        return None  
  
    def remove_proxy(self, proxy_id: str):  
        self.proxies = [p for p in self.proxies if p.id != proxy_id]  
  
    async def get_proxy(self) -> Optional[str]:  
        async with self.lock:  
            healthy = [p for p in self.proxies if p.health and p.fail_count < p.max_fails]  
            if healthy:  
                proxy = random.choice(healthy)  
                return proxy.url  
            return None  
  
    async def check_health(self, proxy: Proxy):  
        try:  
            async with aiohttp.ClientSession() as session:  
                async with session.get('https://www.google.com',   
                                       proxy=proxy.url,   
                                       timeout=aiohttp.ClientTimeout(total=5)) as resp:  
                    if resp.status == 200:  
                        proxy.health = True  
                        proxy.fail_count = 0  
                    else:  
                        proxy.health = False  
        except Exception:  
            proxy.health = False  
        proxy.last_check = time.time()  
  
    async def check_all_health(self):  
        tasks = [self.check_health(p) for p in self.proxies]  
        if tasks:  
            await asyncio.gather(*tasks)  
  
    async def run_scraper(self):  
        if self.scraper_running:  
            return  
        self.scraper_running = True  
        logging.info("Starting proxy scraper...")  
          
        async with aiohttp.ClientSession() as session:  
            proxies = await ProxyScraper.scrape_all(session)  
            logging.info(f"Scraped {len(proxies)} proxies")  
              
            for p in proxies:  
                self.add_proxy(p, source="scraper")  
          
        # Validate scraped proxies  
        await self.check_all_health()  
        self.scraper_running = False  
        logging.info(f"Scraper finished. Total proxies: {len(self.proxies)}")  
  
class TikTokBot:  
    def __init__(self):  
        self.proxy_manager = ProxyManager()  
        self.stats = Stats()  
        self.session = None  
        self.is_running = False  
        self.auto_scraper_task = None  
        self.auto_tester_task = None  
        self.live_parser = TikTokLiveParser()  
  
    async def _get_session(self):  
        if not self.session:  
            self.session = aiohttp.ClientSession()  
        return self.session  
  
    async def start_campaign(self, room_id: str, views: int, delay: float):  
        self.stats.active_campaign = True  
        self.stats.current_room = room_id  
        self.stats.views_target = views  
        self.stats.views_remaining = views  
        self.stats.start_time = time.time()  
          
        session = await self._get_session()  
          
        for i in range(views):  
            if not self.is_running:  
                break  
              
            proxy = await self.proxy_manager.get_proxy()  
            if not proxy:  
                logging.warning("No healthy proxies, pausing campaign")  
                await asyncio.sleep(5)  
                continue  
  
            try:  
                # Simulate view send  
                await asyncio.sleep(delay)  
                self.stats.views_sent += 1  
                self.stats.views_remaining -= 1  
                  
                # Simulate 5% failure rate  
                if random.random() < 0.05:  
                    self.stats.views_failed += 1  
                    # Refresh proxy health on failure  
                    await self.proxy_manager.check_all_health()  
            except Exception as e:  
                logging.error(f"Campaign error: {e}")  
          
        self.stats.active_campaign = False  
        self.stats.current_room = ""  
  
    def stop_campaign(self):  
        self.is_running = False  
  
    def get_dashboard_data(self) -> dict:  
        progress = 0  
        if self.stats.views_target > 0:  
            progress = ((self.stats.views_target - self.stats.views_remaining) / self.stats.views_target) * 100  
          
        elapsed = time.time() - self.stats.start_time if self.stats.start_time else 1  
        vps = self.stats.views_sent / elapsed if elapsed > 0 else 0  
  
        return {  
            "proxies": [asdict(p) for p in self.proxy_manager.proxies],  
            "stats": {  
                **asdict(self.stats),  
                "progress": progress,  
                "vps": round(vps, 2)  
            },  
            "scraper_status": "Running" if self.proxy_manager.scraper_running else "Idle",  
            "tester_status": "Running" if self.proxy_manager.testing_running else "Idle"  
        }  
  
    async def test_all_proxies(self):  
        if self.proxy_manager.testing_running:  
            return  
        self.proxy_manager.testing_running = True  
        logging.info("Starting proxy health test...")  
        await self.proxy_manager.check_all_health()  
        self.proxy_manager.testing_running = False  
        logging.info("Proxy health test finished.")  
  
# --- 5. FastAPI Backend ---  
app = FastAPI()  
bot = TikTokBot()  
bot.is_running = True  
  
# Start auto-scraper  
async def auto_scraper():  
    while True:  
        await bot.proxy_manager.run_scraper()  
        await asyncio.sleep(600)  # Run every 10 minutes  
  
bot.auto_scraper_task = asyncio.create_task(auto_scraper())  
  
# Start auto-tester  
async def auto_tester():  
    while True:  
        await bot.test_all_proxies()  
        await asyncio.sleep(300)  # Run every 5 minutes  
  
bot.auto_tester_task = asyncio.create_task(auto_tester())  
  
@app.websocket("/ws")  
async def websocket_endpoint(websocket: WebSocket):  
    await websocket.accept()  
    try:  
        while True:  
            data = bot.get_dashboard_data()  
            await websocket.send_json(data)  
            await asyncio.sleep(2)  
    except WebSocketDisconnect:  
        pass  
  
@app.post("/proxies")  
async def add_proxy(proxy: dict):  
    url = proxy.get("url")  
    if not url:  
        raise HTTPException(400, "URL required")  
    bot.proxy_manager.add_proxy(url)  
    return {"status": "ok"}  
  
@app.delete("/proxies/{proxy_id}")  
async def remove_proxy(proxy_id: str):  
    bot.proxy_manager.remove_proxy(proxy_id)  
    return {"status": "ok"}  
  
@app.post("/proxies/check")  
async def check_proxies():  
    await bot.proxy_manager.check_all_health()  
    return {"status": "ok"}  
  
@app.post("/proxies/scrape")  
async def scrape_proxies():  
    if not bot.proxy_manager.scraper_running:  
        asyncio.create_task(bot.proxy_manager.run_scraper())  
        return {"status": "scraping_started"}  
    return {"status": "scraper_already_running"}  
  
@app.post("/campaign")  
async def start_campaign(data: dict):  
    room_id = data.get("room_id")  
    views = data.get("views", 100)  
    delay = data.get("delay", 0.5)  
      
    if not room_id:  
        raise HTTPException(400, "Room ID required")  
      
    asyncio.create_task(bot.start_campaign(room_id, views, delay))  
    return {"status": "started"}  
  
@app.post("/campaign/stop")  
async def stop_campaign():  
    bot.stop_campaign()  
    return {"status": "stopped"}  
  
@app.post("/live/parse")  
async def parse_live_url(data: dict):  
    url = data.get("url")  
    if not url:  
        raise HTTPException(400, "URL required")  
      
    target = await bot.live_parser.parse_live_url(url)  
    if target:  
        bot.stats.current_target = target  
        return {"status": "ok", "data": asdict(target)}  
    else:  
        return {"status": "error", "message": "Could not parse live URL"}  
  
@app.get("/dashboard")  
async def get_dashboard():  
    return HTMLResponse(content=open("templates/dashboard.html").read())  
  
# --- 6. Frontend (Enhanced HTML) ---  
dashboard_html = """  
<!DOCTYPE html>  
<html lang="en">  
<head>  
    <meta charset="UTF-8">  
    <meta name="viewport" content="width=device-width, initial-scale=1.0">  
    <title>TikTok Live Bot Dashboard</title>  
    <script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js"></script>  
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>  
    <style>  
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f0f0f; color: #fff; padding: 20px; margin: 0; }  
        .container { max-width: 1400px; margin: 0 auto; }  
        .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }  
        .card { background: #1a1a1a; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }  
        h1 { color: #00f2ea; text-align: center; margin-bottom: 30px; }  
        h2 { color: #fe2c55; border-bottom: 1px solid #333; padding-bottom: 10px; }  
        button { background: #fe2c55; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; transition: background 0.3s; }  
        button:hover { background: #e62046; }  
        button:disabled { background: #666; cursor: not-allowed; }  
        input { padding: 10px; border-radius: 8px; border: 1px solid #444; background: #2a2a2a; color: white; width: 70%; margin-right: 10px; }  
        input:focus { outline: none; border-color: #00f2ea; }  
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }  
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }  
        .healthy { color: #00ff00; font-weight: bold; }  
        .dead { color: #ff0000; font-weight: bold; }  
        .progress-bar { background: #333; height: 24px; border-radius: 12px; overflow: hidden; margin-top: 15px; position: relative; }  
        .progress { background: linear-gradient(90deg, #fe2c55, #00f2ea); height: 100%; transition: width 0.5s; }  
        .progress-text { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 12px; font-weight: bold; }  
        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: center; }  
        .stat-box { background: #252525; padding: 15px; border-radius: 8px; }  
        .stat-value { font-size: 24px; font-weight: bold; color: #00f2ea; }  
        .stat-label { font-size: 12px; color: #aaa; }  
        .scraper-status { padding: 5px 10px; border-radius: 4px; font-size: 12px; }  
        .scraper-running { background: #ff9800; color: #000; }  
        .scraper-idle { background: #4caf50; color: #fff; }  
        .tester-status { padding: 5px 10px; border-radius: 4px; font-size: 12px; }  
        .tester-running { background: #2196f3; color: #fff; }  
        .tester-idle { background: #9e9e9e; color: #fff; }  
        .live-target { background: #2a2a2a; padding: 15px; border-radius: 8px; margin-top: 10px; }  
        .live-target h3 { color: #00f2ea; margin-top: 0; }  
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }  
    </style>  
</head>  
<body>  
    <div id="app" class="container">  
        <h1>🎵 TikTok Live Bot Dashboard</h1>  
          
        <div class="grid">  
            <!-- Left Column: Stats & Controls -->  
            <div>  
                <!-- Stats Card -->  
                <div class="card">  
                    <h2>📊 Campaign Stats</h2>  
                    <div class="stats-grid">  
                        <div class="stat-box">  
                            <div class="stat-value">{{ stats.views_sent }}</div>  
                            <div class="stat-label">Views Sent</div>  
                        </div>  
                        <div class="stat-box">  
                            <div class="stat-value">{{ stats.views_failed }}</div>  
                            <div class="stat-label">Views Failed</div>  
                        </div>  
                        <div class="stat-box">  
                            <div class="stat-value">{{ stats.vps }}</div>  
                            <div class="stat-label">Views/sec</div>  
                        </div>  
                    </div>  
                      
                    <div style="margin-top: 20px;">  
                        <p>Target Room: <strong>{{ stats.current_room || 'None' }}</strong></p>  
                        <p>Remaining: <strong>{{ stats.views_remaining }}</strong> / {{ stats.views_target }}</p>  
                          
                        <div class="progress-bar">  
                            <div class="progress" :style="{ width: stats.progress + '%' }"></div>  
                            <div class="progress-text">{{ stats.progress.toFixed(1) }}%</div>  
                        </div>  
                    </div>  
                      
                    <div style="margin-top: 20px; text-align: center;">  
                        <button v-if="!stats.active_campaign" @click="startCampaign">🚀 Start Campaign</button>  
                        <button v-else @click="stopCampaign" style="background: #ff9800;">⏹ Stop Campaign</button>  
                    </div>  
                </div>  
  
                <!-- Chart Card -->  
                <div class="card">  
                    <h2>📈 Live Performance</h2>  
                    <canvas id="performanceChart" height="100"></canvas>  
                </div>  
            </div>  
  
            <!-- Right Column: Proxies & Live Target -->  
            <div>  
                <!-- Live Target Card -->  
                <div class="card">  
                    <h2>🎯 Live Target</h2>  
                    <div style="display: flex; gap: 10px; margin-bottom: 10px;">  
                        <input v-model="liveUrl" placeholder="Paste TikTok Live URL" @keyup.enter="parseLiveUrl">  
                        <button @click="parseLiveUrl">Parse</button>  
                    </div>  
                      
                    <div class="live-target" v-if="liveTarget.is_live">  
                        <h3>{{ liveTarget.title }}</h3>  
                        <p>Room ID: <code>{{ liveTarget.room_id }}</code></p>  
                        <p>Owner UID: <code>{{ liveTarget.owner_uid }}</code></p>  
                        <p>Status: <span class="healthy">🟢 LIVE</span></p>  
                        <button @click="setLiveTargetAsCampaign" style="margin-top: 10px;">🚀 Use as Target</button>  
                    </div>  
                    <div v-else>  
                        <p>Enter a live URL and click Parse to see details.</p>  
                    </div>  
                </div>  
  
                <!-- Proxy Health Card -->  
                <div class="card">  
                    <h2>🌐 Proxy Health</h2>  
                    <p>Healthy: <span class="healthy">{{ proxies.filter(p => p.health).length }}</span> / {{ proxies.length }}</p>  
                      
                    <div style="margin-bottom: 15px;">  
                        <button @click="checkAllHealth" :disabled="proxies.length === 0">🔄 Force Check</button>  
                        <button @click="scrapeProxies" :disabled="scraper_status === 'Running'">🕷 Scrape New</button>  
                        <span class="scraper-status" :class="scraper_status === 'Running' ? 'scraper-running' : 'scraper-idle'">  
                            {{ scraper_status }}  
                        </span>  
                        <span class="tester-status" :class="tester_status === 'Running' ? 'tester-running' : 'tester-idle'">  
                            {{ tester_status }}  
                        </span>  
                    </div>  
  
                    <div style="max-height: 300px; overflow-y: auto;">  
                        <table>  
                            <tr>  
                                <th>Proxy</th>  
                                <th>Status</th>  
                                <th>Fails</th>  
                                <th>Action</th>  
                            </tr>  
                            <tr v-for="p in proxies">  
                                <td title="{{ p.url }}">{{ truncateUrl(p.url) }}</td>  
                                <td :class="p.health ? 'healthy' : 'dead'">{{ p.health ? '🟢' : '🔴' }}</td>  
                                <td>{{ p.fail_count }}</td>  
                                <td>  
                                    <button @click="removeProxy(p.id)" style="padding: 5px 10px; font-size: 12px;">❌</button>  
                                </td>  
                            </tr>  
                        </table>  
                    </div>  
                </div>  
  
                <!-- Add Proxy Form -->  
                <div class="card">  
                    <h2>➕ Add Proxy</h2>  
                    <div style="display: flex; gap: 10px; margin-bottom: 10px;">  
                        <input v-model="newProxy" placeholder="http://user:pass@host:port" @keyup.enter="addProxy">  
                        <button @click="addProxy">Add</button>  
                    </div>  
                </div>  
            </div>  
        </div>  
  
        <!-- Campaign Form (Modal-like) -->  
        <div class="card" style="position: relative;">  
            <h2>🎯 Quick Start Campaign</h2>  
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">  
                <input v-model="roomId" placeholder="Room ID" style="flex: 2;">  
                <input v-model.number="views" type="number" placeholder="Views" style="flex: 1;">  
                <input v-model.number="delay" type="number" placeholder="Delay (sec)" style="flex: 1;">  
                <button @click="startCampaign" style="flex: 1;">Go</button>  
            </div>  
        </div>  
    </div>  
  
    <script>  
        const { createApp } = Vue;  
        createApp({  
            data() {  
                return {  
                    stats: { views_sent: 0, views_failed: 0, active_campaign: false, current_room: "", views_target: 0, views_remaining: 0, progress: 0, vps: 0, current_target: { is_live: false } },  
                    proxies: [],  
                    scraper_status: "Idle",  
                    tester_status: "Idle",  
                    newProxy: '',  
                    roomId: '',  
                    views: 100,  
                    delay: 0.5,  
                    liveUrl: '',  
                    liveTarget: { is_live: false, room_id: '', owner_uid: '', title: '' },  
                    chart: null,  
                    chartData: {  
                        labels: [],  
                        viewsSent: [],  
                        viewsFailed: []  
                    }  
                }  
            },  
            created() {  
                this.connectWebSocket();  
                this.initChart();  
            },  
            methods: {  
                connectWebSocket() {  
                    const ws = new WebSocket('ws://' + window.location.host + '/ws');  
                    ws.onmessage = (event) => {  
                        const data = JSON.parse(event.data);  
                        this.stats = data.stats;  
                        this.proxies = data.proxies;  
                        this.scraper_status = data.scraper_status;  
                        this.tester_status = data.tester_status;  
                          
                        // Update chart  
                        this.updateChart();  
                    };  
                },  
                initChart() {  
                    const ctx = document.getElementById('performanceChart').getContext('2d');  
                    this.chart = new Chart(ctx, {  
                        type: 'line',  
                        data: {  
                            labels: [],  
                            datasets: [  
                                {  
                                    label: 'Views Sent',  
                                    data: [],  
                                    borderColor: '#00f2ea',  
                                    backgroundColor: 'rgba(0, 242, 234, 0.1)',  
                                    fill: true,  
                                    tension: 0.4  
                                },  
                                {  
                                    label: 'Views Failed',  
                                    data: [],  
                                    borderColor: '#ff0000',  
                                    backgroundColor: 'rgba(255, 0, 0, 0.1)',  
                                    fill: true,  
                                    tension: 0.4  
                                }  
                            ]  
                        },  
                        options: {  
                            responsive: true,  
                            plugins: {  
                                legend: { labels: { color: '#fff' } }  
                            },  
                            scales: {  
                                x: { ticks: { color: '#aaa' }, grid: { color: '#333' } },  
                                y: { ticks: { color: '#aaa' }, grid: { color: '#333' } }  
                            },  
                            animation: { duration: 0 }  
                        }  
                    });  
                },  
                updateChart() {  
                    const now = new Date().toLocaleTimeString();  
                    this.chartData.labels.push(now);  
                    this.chartData.viewsSent.push(this.stats.views_sent);  
                    this.chartData.viewsFailed.push(this.stats.views_failed);  
                      
                    // Keep only last 20 points  
                    if (this.chartData.labels.length > 20) {  
                        this.chartData.labels.shift();  
                        this.chartData.viewsSent.shift();  
                        this.chartData.viewsFailed.shift();  
                    }  
                      
                    this.chart.data.labels = this.chartData.labels;  
                    this.chart.data.datasets[0].data = this.chartData.viewsSent;  
                    this.chart.data.datasets[1].data = this.chartData.viewsFailed;  
                    this.chart.update();  
                },  
                addProxy() {  
                    fetch('/proxies', {  
                        method: 'POST',  
                        headers: {'Content-Type': 'application/json'},  
                        body: JSON.stringify({url: this.newProxy})  
                    }).then(() => this.newProxy = '');  
                },  
                removeProxy(id) {  
                    fetch('/proxies/' + id, {method: 'DELETE'});  
                },  
                checkAllHealth() {  
                    fetch('/proxies/check', {method: 'POST'});  
                },  
                scrapeProxies() {  
                    fetch('/proxies/scrape', {method: 'POST'});  
                },  
                parseLiveUrl() {  
                    fetch('/live/parse', {  
                        method: 'POST',  
                        headers: {'Content-Type': 'application/json'},  
                        body: JSON.stringify({url: this.liveUrl})  
                    }).then(response => response.json())  
                    .then(data => {  
                        if (data.status === 'ok') {  
                            this.liveTarget = data.data;  
                        } else {  
                            alert('Could not parse URL');  
                        }  
                    });  
                },  
                setLiveTargetAsCampaign() {  
                    this.roomId = this.liveTarget.room_id;  
                    this.delay = 0.5; // Default delay  
                },  
                startCampaign() {  
                    if (!this.roomId) {  
                        alert("Please enter a Room ID");  
                        return;  
                    }  
                    fetch('/campaign', {  
                        method: 'POST',  
                        headers: {'Content-Type': 'application/json'},  
                        body: JSON.stringify({room_id: this.roomId, views: this.views, delay: this.delay})  
                    });  
                },  
                stopCampaign() {  
                    fetch('/campaign/stop', {method: 'POST'});  
                },  
                truncateUrl(url) {  
                    return url.length > 20 ? url.substring(0, 17) + '...' : url;  
                }  
            }  
        }).mount('#app');  
    </script>  
</body>  
</html>  
"""  
  
# Write the HTML to a file so FastAPI can serve it  
os.makedirs("templates", exist_ok=True)  
with open("templates/dashboard.html", "w") as f:  
    f.write(dashboard_html)  
  
# --- 7. Run ---  
if __name__ == "__main__":  
    uvicorn.run(app, host="0.0.0.0", port=8000)  
