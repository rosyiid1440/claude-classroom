import asyncio
import websockets
import json
import time
import threading
import base64
import os
import subprocess
import pyautogui
from PIL import ImageGrab
import io
import shutil
import zipfile

from shared.config import Config
from shared.protocol import Message, MessageType
from shared.utils import generate_client_id, get_machine_info, encode_file, decode_file

class StudentClient:
    def __init__(self):
        self.client_id = generate_client_id()
        self.server_uri = f"ws://{Config.SERVER_HOST}:{Config.WEBSOCKET_PORT}"
        self.websocket = None
        self.is_running = False
        self.remote_control_active = False

    def start(self):
        self.is_running = True
        self.main_loop_thread = threading.Thread(target=self.run_main_loop)
        self.main_loop_thread.daemon = True
        self.main_loop_thread.start()

    def stop(self):
        self.is_running = False
        if self.websocket:
            asyncio.run(self.websocket.close())

    def run_main_loop(self):
        asyncio.run(self.main_loop())

    async def main_loop(self):
        while self.is_running:
            try:
                async with websockets.connect(self.server_uri) as websocket:
                    self.websocket = websocket
                    await self.register()

                    # Start heartbeat and screenshot tasks
                    heartbeat_task = asyncio.create_task(self.send_heartbeat())
                    screenshot_task = asyncio.create_task(self.send_screenshots())

                    await self.listen_for_commands()

            except (websockets.exceptions.ConnectionClosed, OSError):
                print("Connection lost. Reconnecting...")
                await asyncio.sleep(5)

    async def register(self):
        machine_info = get_machine_info()
        message = Message(MessageType.CLIENT_REGISTER, data=machine_info, client_id=self.client_id)
        await self.websocket.send(message.to_json())
        print("Registered with server.")

    async def send_heartbeat(self):
        while self.is_running:
            message = Message(MessageType.CLIENT_HEARTBEAT, client_id=self.client_id)
            await self.websocket.send(message.to_json())
            await asyncio.sleep(Config.CLIENT_HEARTBEAT_INTERVAL)

    async def send_screenshots(self):
        """Mengirim screenshot secara berkala dengan interval yang berbeda."""
        while self.is_running:
            try:
                # Jika remote control aktif, kirim gambar lebih cepat
                if self.remote_control_active:
                    screenshot = self.capture_screenshot()
                    # Tambahkan flag untuk menandakan ini adalah update remote control
                    message = Message(MessageType.SCREENSHOT_RESPONSE,
                                      data={'screenshot': screenshot, 'is_remote_control': True},
                                      client_id=self.client_id)
                    await self.websocket.send(message.to_json())
                    # Gunakan interval yang lebih cepat
                    await asyncio.sleep(Config.REMOTE_CONTROL_SCREENSHOT_INTERVAL)
                else:
                    # Jika tidak, kirim pembaruan thumbnail seperti biasa
                    screenshot = self.capture_screenshot()
                    message = Message(MessageType.SCREENSHOT_RESPONSE,
                                      data={'screenshot': screenshot, 'is_remote_control': False},
                                      client_id=self.client_id)
                    await self.websocket.send(message.to_json())
                    # Gunakan interval normal
                    await asyncio.sleep(Config.SCREENSHOT_INTERVAL)
            except websockets.exceptions.ConnectionClosed:
                print("Koneksi ditutup saat mengirim screenshot, akan mencoba lagi.")
                break # Keluar dari loop ini untuk memulai kembali koneksi utama
            except Exception as e:
                print(f"Gagal mengirim screenshot: {e}")
                await asyncio.sleep(Config.SCREENSHOT_INTERVAL) # Tunggu sebelum mencoba lagi

    def capture_screenshot(self) -> str:
        try:
            screenshot = ImageGrab.grab()
            buffer = io.BytesIO()
            screenshot.save(buffer, format='JPEG', quality=Config.SCREENSHOT_QUALITY)
            return base64.b64encode(buffer.getvalue()).decode()
        except Exception as e:
            print(f"Screenshot error: {e}")
            return ""

    async def listen_for_commands(self):
        async for message_json in self.websocket:
            try:
                message = Message.from_json(message_json)
                await self.handle_command(message)
            except Exception as e:
                print(f"Command handling error: {e}")

    async def handle_command(self, message: Message):
        if message.type == MessageType.MESSAGE_SEND:
            self.show_message(message.data['message'])

        elif message.type == MessageType.POWER_SHUTDOWN:
            self.power_control('shutdown', message.data.get('force', False))
        elif message.type == MessageType.POWER_RESTART:
            self.power_control('restart', message.data.get('force', False))
        elif message.type == MessageType.POWER_LOGOFF:
            self.power_control('logoff', message.data.get('force', False))

        elif message.type == MessageType.REMOTE_CONTROL_START:
            self.remote_control_active = True
        elif message.type == MessageType.REMOTE_CONTROL_STOP:
            self.remote_control_active = False

        elif message.type == MessageType.REMOTE_INPUT:
            self.handle_remote_input(message.data)

        elif message.type == MessageType.FILE_MANAGER:
            await self.handle_file_manager(message.data)

        elif message.type == MessageType.EXECUTE_PROGRAM:
            await self.execute_program(message.data)

    def show_message(self, text: str):
        # This will show a message box on the client's screen
        # On Windows, this requires a UI context, which a service might not have.
        # For simplicity, we'll use a command-line tool.
        subprocess.Popen(['msg', '*', text], shell=True)

    def power_control(self, action: str, force: bool = True):
        force_flag = '/f' if force else ''
        if action == 'shutdown':
            subprocess.run(f'shutdown /s /t 0 {force_flag}', shell=True)
        elif action == 'restart':
            subprocess.run(f'shutdown /r /t 0 {force_flag}', shell=True)
        elif action == 'logoff':
            subprocess.run('shutdown /l', shell=True)

    def handle_remote_input(self, data: dict):
        if not self.remote_control_active:
            return

        input_type = data.get('type')
        if input_type == 'click':
            x, y = data.get('x'), data.get('y')
            screen_width, screen_height = pyautogui.size()
            pyautogui.moveTo(x * screen_width, y * screen_height)
            pyautogui.click(button='left' if data.get('button') == 0 else 'right')
        elif input_type == 'key':
            key = data.get('key')
            pyautogui.press(key)

    async def handle_file_manager(self, data: dict):
        operation = data.get('operation')
        path = data.get('path')
        response_data = {}

        try:
            if operation == 'list':
                files = []
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    files.append({
                        'name': item,
                        'is_dir': os.path.isdir(item_path),
                        'size': os.path.getsize(item_path)
                    })
                response_data = {'files': files}

            # ... other file operations ...

            response = Message(MessageType.FILE_MANAGER, data=response_data, client_id=self.client_id)
            await self.websocket.send(response.to_json())

        except Exception as e:
            print(f"File manager error: {e}")

    async def execute_program(self, data: dict):
        filename = data.get('filename')
        file_data = data.get('data')
        silent = data.get('silent', False)
        
        try:
            # Save the executable
            temp_dir = os.path.join(os.environ['TEMP'], 'claude_classroom')
            os.makedirs(temp_dir, exist_ok=True)
            exe_path = os.path.join(temp_dir, filename)
            decode_file(file_data, exe_path)

            # Execute it
            if silent:
                subprocess.Popen([exe_path], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([exe_path])

            result = {'status': 'success', 'message': f'{filename} executed.'}

        except Exception as e:
            result = {'status': 'error', 'message': str(e)}
        
        response = Message(MessageType.PROGRAM_RESULT, data=result, client_id=self.client_id)
        await self.websocket.send(response.to_json())

if __name__ == '__main__':
    client = StudentClient()
    client.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.stop()