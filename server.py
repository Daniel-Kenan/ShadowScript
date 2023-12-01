import asyncio
import websockets
import socket
import os
import sqlite3
from colorama import init, Fore
from datetime import datetime

# Initialize colorama
init(autoreset=True)

class WebSocketServer:
    def __init__(self):
        self.rooms = {}
        self.db_connection = sqlite3.connect('db.sqlite3')
        self.create_tables()

    def create_tables(self):
        # Create tables if they don't exist
        cursor = self.db_connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id TEXT PRIMARY KEY,
                masters TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servants (
                id TEXT PRIMARY KEY,
                room_id TEXT,
                FOREIGN KEY (room_id) REFERENCES rooms(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                room_id TEXT,
                sender TEXT,
                message TEXT
            )
        ''')
        self.db_connection.commit()

    async def handle_connection(self, websocket, path):
        # This function is called when a new connection is established

        print(f"{Fore.GREEN}[{datetime.now()}] Client connected from {websocket.remote_address}")

        try:
            # Receive the initial message to determine client type and room
            initial_message = await websocket.recv()
            client_type, room_id = initial_message.split(':')

            if client_type == 'master':
                await self.handle_master(websocket, room_id)
            elif client_type == 'servant':
                await self.handle_servant(websocket, room_id)
            else:
                print(f"{Fore.RED}[{datetime.now()}] Invalid client type: {client_type}")

        except websockets.exceptions.ConnectionClosed:
            print(f"{Fore.YELLOW}[{datetime.now()}] Connection closed by the client.")

    async def create_or_get_room(self, room_id):
        # Create a new room if it doesn't exist
        cursor = self.db_connection.cursor()
        cursor.execute('INSERT OR IGNORE INTO rooms (id, masters) VALUES (?, ?)', (room_id, ''))
        self.db_connection.commit()

        if room_id not in self.rooms:
            self.rooms[room_id] = {"masters": set(), "servants": set()}
            print(f"{Fore.BLUE}[{datetime.now()}] Room '{room_id}' created.")
        return self.rooms[room_id]

    async def handle_master(self, websocket, room_id):
        # Handle master client logic

        room = await self.create_or_get_room(room_id)
        room["masters"].add(websocket)

        # Store master information in the database
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT masters FROM rooms WHERE id = ?', (room_id,))
        existing_masters = cursor.fetchone()[0]
        updated_masters = f"{existing_masters},{str(websocket.remote_address)}"
        cursor.execute('UPDATE rooms SET masters = ? WHERE id = ?', (updated_masters, room_id))
        self.db_connection.commit()

        try:
            while True:
                # Master sends a message
                message_to_servants = await websocket.recv()
                print(f"{Fore.GREEN}[{datetime.now()}] Master in room '{room_id}' sent message: {message_to_servants}")

                # Store message in the database
                cursor.execute('INSERT INTO messages (room_id, sender, message) VALUES (?, ?, ?)',
                               (room_id, str(websocket.remote_address), message_to_servants))
                self.db_connection.commit()

                # Broadcast the message to all masters and servants in the room
                await self.broadcast_to_masters(room, message_to_servants)
                await self.broadcast_to_servants(room, message_to_servants)

        except websockets.exceptions.ConnectionClosed:
            print(f"{Fore.YELLOW}[{datetime.now()}] Master in room '{room_id}' disconnected.")
            room["masters"].remove(websocket)

    async def handle_servant(self, websocket, room_id):
        # Handle servant PC logic

        # Check if the room exists
        room = await self.create_or_get_room(room_id)

        # Add the servant to the room
        room["servants"].add(websocket)
        print(f"{Fore.CYAN}[{datetime.now()}] Servant joined room '{room_id}'.")

        # Store servant information in the database
        cursor = self.db_connection.cursor()
        cursor.execute('INSERT OR IGNORE INTO servants (id, room_id) VALUES (?, ?)', (str(websocket.remote_address), room_id))
        self.db_connection.commit()

        try:
            while True:
                # Servant receives a message from any master
                message_from_master = await websocket.recv()
                print(f"{Fore.CYAN}[{datetime.now()}] Servant in room '{room_id}' received message from master: {message_from_master}")

                # Store message in the database
                cursor.execute('INSERT INTO messages (room_id, sender, message) VALUES (?, ?, ?)',
                               (room_id, str(websocket.remote_address), message_from_master))
                self.db_connection.commit()

                # Simulate processing by adding a prefix
                servant_response = f"Servant Response: {message_from_master}"

                # Send the response back to all masters in the room
                await self.broadcast_to_masters(room, servant_response)

        except websockets.exceptions.ConnectionClosed:
            print(f"{Fore.YELLOW}[{datetime.now()}] Servant in room '{room_id}' disconnected.")
            room["servants"].remove(websocket)

    async def broadcast_to_masters(self, room, message):
        # Broadcast the message to all masters in the room
        tasks = [master.send(message) for master in room["masters"]]
        await asyncio.gather(*tasks)

    async def broadcast_to_servants(self, room, message):
        # Broadcast the message to all servants in the room
        tasks = [servant.send(message) for servant in room["servants"]]
        await asyncio.gather(*tasks)

async def start_websocket_server():
    # Create an instance of the WebSocketServer class
    server = WebSocketServer()

    # Get local IP address
    ip_address = socket.gethostbyname(socket.gethostname())

    # Check if the $PORT environment variable is set
    port = int(os.getenv('PORT', 8765))

    # Start the WebSocket server with the specified or dynamically assigned port
    server_instance = await websockets.serve(
        server.handle_connection, "0.0.0.0", port
    )

    print(f"{Fore.MAGENTA}[{datetime.now()}] WebSocket server started. Listening on ws://{ip_address}:{port}")

    # Keep the server running
    await asyncio.Future()

# Run the WebSocket server
asyncio.get_event_loop().run_until_complete(start_websocket_server())
