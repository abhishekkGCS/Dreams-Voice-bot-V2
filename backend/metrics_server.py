import asyncio
import json
import websockets
from http import HTTPStatus

async def start_metrics_server(collector, host="localhost", port=8765):
    connected = set()

    async def process_request(connection, request):
        headers = request.headers
        if "Upgrade" not in headers.get("Connection", ""):
            if request.method == "OPTIONS":
                return (
                    HTTPStatus.OK,
                    [
                        ("Access-Control-Allow-Origin", "*"),
                        ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
                        ("Access-Control-Allow-Headers", "Content-Type"),
                    ],
                    b""
                )
            
            return (
                HTTPStatus.OK,
                [
                    ("Access-Control-Allow-Origin", "*"),
                    ("Content-Type", "application/json"),
                ],
                json.dumps(collector.get_snapshot()).encode("utf-8")
            )
        return None

    async def handler(websocket):
        connected.add(websocket)
        try:
            snapshot = collector.get_snapshot()
            await websocket.send(json.dumps({"type": "snapshot", "data": snapshot}))
            await websocket.wait_closed()
        finally:
            connected.remove(websocket)

    async def broadcaster():
        while True:
            await asyncio.sleep(1.0)
            if connected:
                payload = collector.get_broadcast_payload()
                message = json.dumps({"type": "broadcast", "data": payload})
                websockets.broadcast(connected, message)
            else:
                # clear events to prevent memory leak when no one is listening
                collector.get_broadcast_payload()

    server = await websockets.serve(
        handler, 
        host, 
        port, 
        process_request=process_request,
        extra_headers=[("Access-Control-Allow-Origin", "*")]
    )
    
    asyncio.create_task(broadcaster())
    print(f"Metrics server running on ws://{host}:{port}")
    await server.wait_closed()
