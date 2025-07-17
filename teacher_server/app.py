from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import os
import threading
import time
from datetime import datetime
import base64
import io
from PIL import Image
import uuid

from teacher_server.websocket_handler import WebSocketHandler
from teacher_server.auth import AuthManager
from shared.config import Config
from shared.protocol import Message, MessageType
from shared.utils import get_local_ip
# from .websocket_handler import WebSocketHandler
# from .auth import AuthManager

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
connected_clients = {}
websocket_handler = None
auth_manager = AuthManager()

class TeacherServer:
    def __init__(self):
        self.clients = {}
        self.screenshots = {}
        self.remote_sessions = {}

    def start(self):
        """Start the teacher server"""
        global websocket_handler

        # Create upload directory
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

        # Start WebSocket handler for client communication
        global websocket_handler
        websocket_handler = WebSocketHandler(self)
        websocket_handler.start_in_thread()

        # Start client discovery
        discovery_thread = threading.Thread(target=self.start_discovery)
        discovery_thread.daemon = True
        discovery_thread.start()

        print(f"Teacher server starting on {get_local_ip()}:{Config.SERVER_PORT}")
        socketio.run(app, host=Config.SERVER_HOST, port=Config.SERVER_PORT, debug=False)

    def start_discovery(self):
        """Start client discovery service"""
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(('', Config.DISCOVERY_PORT))

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode())

                if message.get('type') == 'client_discovery':
                    # Respond to client discovery
                    response = {
                        'type': 'server_response',
                        'server_ip': get_local_ip(),
                        'server_port': Config.WEBSOCKET_PORT
                    }
                    sock.sendto(json.dumps(response).encode(), addr)

            except Exception as e:
                print(f"Discovery error: {e}")
                time.sleep(1)

    def register_client(self, client_id, client_info):
        """Register a new client"""
        self.clients[client_id] = {
            'id': client_id,
            'info': client_info,
            'last_seen': time.time(),
            'status': 'online',
            'websocket': None
        }

        # Notify web dashboard
        socketio.emit('client_connected', {
            'client_id': client_id,
            'client_info': client_info
        })

        print(f"Client registered: {client_id}")

    def update_client_status(self, client_id, status):
        """Update client status"""
        if client_id in self.clients:
            self.clients[client_id]['status'] = status
            self.clients[client_id]['last_seen'] = time.time()

            socketio.emit('client_status_update', {
                'client_id': client_id,
                'status': status
            })

    def handle_screenshot(self, client_id, data):
        """Menangani screenshot dari klien dan membedakan antara thumbnail dan remote control."""
        try:
            is_remote_control = data.get('is_remote_control', False)
            screenshot_b64 = data.get('screenshot')

            if not screenshot_b64:
                return

            # Jika ini adalah stream untuk remote control
            if is_remote_control:
                # Langsung kirim data gambar resolusi penuh ke dasbor web
                socketio.emit('remote_screen_update', {
                    'client_id': client_id,
                    'image': screenshot_b64
                })
            # Jika ini untuk pembaruan thumbnail di dasbor utama
            else:
                image_data = base64.b64decode(screenshot_b64)
                image = Image.open(io.BytesIO(image_data))

                # Buat thumbnail
                thumbnail = image.copy()
                thumbnail.thumbnail((200, 150), Image.Resampling.LANCZOS)

                buffer = io.BytesIO()
                thumbnail.save(buffer, format='JPEG', quality=Config.SCREENSHOT_QUALITY)
                thumbnail_b64 = base64.b64encode(buffer.getvalue()).decode()

                # Simpan thumbnail
                if client_id in self.clients:
                    self.screenshots[client_id] = {
                        'thumbnail': thumbnail_b64,
                        'timestamp': time.time()
                    }

                # Kirim pembaruan thumbnail ke dasbor web
                socketio.emit('screenshot_update', {
                    'client_id': client_id,
                    'thumbnail': thumbnail_b64
                })

        except Exception as e:
            print(f"Gagal memproses screenshot dari {client_id}: {e}")

    def send_message_to_client(self, client_id, message_type, data):
        """Send message to specific client"""
        if websocket_handler:
            websocket_handler.send_to_client(client_id, message_type, data)

    def broadcast_message(self, message_type, data):
        """Broadcast message to all clients"""
        if websocket_handler:
            websocket_handler.broadcast_message(message_type, data)

# Initialize server
teacher_server = TeacherServer()

# Web Routes
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/clients')
def get_clients():
    """Get all connected clients"""
    return jsonify(list(teacher_server.clients.values()))

@app.route('/api/screenshot/<client_id>')
def get_screenshot(client_id):
    """Get full screenshot for client"""
    if client_id in teacher_server.screenshots:
        screenshot_data = teacher_server.screenshots[client_id]['full']
        return jsonify({'screenshot': screenshot_data})
    return jsonify({'error': 'Screenshot not found'}), 404

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    print('Web client connected')
    emit('client_list', list(teacher_server.clients.values()))

@socketio.on('send_message')
def handle_send_message(data):
    """Send message to client(s)"""
    client_id = data.get('client_id')
    message = data.get('message')

    if client_id == 'all':
        teacher_server.broadcast_message(MessageType.MESSAGE_SEND, {'message': message})
    else:
        teacher_server.send_message_to_client(client_id, MessageType.MESSAGE_SEND, {'message': message})

@socketio.on('power_control')
def handle_power_control(data):
    """Handle power control commands"""
    client_id = data.get('client_id')
    action = data.get('action')

    message_type = {
        'shutdown': MessageType.POWER_SHUTDOWN,
        'restart': MessageType.POWER_RESTART,
        'logoff': MessageType.POWER_LOGOFF,
        'hibernate': MessageType.POWER_HIBERNATE
    }.get(action)

    if message_type:
        if client_id == 'all':
            teacher_server.broadcast_message(message_type, {'force': True})
        else:
            teacher_server.send_message_to_client(client_id, message_type, {'force': True})

@socketio.on('remote_control')
def handle_remote_control(data):
    """Handle remote control commands"""
    client_id = data.get('client_id')
    action = data.get('action')

    if action == 'start':
        teacher_server.send_message_to_client(client_id, MessageType.REMOTE_CONTROL_START, {})
        teacher_server.remote_sessions[client_id] = True
    elif action == 'stop':
        teacher_server.send_message_to_client(client_id, MessageType.REMOTE_CONTROL_STOP, {})
        teacher_server.remote_sessions.pop(client_id, None)

@socketio.on('remote_input')
def handle_remote_input(data):
    """Handle remote input events"""
    client_id = data.get('client_id')
    if client_id in teacher_server.remote_sessions:
        teacher_server.send_message_to_client(client_id, MessageType.REMOTE_INPUT, data)

@socketio.on('file_operation')
def handle_file_operation(data):
    """Handle file operations"""
    client_id = data.get('client_id')
    operation = data.get('operation')

    teacher_server.send_message_to_client(client_id, MessageType.FILE_MANAGER, data)

@socketio.on('execute_program')
def handle_execute_program(data):
    """Handle program execution"""
    client_id = data.get('client_id')
    program_data = data.get('program_data')

    teacher_server.send_message_to_client(client_id, MessageType.EXECUTE_PROGRAM, program_data)

if __name__ == '__main__':
    teacher_server.start()