"""
Modbus HTTP Bridge

HTTP server that bridges Modbus TCP traffic over HTTP for use with LocalTunnel.
Remote clients send Modbus frames as HTTP POST requests, and receive responses.
"""

import asyncio
import base64
from aiohttp import web
from typing import Optional
from rich.console import Console

console = Console()


class ModbusHttpBridge:
    """HTTP bridge that forwards Modbus requests to a local Modbus server"""
    
    def __init__(self, modbus_host: str = "127.0.0.1", modbus_port: int = 502, http_port: int = 8080):
        self.modbus_host = modbus_host
        self.modbus_port = modbus_port
        self.http_port = http_port
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.setup_routes()
    
    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_post('/modbus', self.handle_modbus_request)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/', self.handle_index)
    
    async def handle_index(self, request: web.Request) -> web.Response:
        """Index page with usage info"""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Modbus HTTP Bridge</title></head>
        <body style="font-family: Arial; padding: 20px; background: #1a1a2e; color: #eee;">
            <h1>🔌 Modbus HTTP Bridge</h1>
            <p>This server bridges Modbus TCP traffic over HTTP.</p>
            <h2>API Endpoints:</h2>
            <ul>
                <li><code>POST /modbus</code> - Send Modbus frame (base64 encoded in JSON)</li>
                <li><code>GET /health</code> - Health check</li>
            </ul>
            <h2>Usage:</h2>
            <pre>
POST /modbus
Content-Type: application/json

{"data": "&lt;base64-encoded-modbus-frame&gt;"}
            </pre>
            <p style="color: #0f0;">✓ Bridge is running</p>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({"status": "ok", "modbus_target": f"{self.modbus_host}:{self.modbus_port}"})
    
    async def handle_modbus_request(self, request: web.Request) -> web.Response:
        """Handle Modbus request forwarding"""
        try:
            # Parse request
            data = await request.json()
            
            if 'data' not in data:
                return web.json_response({"error": "Missing 'data' field"}, status=400)
            
            # Decode base64 Modbus frame
            try:
                modbus_frame = base64.b64decode(data['data'])
            except Exception as e:
                return web.json_response({"error": f"Invalid base64: {e}"}, status=400)
            
            # Forward to Modbus server
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.modbus_host, self.modbus_port),
                    timeout=5.0
                )
                
                # Send request
                writer.write(modbus_frame)
                await writer.drain()
                
                # Read response
                response = await asyncio.wait_for(reader.read(260), timeout=5.0)
                
                # Close connection
                writer.close()
                await writer.wait_closed()
                
                # Return response as base64
                return web.json_response({
                    "data": base64.b64encode(response).decode('ascii'),
                    "length": len(response)
                })
                
            except asyncio.TimeoutError:
                return web.json_response({"error": "Modbus timeout"}, status=504)
            except ConnectionRefusedError:
                return web.json_response({"error": "Modbus connection refused"}, status=502)
            except Exception as e:
                return web.json_response({"error": f"Modbus error: {e}"}, status=502)
                
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def start(self):
        """Start the HTTP bridge server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.http_port)
        await site.start()
        console.print(f"[green]✓[/green] HTTP Bridge listening on 0.0.0.0:{self.http_port}")
    
    async def stop(self):
        """Stop the HTTP bridge server"""
        if self.runner:
            await self.runner.cleanup()


async def main():
    """Standalone HTTP bridge for testing"""
    bridge = ModbusHttpBridge(modbus_host="127.0.0.1", modbus_port=502, http_port=8080)
    await bridge.start()
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
