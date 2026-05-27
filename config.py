#!/usr/bin/env python3
"""
TikTok Bot - Configuration Module
Author: HackerAI PenTest Framework
"""
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Paths - all changeable
ACCOUNTS_DIR = BASE_DIR / "accounts"
SESSIONS_DIR = BASE_DIR / "sessions"
DEVICES_DIR = BASE_DIR / "devices"
PROXIES_FILE = BASE_DIR / "proxies.txt"
WORKING_PROXIES_FILE = BASE_DIR / "working_proxies.txt"
CONFIG_FILE = BASE_DIR / "config.json"

# Ensure directories exist
for d in [ACCOUNTS_DIR, SESSIONS_DIR, DEVICES_DIR]:
    d.mkdir(exist_ok=True)

DEFAULT_CONFIG = {
    "accounts_path": str(ACCOUNTS_DIR),
    "sessions_path": str(SESSIONS_DIR),
    "devices_path": str(DEVICES_DIR),
    "proxies_file": str(PROXIES_FILE),
    "working_proxies_file": str(WORKING_PROXIES_FILE),
    "threads": 5,
    "view_delay_min": 3,
    "view_delay_max": 8,
    "views_per_account": 50,
    "views_per_video": 10,
    "proxy_rotation": "round_robin",
    "auto_scrape_proxies": True,
    "proxy_check_timeout": 5,
    "proxy_check_threads": 50,
    "zefoy_captcha_auto_solve": True,
    "signerpy_use_local": False,
    "signerpy_endpoint": "http://localhost:8080/sign",
    "x_gorgon_version": "v2",
    "app_id": 1233,
    "app_version": "31.5.2",
    "device_platform": "android",
    "sdk_version": "27.0.0",
}

config = DEFAULT_CONFIG.copy()

def load_config(path=None):
    """Load configuration from JSON file"""
    global config
    path = path or CONFIG_FILE
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                loaded = json.load(f)
                config.update(loaded)
        except Exception as e:
            print(f"[!] Failed to load config: {e}")

def save_config(path=None):
    """Save current configuration to JSON file"""
    global config
    path = path or CONFIG_FILE
    try:
        with open(path, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"[!] Failed to save config: {e}")
        return False

def set_path(key, value):
    """Update a path configuration"""
    global config
    config[key] = str(value)
    save_config()

# Load on import
load_config()
