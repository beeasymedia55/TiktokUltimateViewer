import asyncio  
import os  
import random  
import time  
import requests  
import logging  
import threading  
import uvicorn  
from typing import Optional  
from fastapi import FastAPI, HTTPException  
from pydantic import BaseModel  
from contextlib import asynccontextmanager  
import aiohttp  
from bs4 import BeautifulSoup  
import json  
import hashlib  
import base64  
import urllib.parse  
from urllib.parse import urlencode  
import uuid  
  
# Configure logging  
logging.basicConfig(  
    level=logging.INFO,  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'  
)  
logger = logging.getLogger(__name__)  
  
# Constants  
VERSIONS = ["270204", "260104", "250904", "250702", "250402"]  
DOMAINS = ["api-h2.tiktokv.com", "api22-core-c-useast1a.tiktokv.com", "api16-core-c-useast1a.tiktokv.com"]  
HEADERS_TEMPLATE = {  
    'User-Agent': 'com.zhiliaoapp.musically/2022607030 (Linux; U; Android 9; en_US; Pixel 2; Build/PPR1.180610.009;),okhttp/3.14.9',  
    'Accept': 'application/json',  
    'Accept-Language': 'en-US,en;q=0.9',  
    'X-Argus': '',  
    'X-Ladon': '',  
    'X-Gorgon': '',  
    'X-Khronos': '',  
    'X-SS-STUB': '',  
    'X-TC-Wrap': '',  
    'X-TT-REGION': 'us',  
    'X-Tt-Internal-Req': '0',  
    'X-TT-Timestamp': '0',  
    'X-TT-Req-Url': 'Bytes',  
    'X-TT-Req-Url-Extra': 'Bytes',  
    'X-SS-Request-Key': 'true',  
    'X-Ve-Log-Info-As': "some-logs",  
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',  
    'Host': 'api-h2.tiktokv.com',  
    'Connection': 'Keep-Alive',  
    'Accept-Encoding': 'gzip'  
}  
  
class TikTokBotConfig(BaseModel):  
    target: int = 1000  
    threads: int = 50  
    delay_min: float = 0.5  
    delay_max: float = 1.5  
    room_id: Optional[str] = None  
    device_ids: list = None  
  
class TikTokBot:  
    def __init__(self, config: TikTokBotConfig):  
        self.config = config  
        self.running = True  
        self.stats = {  
            'success': 0,  
            'fails': 0,  
            'active': 0,  
            'total': 0  
        }  
        self.lock = asyncio.Lock()  
        self.auto_scraper_task = None  
        self.auto_tester_task = None  
          
        # Device pool  
        self.device_ids = self._generate_device_pool()  
          
    def _generate_device_pool(self):  
        devices = []  
        for _ in range(100):  
            did = hashlib.md5(str(random.random()).encode()).hexdigest()[:16]  
            iid = hashlib.md5(str(random.random()).encode()).hexdigest()[:16]  
            cdid = str(uuid.uuid4())  
            openudid = hashlib.md5(str(random.random()).encode()).hexdigest()[:32]  
            devices.append(f"{did}:{iid}:{cdid}:{openudid}")  
        return devices  
  
    def _get_headers(self, method, url, params, device):  
        did, iid, cdid, openudid = device.split(':')  
        headers = HEADERS_TEMPLATE.copy()  
        headers['X-Argus'] = self._generate_argus(method, url, params)  
        headers['X-Ladon'] = self._generate_ladon()  
        headers['X-Gorgon'] = self._generate_gorgon(method, url, params)  
        headers['X-Khronos'] = str(int(time.time()))  
        headers['X-SS-STUB'] = self._generate_stub()  
        headers['X-TT-Timestamp'] = str(int(time.time()))  
        headers['Host'] = random.choice(DOMAINS).replace('https://', '')  
        return headers  
  
    def _generate_argus(self, method, url, params):  
        # Simplified Argus generation  
        return base64.b64encode(hashlib.md5(f"{method}{url}{params}".encode()).digest()).decode()  
  
    def _generate_ladon(self):  
        return base64.b64encode(hashlib.md5(str(time.time()).encode()).digest()).decode()  
  
    def _generate_gorgon(self, method, url, params):  
        return base64.b64encode(hashlib.md5(f"{method}{url}{params}".encode()).digest()).decode()  
  
    def _generate_stub(self):  
        return base64.b64encode(hashlib.md5(str(time.time()).encode()).digest()).decode()  
  
    async def send_live_views(self, device):  
        async with self.lock:  
            self.stats['active'] += 1  
            self.stats['total'] += 1  
              
        try:  
            did, iid, cdid, openudid = device.split(':')  
            headers = self._get_headers('POST', '/aweme/v1/play/aweme/', '', device)  
              
            payload = {  
                'aweme_id': self.config.room_id,  
                'iid': iid,  
                'device_id': did,  
                'cdid': cdid,  
                'openudid': openudid,  
                'version_code': random.choice(VERSIONS),  
                'channel': 'googleplay',  
                'app_name': 'musical_ly',  
                'device_platform': 'android',  
                'device_type': 'Pixel 2',  
                'ssmix': 'a',  
                'aid': '1233',  
                'app_type': 'normal',  
                'update_version_code': '270204',  
                'ac': 'wifi',  
                'channel_id': 'googleplay',  
                'cpu_core_num': '4',  
                'is_my_cn': 'false',  
                'aid': '1233',  
                'mcc_mnc': '310260',  
                'os_api': '28',  
                'os_version': '9',  
                'ac2': 'wifi',  
                'uoo': '1',  
                'op': 'nfc',  
                'ntlist': '768',  
                'vvt': '4',  
                'cdid': cdid,  
                'openudid': openudid,  
                'device_id': did,  
                'iid': iid  
            }  
              
            async with aiohttp.ClientSession() as session:  
                async with session.post(  
                    f"https://{random.choice(DOMAINS)}/aweme/v1/play/aweme/",  
                    headers=headers,  
                    data=payload,  
                    ssl=False,  
                    timeout=aiohttp.ClientTimeout(total=10)  
                ) as response:  
                    if response.status == 200:  
                        async with self.lock:  
                            self.stats['success'] += 1  
                    else:  
                        async with self.lock:  
                            self.stats['fails'] += 1  
        except Exception as e:  
            logger.error(f"Error sending views: {e}")  
            async with self.lock:  
                self.stats['fails'] += 1  
        finally:  
            async with self.lock:  
                self.stats['active'] -= 1  
  
    async def auto_scraper(self):  
        logger.info("Auto scraper started")  
        while self.running:  
            try:  
                # Scrape logic here  
                await asyncio.sleep(60)  
            except Exception as e:  
                logger.error(f"Scraper error: {e}")  
                await asyncio.sleep(5)  
  
    async def auto_tester(self):  
        logger.info("Auto tester started")  
        while self.running:  
            try:  
                # Tester logic here  
                await asyncio.sleep(30)  
            except Exception as e:  
                logger.error(f"Tester error: {e}")  
                await asyncio.sleep(5)  
  
    async def start_bot(self):  
        logger.info("Starting TikTok bot")  
        self.running = True  
        import concurrent.futures  
          
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.threads) as executor:  
            futures = []  
            while self.running and self.stats['success'] < self.config.target:  
                device = random.choice(self.device_ids)  
                future = executor.submit(asyncio.run, self.send_live_views(device))  
                futures.append(future)  
                  
                if len(futures) >= self.config.threads:  
                    done, _ = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)  
                    for future in done:  
                        try:  
                            future.result()  
                        except Exception as e:  
                            logger.error(f"Thread error: {e}")  
                        futures.remove(future)  
                      
                    await asyncio.sleep(random.uniform(self.config.delay_min, self.config.delay_max))  
              
            # Wait for remaining threads  
            concurrent.futures.wait(futures)  
            logger.info("Bot stopped")  
  
    def get_stats(self):  
        return self.stats  
  
@asynccontextmanager  
async def lifespan(app: FastAPI):  
    # Startup  
    config = TikTokBotConfig()  
    bot = TikTokBot(config)  
    app.state.bot = bot  
      
    bot.auto_scraper_task = asyncio.create_task(bot.auto_scraper())  
    bot.auto_tester_task = asyncio.create_task(bot.auto_tester())  
      
    # Start the bot in a separate thread  
    bot_thread = threading.Thread(target=asyncio.run, args=(bot.start_bot(),))  
    bot_thread.start()  
      
    yield  
      
    # Shutdown  
    bot.running = False  
    if bot.auto_scraper_task:  
        bot.auto_scraper_task.cancel()  
    if bot.auto_tester_task:  
        bot.auto_tester_task.cancel()  
  
app = FastAPI(lifespan=lifespan)  
  
@app.get("/stats")  
def get_stats():  
    if not hasattr(app.state, 'bot'):  
        raise HTTPException(status_code=503, detail="Bot not initialized")  
    return app.state.bot.get_stats()  
  
@app.post("/start")  
def start_bot():  
    if not hasattr(app.state, 'bot'):  
        raise HTTPException(status_code=503, detail="Bot not initialized")  
    app.state.bot.running = True  
    return {"status": "Bot started"}  
  
@app.post("/stop")  
def stop_bot():  
    if not hasattr(app.state, 'bot'):  
        raise HTTPException(status_code=503, detail="Bot not initialized")  
    app.state.bot.running = False  
    return {"status": "Bot stopped"}  
  
@app.get("/health")  
def health_check():  
    return {"status": "ok"}  
  
if __name__ == "__main__":  
    uvicorn.run(app, host="0.0.0.0", port=8000)  
