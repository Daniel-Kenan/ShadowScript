import asyncio
import websockets
import socket

class WebSocketServer:
    def __init__(self):
        self.rooms = {}

    async def handle_connection(self, websocket, path):
        # This function is called when a new connection is established

        print(f"Client connected from {websocket.remote_address}")

        try:
            # Receive the initial message to determine client type and room
            initial_message = await websocket.recv()
            client_type, room_id = initial_message.split(':')

            if client_type == 'master':
                await self.handle_master(websocket, room_id)
            elif client_type == 'servant':
                await self.handle_servant(websocket, room_id)
            else:
                print(f"Invalid client type: {client_type}")

        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by the client.")

    async def handle_master(self, websocket, room_id):
        # Handle master client logic

        # Create a new room if it doesn't exist
        if room_id not in self.rooms:
            self.rooms[room_id] = {"master": websocket, "servants": set()}
            print(f"Room '{room_id}' created.")

        try:
            while True:
                # Master sends a message
                message_to_servants = await websocket.recv()
                print(f"Master in room '{room_id}' sent message: {message_to_servants}")

                # Broadcast the message to all servants in the room
                for servant in self.rooms[room_id]["servants"]:
                    await servant.send(message_to_servants)

                # Wait for responses from servants
                servant_responses = []
                for _ in self.rooms[room_id]["servants"]:
                    response = await websocket.recv()
                    servant_responses.append(response)

                # Send the responses back to the master
                for response in servant_responses:
                    await websocket.send(response)

        except websockets.exceptions.ConnectionClosed:
            print(f"Master in room '{room_id}' disconnected.")
            del self.rooms[room_id]

    async def handle_servant(self, websocket, room_id):
        # Handle servant PC logic

        # Check if the room exists
        if room_id not in self.rooms:
            print(f"Room '{room_id}' does not exist. Closing connection.")
            await websocket.close()
            return

        # Add the servant to the room
        self.rooms[room_id]["servants"].add(websocket)
        print(f"Servant joined room '{room_id}'.")

        try:
            while True:
                # Servant receives a message from the master
                message_from_master = await websocket.recv()
                print(f"Servant in room '{room_id}' received message from master: {message_from_master}")

                # Simulate processing by adding a prefix
                servant_response = f"Servant Response: {message_from_master}"

                # Send the response back to the master
                await self.rooms[room_id]["master"].send(servant_response)
                print(f"Servant in room '{room_id}' sent response to master: {servant_response}")

        except websockets.exceptions.ConnectionClosed:
            print(f"Servant in room '{room_id}' disconnected.")
            self.rooms[room_id]["servants"].remove(websocket)

async def start_websocket_server():
    # Create an instance of the WebSocketServer class
    server = WebSocketServer()

    # Get local IP address
    ip_address = socket.gethostbyname(socket.gethostname())

    # Start the WebSocket server with a dynamically assigned port
    server_instance = await websockets.serve(
        server.handle_connection, ip_address, 0  # 0 for dynamically assigned port
    )

    # Get the assigned port
    _, port = server_instance.sockets[0].getsockname()

    print(f"WebSocket server started. Listening on ws://{ip_address}:{port}")

    # Keep the server running
    await asyncio.Future()

# Run the WebSocket server
asyncio.get_event_loop().run_until_complete(start_websocket_server())
