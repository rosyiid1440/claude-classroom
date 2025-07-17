# teacher_server/websocket_handler.py

import asyncio
import websockets
import json
import threading
import traceback # Import traceback for detailed error logging
from typing import Dict

from shared.config import Config
from shared.protocol import Message, MessageType
from shared.utils import get_local_ip

class WebSocketHandler:
    def __init__(self, teacher_server):
        self.teacher_server = teacher_server
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.loop = None

    def start_in_thread(self):
        """Public method to start the server in a new thread."""
        thread = threading.Thread(target=self._run_server_loop, daemon=True)
        thread.start()

    def _run_server_loop(self):
        """Sets up and runs the asyncio event loop in the new thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._start_server())
        except KeyboardInterrupt:
            print("WebSocket server loop interrupted.")
        finally:
            self.loop.close()
            print("WebSocket server loop closed.")

    async def _start_server(self):
        """The main async method that starts the websockets server."""
        async with websockets.serve(
            self.handle_client,
            Config.SERVER_HOST,
            Config.WEBSOCKET_PORT,
            max_size=Config.MAX_FILE_SIZE
        ):
            print(f"WebSocket server started and listening on {get_local_ip()}:{Config.WEBSOCKET_PORT}")
            await asyncio.Future()

    async def handle_client(self, websocket):
        """Handles an individual client connection."""
        client_id = None
        try:
            message_json = await websocket.recv()
            msg = Message.from_json(message_json)

            if msg.type == MessageType.CLIENT_REGISTER:
                client_id = msg.client_id
                self.clients[client_id] = websocket
                self.loop.call_soon_threadsafe(
                    self.teacher_server.register_client, client_id, msg.data
                )
                response = Message(MessageType.SUCCESS, {'message': 'Registration successful'})
                await websocket.send(response.to_json())
                print(f"Client registered: {client_id}")
            else:
                print("Connection closed: First message was not a registration.")
                return

            async for message in websocket:
                msg = Message.from_json(message)
                self.loop.call_soon_threadsafe(self.handle_message, msg)

        except websockets.exceptions.ConnectionClosed:
            if client_id:
                print(f"Client {client_id} disconnected.")
        except Exception as e:
            print(f"Error in handle_client for {client_id}: {e}")
        finally:
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                self.loop.call_soon_threadsafe(
                    self.teacher_server.update_client_status, client_id, 'offline'
                )
                print(f"Client {client_id} unregistered.")

    def handle_message(self, msg: Message):
        """
        Processes messages from a client. THIS NOW INCLUDES ERROR HANDLING.
        """
        try:
            if msg.type == MessageType.CLIENT_HEARTBEAT:
                self.teacher_server.update_client_status(msg.client_id, 'online')

            elif msg.type == MessageType.SCREENSHOT_RESPONSE:
                # SALAH: self.teacher_server.handle_screenshot(msg.client_id, msg.data['screenshot'])
                # BENAR: Teruskan seluruh objek data
                self.teacher_server.handle_screenshot(msg.client_id, msg.data)

            elif msg.type == MessageType.MESSAGE_REPLY:
                from teacher_server.app import socketio
                socketio.emit('message_reply', {
                    'client_id': msg.client_id,
                    'message': msg.data['message']
                })

            elif msg.type == MessageType.PROGRAM_RESULT:
                from teacher_server.app import socketio
                socketio.emit('program_result', {
                    'client_id': msg.client_id,
                    'result': msg.data
                })

            elif msg.type == MessageType.STATUS_UPDATE:
                self.teacher_server.update_client_status(msg.client_id, msg.data['status'])

        except Exception as e:
            print(f"\n--- Unhandled Exception in handle_message ---")
            print(f"Client ID: {msg.client_id}")
            print(f"Message Type: {msg.type.value if msg.type else 'N/A'}")
            print(f"Error: {e}")
            traceback.print_exc() # This provides a full, detailed traceback
            print(f"-------------------------------------------\n")

    def send_to_client(self, client_id: str, message_type: MessageType, data: dict):
        """Sends a message to a specific client in a thread-safe manner."""
        if client_id in self.clients and self.loop:
            message = Message(message_type, data, client_id=client_id)
            asyncio.run_coroutine_threadsafe(
                self.clients[client_id].send(message.to_json()),
                self.loop
            )

    def broadcast_message(self, message_type: MessageType, data: dict):
        """Broadcasts a message to all clients."""
        if not self.loop:
            return
        message = Message(message_type, data)
        for websocket in self.clients.values():
            asyncio.run_coroutine_threadsafe(
                websocket.send(message.to_json()),
                self.loop
            )