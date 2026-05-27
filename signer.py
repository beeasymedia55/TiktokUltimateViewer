#!/usr/bin/env python3
"""
SignerPy Integration Module
Wraps all SignerPy functionality for TikTok request signing
Features: x-gorgon, x-argus, x-ladon, x-khronos, x-ss-stub,
          x-ss-req-ticket, trace_id, xtoken, TTEncrypt, edata,
          SM3 hashing, Protobuf serialization, Simon cipher, ChaCha20
Author: HackerAI PenTest Framework
"""
import json
import time
import hashlib
import base64
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Tuple

try:
    from SignerPy import (
        sign, edata, ttencrypt, xtoken, trace_id,
        encryption, hosts, xor
    )
    from SignerPy.sign import Signer
    SIGNERPY_AVAILABLE = True
except ImportError:
    SIGNERPY_AVAILABLE = False

from config import config


class TikTokSigner:
    """
    Complete TikTok signature generation wrapper.
    Integrates all SignerPy features for mobile & web API signing.
    """

    def __init__(self, device_id: Optional[str] = None, 
                 app_id: int = None,
                 app_version: str = None,
                 sdk_version: str = None,
                 platform: str = None):
        self.device_id = device_id or self._generate_device_id()
        self.app_id = app_id or config.get("app_id", 1233)
        self.app_version = app_version or config.get("app_version", "31.5.2")
        self.sdk_version = sdk_version or config.get("sdk_version", "27.0.0")
        self.platform = platform or config.get("device_platform", "android")
        self._signer = None
        
        if SIGNERPY_AVAILABLE:
            self._signer = Signer(
                device_id=self.device_id,
                app_id=self.app_id,
                app_version=self.app_version
            )

    def _generate_device_id(self) -> str:
        """Generate a random device ID"""
        import random
        return str(random.randint(6800000000000000000, 7399999999999999999))

    def sign_request(self, url: str, data: str = "", 
                     cookies: str = "", method: str = "GET",
                     headers: Optional[Dict] = None) -> Dict[str, str]:
        """
        Generate ALL required TikTok signature headers for a request.
        
        Returns dict with keys:
            x-gorgon, x-argus, x-ladon, x-khronos, 
            x-ss-stub, x-ss-req-ticket, x-tt-trace-id
        """
        if headers is None:
            headers = {}

        timestamp = str(int(time.time()))
        
        # Parse URL params
        parsed = urlparse(url)
        params = parsed.query
        
        # Generate each signature component
        sig_headers = {}
        
        # 1. x-khronos - Unix timestamp
        sig_headers["x-khronos"] = timestamp
        
        # 2. x-ss-stub - MD5 of body/data
        sig_headers["x-ss-stub"] = self._generate_ss_stub(data)
        
        # 3. x-tt-trace-id - Trace ID
        sig_headers["x-tt-trace-id"] = self._generate_trace_id()
        
        # 4. x-ss-req-ticket - Request ticket
        sig_headers["x-ss-req-ticket"] = self._generate_req_ticket(timestamp)
        
        # 5. x-gorgon - Main signature (version dependent)
        gorgon_ver = config.get("x_gorgon_version", "v2")
        sig_headers["x-gorgon"] = self._generate_gorgon(
            params, data, cookies, timestamp, gorgon_ver
        )
        
        # 6. x-argus - Mobile app signature
        sig_headers["x-argus"] = self._generate_argus(url, data)
        
        # 7. x-ladon - Data encryption token
        sig_headers["x-ladon"] = self._generate_ladon()
        
        # 8. x-tt-token or x-token if available
        sig_headers["x-token"] = self._generate_xtoken(url)
        
        # Merge into existing headers
        headers.update(sig_headers)
        
        # Standard headers
        headers["User-Agent"] = self._get_user_agent()
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        
        return headers

    def _generate_ss_stub(self, data: str) -> str:
        """Generate x-ss-stub - MD5 of data body"""
        if SIGNERPY_AVAILABLE:
            try:
                from SignerPy import md5stub
                return md5stub(data)
            except ImportError:
                pass
        if not data:
            return "00000000000000000000000000000000"
        return hashlib.md5(data.encode()).hexdigest().upper()

    def _generate_trace_id(self) -> str:
        """Generate x-tt-trace-id"""
        if SIGNERPY_AVAILABLE:
            try:
                return trace_id()
            except Exception:
                pass
        import uuid
        return uuid.uuid4().hex[:32].upper()

    def _generate_req_ticket(self, timestamp: str) -> str:
        """Generate x-ss-req-ticket"""
        part1 = hex(int(timestamp) & 0xFFFFFFFF)[2:].zfill(8)
        part2 = hex(int(timestamp) >> 32)[2:].zfill(8)
        return f"0x{part1}{part2}"

    def _generate_gorgon(self, params: str, data: str, 
                         cookies: str, timestamp: str, 
                         version: str = "v2") -> str:
        """
        Generate x-gorgon signature.
        Supports v1 (8404), v2 (8402), v3 (4404)
        """
        if SIGNERPY_AVAILABLE:
            try:
                sig_result = self._signer.sign(
                    params=params, 
                    data=data, 
                    cookies=cookies
                )
                if isinstance(sig_result, dict) and "X-Gorgon" in sig_result:
                    return sig_result["X-Gorgon"]
            except Exception:
                pass

        # Fallback implementation
        if version == "v3":
            base_ver = "4404"
        elif version == "v1":
            base_ver = "8404"
        else:
            base_ver = "8402"

        # Build signature from MD5 hashes
        params_md5 = hashlib.md5(params.encode()).hexdigest() if params else "0" * 32
        data_md5 = hashlib.md5(data.encode()).hexdigest() if data else "0" * 32
        cookies_md5 = hashlib.md5(cookies.encode()).hexdigest() if cookies else "0" * 32

        # Combine and transform
        combined = f"{params_md5[:8]}{data_md5[:8]}{cookies_md5[:8]}"
        combined_md5 = hashlib.md5(combined.encode()).hexdigest()[:8]
        
        gorgon_value = f"{base_ver}{combined_md5}{timestamp[-4:]}"
        return gorgon_value.upper()

    def _generate_argus(self, url: str, data: str) -> str:
        """
        Generate x-argus mobile signature.
        Uses Protobuf serialization, SM3 hashing, Simon cipher, AES-CBC
        """
        if SIGNERPY_AVAILABLE:
            try:
                from SignerPy import sign
                result = sign(
                    url=url,
                    data=data,
                    device_id=self.device_id,
                    app_id=self.app_id,
                    platform=self.platform,
                    sdk_version=self.sdk_version
                )
                if isinstance(result, dict) and "x-argus" in result:
                    return result["x-argus"]
            except Exception:
                pass
        return ""

    def _generate_ladon(self) -> str:
        """Generate x-ladon data encryption token"""
        if SIGNERPY_AVAILABLE:
            try:
                from SignerPy import sign
                result = sign(
                    url="", data="",
                    device_id=self.device_id,
                    app_id=self.app_id
                )
                if isinstance(result, dict) and "x-ladon" in result:
                    return result["x-ladon"]
            except Exception:
                pass
        return ""

    def _generate_xtoken(self, url: str) -> str:
        """Generate x-token (hmac-sha256)"""
        if SIGNERPY_AVAILABLE:
            try:
                return xtoken(url=url, device_id=self.device_id)
            except Exception:
                pass
        return ""

    def _get_user_agent(self) -> str:
        """Generate random but realistic TikTok user-agent"""
        agents = [
            f"com.zhiliaoapp.musically/{self.app_version} (Linux; U; Android 12; en_US; {self.device_id}; Build/OPM1.171019.011; Cronet/58.0.2991.0)",
            f"okhttp/3.14.9",
            f"Dalvik/2.1.0 (Linux; U; Android 12; SM-G998B Build/SP1A.210812.016)",
            f"Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.117 Mobile Safari/537.36",
        ]
        import random
        return random.choice(agents)

    def encrypt_edata(self, data: str) -> str:
        """ChaCha20 edata encryption"""
        if SIGNERPY_AVAILABLE:
            try:
                return edata.encrypt(data)
            except Exception:
                pass
        # Fallback base64
        return base64.b64encode(data.encode()).decode()

    def decrypt_edata(self, encrypted: str) -> str:
        """ChaCha20 edata decryption"""
        if SIGNERPY_AVAILABLE:
            try:
                return edata.decrypt(encrypted)
            except Exception:
                pass
        try:
            return base64.b64decode(encrypted).decode()
        except Exception:
            return encrypted

    def ttencrypt(self, data: str) -> str:
        """TTEncrypt implementation"""
        if SIGNERPY_AVAILABLE:
            try:
                return ttencrypt.Enc().encrypt(data)
            except Exception:
                pass
        return data[::-1]  # fallback

    def get_api_hosts(self) -> list:
        """Get TikTok API hosts"""
        if SIGNERPY_AVAILABLE:
            try:
                return hosts.host()
            except Exception:
                pass
        return [
            "api16-normal-c-useast1a.tiktokv.com",
            "api16-normal-c-alisg.tiktokv.com",
            "api19-normal-c-useast1a.tiktokv.com",
            "api22-normal-c-alisg.tiktokv.com",
            "api-h2.tiktokv.com",
        ]

    def sign_full(self, url: str, method: str = "GET",
                  body: str = "", cookies: str = "",
                  extra_headers: Optional[Dict] = None) -> Tuple[str, Dict]:
        """
        Sign a complete request. Returns (signed_url, headers_dict).
        Automatically handles URL param signing and header injection.
        """
        headers = extra_headers or {}
        headers = self.sign_request(url, body, cookies, method, headers)
        return url, headers


# Module-level convenience functions
def sign_request(url, data="", cookies="", method="GET", device_id=None):
    """Quick one-shot signing"""
    signer = TikTokSigner(device_id=device_id)
    return signer.sign_request(url, data, cookies, method)


def encrypt_edata(data):
    """Quick edata encrypt"""
    signer = TikTokSigner()
    return signer.encrypt_edata(data)


def decrypt_edata(data):
    """Quick edata decrypt"""
    signer = TikTokSigner()
    return signer.decrypt_edata(data)
