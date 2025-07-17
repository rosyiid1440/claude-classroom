import asyncio
import websockets
import json
import threading
from typing import Dict, Set
import time

from shared.config import Config
from shared.protocol import Message, MessageType
from shared.utils import get_local_ip

class WebSocketHandler:
    def __init__(self, teacher_server):
        self.teacher_server = teacher_server
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.server = None
        
    def start(self):
        """Start WebSocket server"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        start_server = websockets.serve(
            self.handle_client, 
            Config.SERVER_HOST, 
            Config.WEBSOCKET_PORT
        )
        
        print(f"WebSocket server starting on {get_local_ip()}:{Config.WEBSOCKET_PORT}")
        loop.run_until_complete(start_server)
        loop.run_forever()
    
    async def handle_client(self, websocket, path):
        """Handle client WebSocket connection"""
        client_id = None
        
        try:
            async for message in websocket:
                try:
                    msg = Message.from_json(message)
                    
                    if msg.type == MessageType.CLIENT_REGISTER:
                        client_id = msg.client_id
                        self.clients[client_id] = websocket
                        self.teacher_server.register_client(client_id, msg.data)
                        
                        # Send acknowledgment
                        response = Message(MessageType.SUCCESS, {'message': 'Registration successful'})
                        await websocket.send(response.to_json())
                        
                    elif msg.type == MessageType.CLIENT_HEARTBEAT:
                        client_id = msg.client_id
                        self.teacher_server.update_client_status(client_id, 'online')
                        
                    elif msg.type == MessageType.SCREENSHOT_RESPONSE:
                        self.teacher_server.handle_screenshot(msg.client_id, msg.data['screenshot'])
                        
                    elif msg.type == MessageType.MESSAGE_REPLY:
                        # Handle message reply from client
                        from teacher_server.app import socketio
                        socketio.emit('message_reply', {
                            'client_id': msg.client_id,
                            'message': msg.data['message']
                        })
                        
                    elif msg.type == MessageType.PROGRAM_RESULT:
                        # Handle program execution result
                        from teacher_server.app import socketio
                        socketio.emit('program_result', {
                            'client_id': msg.client_id,
                            'result': msg.data
                        })
                        
                    elif msg.type == MessageType.STATUS_UPDATE:
                        self.teacher_server.update_client_status(msg.client_id, msg.data['status'])
                        
                except Exception as e:
                    print(f"Message handling error: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                self.teacher_server.update_client_status(client_id, 'offline')
    
    def send_to_client(self, client_id: str, message_type: MessageType, data: dict):
        """Send message to specific client"""
        if client_id in self.clients:
            message = Message(message_type, data)
            asyncio.run_coroutine_threadsafe(
                self.clients[client_id].send(message.to_json()),
                asyncio.get_event_loop()
            )
    
    def broadcast_message(self, message_type: MessageType, data: dict):
        """Broadcast message to all clients"""
        message = Message(message_type, data)
        for client_id, websocket in self.clients.items():
            asyncio.run_coroutine_threadsafe(
                websocket.send(message.to_json()),
                asyncio.get_event_loop()
            )