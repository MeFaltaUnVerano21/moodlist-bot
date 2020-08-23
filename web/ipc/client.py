import asyncio
import websockets

import json

async def hello():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"endpoint": "now_playing", "data": {"songs": ["song1", "song2"]}}))

        greeting = await websocket.recv()
        print(greeting)

loop = asyncio.get_event_loop()
loop.run_until_complete(hello())