import os
import json
from typing import Dict, Any

class Config:
    # Server configuration
    SERVER_HOST = '127.0.0.1'
    SERVER_PORT = 8080
    WEBSOCKET_PORT = 8081

    # Security
    SECRET_KEY = 'your-secret-key-change-in-production'
    AUTH_TOKEN_EXPIRY = 3600  # 1 hour

    # Client settings
    CLIENT_HEARTBEAT_INTERVAL = 30  # seconds
    SCREENSHOT_INTERVAL = 1  # seconds
    REMOTE_CONTROL_SCREENSHOT_INTERVAL = 0.5
    SCREENSHOT_QUALITY = 30

    # File transfer
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    UPLOAD_FOLDER = 'uploads'

    # Network
    DISCOVERY_PORT = 9999
    BROADCAST_INTERVAL = 10

    @classmethod
    def load_from_file(cls, config_file: str) -> None:
        """Load configuration from JSON file"""
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                for key, value in config_data.items():
                    setattr(cls, key, value)

    @classmethod
    def save_to_file(cls, config_file: str) -> None:
        """Save configuration to JSON file"""
        config_data = {
            attr: getattr(cls, attr)
            for attr in dir(cls)
            if not attr.startswith('_') and not callable(getattr(cls, attr))
        }
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)