from enum import Enum
from typing import Dict, Any, Optional
import json
import time

class MessageType(Enum):
    # Client registration
    CLIENT_REGISTER = "client_register"
    CLIENT_HEARTBEAT = "client_heartbeat"

    # Screen sharing
    SCREENSHOT_REQUEST = "screenshot_request"
    SCREENSHOT_RESPONSE = "screenshot_response"

    # Remote control
    REMOTE_CONTROL_START = "remote_control_start"
    REMOTE_CONTROL_STOP = "remote_control_stop"
    REMOTE_INPUT = "remote_input"

    # File operations
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETE = "file_delete"
    FILE_LIST = "file_list"
    FILE_MANAGER = "file_manager"

    # Power management
    POWER_SHUTDOWN = "power_shutdown"
    POWER_RESTART = "power_restart"
    POWER_LOGOFF = "power_logoff"
    POWER_HIBERNATE = "power_hibernate"

    # Messaging
    MESSAGE_SEND = "message_send"
    MESSAGE_REPLY = "message_reply"

    # Program execution
    EXECUTE_PROGRAM = "execute_program"
    PROGRAM_RESULT = "program_result"

    # Status updates
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    SUCCESS = "success"

class Message:
    def __init__(self, msg_type: MessageType, data: Dict[str, Any] = None,
                 client_id: str = None, timestamp: float = None):
        self.type = msg_type
        self.data = data or {}
        self.client_id = client_id
        self.timestamp = timestamp or time.time()
        self.id = str(int(self.timestamp * 1000000))  # Microsecond precision

    def to_json(self) -> str:
        return json.dumps({
            'type': self.type.value,
            'data': self.data,
            'client_id': self.client_id,
            'timestamp': self.timestamp,
            'id': self.id
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        data = json.loads(json_str)
        return cls(
            MessageType(data['type']),
            data.get('data'),
            data.get('client_id'),
            data.get('timestamp')
        )