#!/usr/bin/env python3
"""
TikTok Account Generator
Generates accounts with associated session and device files.
Each account gets: username, email, password, device_id, session_token
Author: HackerAI PenTest Framework
"""
import os
import sys
import json
import random
import string
import hashlib
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))
from config import config, ACCOUNTS_DIR, SESSIONS_DIR, DEVICES_DIR


class AccountGenerator:
    """Generate TikTok accounts with full device profiles"""

    # TikTok-like username patterns
    USERNAME_PREFIXES = [
        "user", "tiktok", "viral", "trend", "dance", "music", "fun",
        "cool", "best", "top", "real", "pro", "max", "super", "mega",
        "lite", "nova", "star", "zone", "hub", "wave", "flow", "rush"
    ]
    
    USERNAME_SUFFIXES = [
        "2024", "2025", "2026", "official", "page", "live", "stream",
        "clips", "vids", "reels", "daily", "hour", "fresh", "new"
    ]

    # Realistic email domains
    EMAIL_DOMAINS = [
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
        "protonmail.com", "mail.com", "yandex.com", "aol.com",
        "icloud.com", "zoho.com", "tutanota.com", "gmx.com"
    ]

    # Device profiles (realistic TikTok device fingerprints)
    DEVICE_PROFILES = [
        {
            "platform": "android",
            "os_version": "13",
            "device_brand": "Samsung",
            "device_model": "SM-S918B",  # Galaxy S23 Ultra
            "device_type": "SM-S918B",
            "device_manufacturer": "samsung",
            "resolution": "1440x3088",
            "density_dpi": 500,
            "device_language": "en",
            "device_region": "US",
            "display_name": "Samsung Galaxy S23 Ultra"
        },
        {
            "platform": "android",
            "os_version": "12",
            "device_brand": "Google",
            "device_model": "Pixel 7 Pro",
            "device_type": "Pixel 7 Pro",
            "device_manufacturer": "Google",
            "resolution": "1440x3120",
            "density_dpi": 512,
            "device_language": "en",
            "device_region": "US",
            "display_name": "Google Pixel 7 Pro"
        },
        {
            "platform": "android",
            "os_version": "14",
            "device_brand": "Xiaomi",
            "device_model": "Xiaomi14",
            "device_type": "Xiaomi14",
            "device_manufacturer": "Xiaomi",
            "resolution": "1440x3200",
            "density_dpi": 522,
            "device_language": "en",
            "device_region": "US",
            "display_name": "Xiaomi 14"
        },
        {
            "platform": "android",
            "os_version": "13",
            "device_brand": "OnePlus",
            "device_model": "OnePlus 11",
            "device_type": "OnePlus 11",
            "device_manufacturer": "OnePlus",
            "resolution": "1440x3216",
            "density_dpi": 525,
            "device_language": "en",
            "device_region": "US",
            "display_name": "OnePlus 11"
        },
        {
            "platform": "android",
            "os_version": "12",
            "device_brand": "OPPO",
            "device_model": "CPH2305",
            "device_type": "CPH2305",
            "device_manufacturer": "OPPO",
            "resolution": "1080x2400",
            "density_dpi": 480,
            "device_language": "en",
            "device_region": "US",
            "display_name": "OPPO Find X5"
        }
    ]

    def __init__(self, accounts_dir: str = None, sessions_dir: str = None, 
                 devices_dir: str = None):
        self.accounts_dir = Path(accounts_dir or config.get("accounts_path", "accounts"))
        self.sessions_dir = Path(sessions_dir or config.get("sessions_path", "sessions"))
        self.devices_dir = Path(devices_dir or config.get("devices_path", "devices"))
        
        for d in [self.accounts_dir, self.sessions_dir, self.devices_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _random_str(self, length: int = 8, chars: str = string.ascii_lowercase + string.digits) -> str:
        """Generate random string"""
        return ''.join(random.choice(chars) for _ in range(length))

    def _generate_username(self) -> str:
        """Generate realistic TikTok username"""
        pattern = random.choice([
            lambda: f"{random.choice(self.USERNAME_PREFIXES)}_{self._random_str(4)}",
            lambda: f"{random.choice(self.USERNAME_PREFIXES)}{random.randint(100, 9999)}",
            lambda: f"{self._random_str(6)}{random.randint(10, 99)}",
            lambda: f"{random.choice(self.USERNAME_PREFIXES)}.{random.choice(self.USERNAME_SUFFIXES)}",
            lambda: f"{random.choice(self.USERNAME_PREFIXES)}{random.choice(self.USERNAME_SUFFIXES)}{random.randint(1, 999)}",
        ])
        return pattern()

    def _generate_email(self, username: str) -> str:
        """Generate email from username"""
        domain = random.choice(self.EMAIL_DOMAINS)
        separator = random.choice(['', '.', '_', '-'])
        prefix = f"{username}{separator}{self._random_str(3)}"
        return f"{prefix}@{domain}"

    def _generate_password(self, length: int = 16) -> str:
        """Generate strong password"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choice(chars) for _ in range(length))

    def _generate_device_id(self) -> str:
        """Generate TikTok device ID"""
        return str(random.randint(6800000000000000000, 7399999999999999999))

    def _generate_session_token(self) -> str:
        """Generate session token"""
        return hashlib.sha256(str(random.getrandbits(256)).encode()).hexdigest()

    def _generate_cookie(self, session_token: str) -> str:
        """Generate realistic cookie string"""
        cookies = [
            f"sessionid={session_token}",
            f"uid_to=_{self._random_str(16)}",
            f"guest_id=v1%3A{int(time.time())}",
            f"store-country-code=us",
            f"store-country-code-src=ust",
        ]
        return "; ".join(cookies)

    def generate_account(self, count: int = 1, prefix: str = "") -> List[Dict]:
        """Generate specified number of accounts"""
        accounts = []
        
        for i in range(count):
            username = self._generate_username()
            if prefix:
                username = f"{prefix}_{username}"
            
            email = self._generate_email(username)
            password = self._generate_password()
            device_id = self._generate_device_id()
            session_token = self._generate_session_token()
            
            # Pick a device profile
            device_profile = random.choice(self.DEVICE_PROFILES).copy()
            device_profile["device_id"] = device_id
            device_profile["device_id_str"] = device_id
            
            account = {
                "username": username,
                "email": email,
                "password": password,
                "device_id": device_id,
                "session_token": session_token,
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "proxy": None,
                "total_views": 0,
                "last_used": None,
            }
            
            # Save account file
            account_file = self.accounts_dir / f"{username}.json"
            with open(account_file, 'w') as f:
                json.dump(account, f, indent=4)
            
            # Save session file
            session_data = {
                "username": username,
                "device_id": device_id,
                "session_token": session_token,
                "cookie": self._generate_cookie(session_token),
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            }
            session_file = self.sessions_dir / f"{username}_session.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=4)
            
            # Save device file
            device_file = self.devices_dir / f"{device_id}_device.json"
            with open(device_file, 'w') as f:
                json.dump(device_profile, f, indent=4)
            
            accounts.append(account)
            print(f"  [✓] Generated account {i+1}/{count}: {username}")
        
        return accounts

    def load_accounts(self) -> List[Dict]:
        """Load all accounts from accounts directory"""
        accounts = []
        if self.accounts_dir.exists():
            for f in sorted(self.accounts_dir.glob("*.json")):
                try:
                    with open(f, 'r') as fh:
                        accounts.append(json.load(fh))
                except Exception as e:
                    print(f"  [!] Failed to load {f.name}: {e}")
        return accounts

    def load_sessions(self) -> Dict[str, Dict]:
        """Load all sessions keyed by username"""
        sessions = {}
        if self.sessions_dir.exists():
            for f in self.sessions_dir.glob("*_session.json"):
                try:
                    with open(f, 'r') as fh:
                        session = json.load(fh)
                        sessions[session.get("username", f.stem)] = session
                except Exception:
                    pass
        return sessions

    def load_devices(self) -> Dict[str, Dict]:
        """Load all devices keyed by device_id"""
        devices = {}
        if self.devices_dir.exists():
            for f in self.devices_dir.glob("*_device.json"):
                try:
                    with open(f, 'r') as fh:
                        device = json.load(fh)
                        devices[device.get("device_id", f.stem)] = device
                except Exception:
                    pass
        return devices

    def get_account_count(self) -> int:
        """Get total account count"""
        return len(list(self.accounts_dir.glob("*.json"))) if self.accounts_dir.exists() else 0


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TikTok Account Generator")
    parser.add_argument("-n", "--count", type=int, default=10, help="Number of accounts to generate")
    parser.add_argument("-p", "--prefix", type=str, default="", help="Username prefix")
    parser.add_argument("--accounts-dir", type=str, default=None, help="Accounts directory path")
    parser.add_argument("--sessions-dir", type=str, default=None, help="Sessions directory path")
    parser.add_argument("--devices-dir", type=str, default=None, help="Devices directory path")
    parser.add_argument("--list", action="store_true", help="List existing accounts")
    
    args = parser.parse_args()
    
    gen = AccountGenerator(args.accounts_dir, args.sessions_dir, args.devices_dir)
    
    if args.list:
        accounts = gen.load_accounts()
        print(f"\n  [*] Loaded {len(accounts)} accounts:\n")
        for a in accounts:
            print(f"      - {a['username']:20s} | device: {a['device_id']} | views: {a.get('total_views', 0)}")
        return
    
    print(f"\n  [*] Generating {args.count} accounts...\n")
    accounts = gen.generate_account(args.count, args.prefix)
    print(f"\n  [✓] Generated {len(accounts)} accounts successfully!")
    print(f"      Accounts: {gen.accounts_dir}")
    print(f"      Sessions: {gen.sessions_dir}")
    print(f"      Devices:  {gen.devices_dir}")


if __name__ == "__main__":
    main()
