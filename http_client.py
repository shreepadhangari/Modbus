"""
Modbus HTTP Client Wrapper

Wraps Modbus operations in HTTP requests for use with the HTTP Bridge.
This allows connecting to a remote Modbus server through LocalTunnel.
"""

import requests
import base64
import struct
from typing import Optional, List
from rich.console import Console

console = Console()


class ModbusHttpClient:
    """
    HTTP-based Modbus client that communicates with the HTTP Bridge.
    Wraps pyModbusTCP-like API but sends requests over HTTP.
    """
    
    def __init__(self, url: str, timeout: float = 10.0):
        """
        Initialize HTTP Modbus client.
        
        Args:
            url: Base URL of the HTTP bridge (e.g., https://xxx.loca.lt)
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip('/')
        self.timeout = timeout
        self.transaction_id = 0
        self.unit_id = 1
        self.last_error = 0
        self.last_error_as_txt = ""
    
    def _next_transaction_id(self) -> int:
        """Get next transaction ID"""
        self.transaction_id = (self.transaction_id + 1) % 65536
        return self.transaction_id
    
    def _build_request_frame(self, function_code: int, data: bytes) -> bytes:
        """Build a Modbus TCP frame"""
        tx_id = self._next_transaction_id()
        protocol_id = 0
        length = 2 + len(data)  # Unit ID + Function Code + Data
        
        header = struct.pack('>HHHBB', tx_id, protocol_id, length, self.unit_id, function_code)
        return header + data
    
    def _send_request(self, frame: bytes) -> Optional[bytes]:
        """Send Modbus frame via HTTP and return response"""
        try:
            # Encode frame as base64
            payload = {"data": base64.b64encode(frame).decode('ascii')}
            
            # Send to bridge
            response = requests.post(
                f"{self.url}/modbus",
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    return base64.b64decode(data['data'])
                else:
                    self.last_error = 1
                    self.last_error_as_txt = data.get('error', 'Unknown error')
                    return None
            else:
                self.last_error = response.status_code
                self.last_error_as_txt = f"HTTP {response.status_code}"
                return None
                
        except requests.exceptions.Timeout:
            self.last_error = 2
            self.last_error_as_txt = "Timeout"
            return None
        except requests.exceptions.ConnectionError:
            self.last_error = 3
            self.last_error_as_txt = "Connection failed"
            return None
        except Exception as e:
            self.last_error = 4
            self.last_error_as_txt = str(e)
            return None
    
    def _parse_read_response(self, response: bytes, expected_fc: int) -> Optional[List[int]]:
        """Parse a Modbus read response"""
        if not response or len(response) < 9:
            return None
        
        # Parse header
        # tx_id, proto_id, length, unit_id, fc = struct.unpack('>HHHBB', response[:8])
        fc = response[7]
        
        # Check for exception
        if fc >= 0x80:
            self.last_error = 7
            self.last_error_as_txt = "modbus exception"
            return None
        
        if fc != expected_fc:
            self.last_error = 5
            self.last_error_as_txt = f"Unexpected FC: {fc}"
            return None
        
        byte_count = response[8]
        data = response[9:9+byte_count]
        
        if expected_fc in [1, 2]:  # Coils or Discrete Inputs
            # Unpack bits
            result = []
            for byte in data:
                for bit in range(8):
                    result.append(bool(byte & (1 << bit)))
            return result
        else:  # Registers
            # Unpack 16-bit values
            result = []
            for i in range(0, len(data), 2):
                if i + 1 < len(data):
                    result.append(struct.unpack('>H', data[i:i+2])[0])
            return result
    
    def open(self) -> bool:
        """Test connection to HTTP bridge"""
        try:
            response = requests.get(f"{self.url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def close(self) -> None:
        """No-op for HTTP client"""
        pass
    
    def read_coils(self, address: int, count: int) -> Optional[List[bool]]:
        """Read coils (FC 01)"""
        data = struct.pack('>HH', address, count)
        frame = self._build_request_frame(1, data)
        response = self._send_request(frame)
        result = self._parse_read_response(response, 1)
        return result[:count] if result else None
    
    def read_discrete_inputs(self, address: int, count: int) -> Optional[List[bool]]:
        """Read discrete inputs (FC 02)"""
        data = struct.pack('>HH', address, count)
        frame = self._build_request_frame(2, data)
        response = self._send_request(frame)
        result = self._parse_read_response(response, 2)
        return result[:count] if result else None
    
    def read_holding_registers(self, address: int, count: int) -> Optional[List[int]]:
        """Read holding registers (FC 03)"""
        data = struct.pack('>HH', address, count)
        frame = self._build_request_frame(3, data)
        response = self._send_request(frame)
        return self._parse_read_response(response, 3)
    
    def read_input_registers(self, address: int, count: int) -> Optional[List[int]]:
        """Read input registers (FC 04)"""
        data = struct.pack('>HH', address, count)
        frame = self._build_request_frame(4, data)
        response = self._send_request(frame)
        return self._parse_read_response(response, 4)
    
    def write_single_coil(self, address: int, value: bool) -> bool:
        """Write single coil (FC 05)"""
        coil_value = 0xFF00 if value else 0x0000
        data = struct.pack('>HH', address, coil_value)
        frame = self._build_request_frame(5, data)
        response = self._send_request(frame)
        
        if response and len(response) >= 8:
            fc = response[7]
            return fc == 5  # Success if FC matches
        return False
    
    def write_single_register(self, address: int, value: int) -> bool:
        """Write single register (FC 06)"""
        data = struct.pack('>HH', address, value)
        frame = self._build_request_frame(6, data)
        response = self._send_request(frame)
        
        if response and len(response) >= 8:
            fc = response[7]
            return fc == 6
        return False
    
    def write_multiple_registers(self, address: int, values: List[int]) -> bool:
        """Write multiple registers (FC 16)"""
        count = len(values)
        byte_count = count * 2
        
        # Pack: address, count, byte_count, then values
        data = struct.pack('>HHB', address, count, byte_count)
        for v in values:
            data += struct.pack('>H', v)
        
        frame = self._build_request_frame(16, data)
        response = self._send_request(frame)
        
        if response and len(response) >= 8:
            fc = response[7]
            return fc == 16
        return False


# Test the HTTP client
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test HTTP Modbus Client")
    parser.add_argument("url", help="HTTP Bridge URL (e.g., https://xxx.loca.lt)")
    args = parser.parse_args()
    
    client = ModbusHttpClient(args.url)
    
    if client.open():
        console.print("[green]✓[/green] Connected to HTTP Bridge")
        
        # Test read
        coils = client.read_coils(0, 10)
        if coils:
            console.print(f"Coils: {coils}")
        else:
            console.print(f"[red]Read failed: {client.last_error_as_txt}[/red]")
    else:
        console.print("[red]✗[/red] Failed to connect")
