import socket
import hashlib
import base64
import os
import platform
from typing import Optional, Tuple

def get_local_ip() -> str:
    """Get local IP address"""
    try:
        # Connect to a non-routable address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('10.255.255.255', 1))
            return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'

def generate_client_id() -> str:
    """Generate unique client ID based on machine info"""
    machine_info = f"{platform.node()}-{platform.machine()}-{platform.system()}"
    return hashlib.md5(machine_info.encode()).hexdigest()[:12]

def encode_file(file_path: str) -> str:
    """Encode file to base64 string"""
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def decode_file(encoded_data: str, output_path: str) -> None:
    """Decode base64 string to file"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(base64.b64decode(encoded_data))

def is_admin() -> bool:
    """Check if running with admin privileges"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_machine_info() -> dict:
    """Get machine information"""
    return {
        'hostname': platform.node(),
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'ip_address': get_local_ip()
    }