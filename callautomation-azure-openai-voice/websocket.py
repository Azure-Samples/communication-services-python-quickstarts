import asyncio
import websockets
from azureOpenAIService import init_websocket, start_conversation
from mediaStreamingHandler import process_websocket_message_async

async def handle_realtime_messages(websocket):
    print('Client connected')
    await init_websocket(websocket)
    await start_conversation()
    try:
        async for message in websocket:
            await process_websocket_message_async(message)
    except websockets.exceptions.ConnectionClosedOK:
        print('Client disconnected')

async def main():
    async with websockets.serve(handle_realtime_messages, "localhost", 5001):
        print("WebSocket server running on port 5001")
        await asyncio.Future()  # run forever
if __name__ == "__main__":
    asyncio.run(main())
