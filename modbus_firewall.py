"""
Modbus Firewall - Main Firewall Implementation

Transparent proxy firewall with Deep Packet Inspection and security policy enforcement.
"""

import asyncio
import signal
import sys
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import DEFAULT_CONFIG, get_function_code_name
from dpi_engine import DPIEngine, ModbusException
from security_policy import SecurityPolicyEngine, PolicyDecision
from logging_system import ModbusLogger, LogAction, get_logger


@dataclass
class ConnectionStats:
    """Statistics for a single connection"""
    client_addr: Tuple[str, int]
    requests: int = 0
    allowed: int = 0
    blocked: int = 0
    errors: int = 0


class ModbusFirewall:
    """
    Modbus TCP Firewall - Transparent Proxy with DPI
    
    Architecture:
    - Client (HMI) connects to firewall on client-facing port
    - Firewall inspects packets and enforces security policy
    - Allowed packets are forwarded to PLC
    - Responses are forwarded back to client
    """
    
    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG
        self.console = Console()
        self.logger = get_logger()
        
        # Initialize engines
        self.dpi_engine = DPIEngine()
        self.policy_engine = SecurityPolicyEngine(self.config.security)
        
        # Connection tracking
        self.connections: Dict[Tuple[str, int], ConnectionStats] = {}
        
        # Server state
        self.server: Optional[asyncio.Server] = None
        self.running = False
        
        # Global statistics
        self.total_requests = 0
        self.total_allowed = 0
        self.total_blocked = 0
        self.total_errors = 0
    
    async def handle_client(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter
    ):
        """Handle a client connection"""
        client_addr = client_writer.get_extra_info('peername')
        client_ip, client_port = client_addr
        
        self.logger.log_info(f"New connection from {client_ip}:{client_port}")
        
        # Track connection
        self.connections[client_addr] = ConnectionStats(client_addr=client_addr)
        
        # Connect to PLC
        try:
            plc_reader, plc_writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.config.network.plc_host,
                    self.config.network.plc_port
                ),
                timeout=self.config.network.connection_timeout
            )
        except asyncio.TimeoutError:
            self.logger.log_error(f"Timeout connecting to PLC at {self.config.network.plc_host}:{self.config.network.plc_port}")
            client_writer.close()
            await client_writer.wait_closed()
            return
        except Exception as e:
            self.logger.log_error(f"Failed to connect to PLC: {e}")
            client_writer.close()
            await client_writer.wait_closed()
            return
        
        self.logger.log_info(f"Connected to PLC at {self.config.network.plc_host}:{self.config.network.plc_port}")
        
        try:
            while self.running:
                # Read from client
                try:
                    data = await asyncio.wait_for(
                        client_reader.read(260),  # Max Modbus ADU size
                        timeout=60.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                if not data:
                    break
                
                # Process the request
                await self.process_request(
                    data,
                    client_ip,
                    client_port,
                    client_writer,
                    plc_reader,
                    plc_writer
                )
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.log_error(f"Connection error: {e}")
        finally:
            # Cleanup
            try:
                plc_writer.close()
                await plc_writer.wait_closed()
            except:
                pass
            
            try:
                client_writer.close()
                await client_writer.wait_closed()
            except:
                pass
            
            self.logger.log_info(f"Connection closed: {client_ip}:{client_port}")
            del self.connections[client_addr]
    
    async def process_request(
        self,
        data: bytes,
        client_ip: str,
        client_port: int,
        client_writer: asyncio.StreamWriter,
        plc_reader: asyncio.StreamReader,
        plc_writer: asyncio.StreamWriter
    ):
        """Process a single Modbus request"""
        self.total_requests += 1
        conn_stats = self.connections.get((client_ip, client_port))
        if conn_stats:
            conn_stats.requests += 1
        
        # Parse the frame
        frame, error = self.dpi_engine.parse_frame(data)
        
        if error:
            # Invalid frame - log and drop
            self.total_errors += 1
            if conn_stats:
                conn_stats.errors += 1
            self.logger.log_transaction(
                transaction_id=0,
                source_ip=client_ip,
                source_port=client_port,
                function_code=0,
                action=LogAction.ERROR,
                reason=error
            )
            return
        
        # Validate frame integrity
        valid, integrity_error = self.dpi_engine.validate_frame_integrity(frame)
        if not valid:
            self.total_errors += 1
            if conn_stats:
                conn_stats.errors += 1
            self.logger.log_transaction(
                transaction_id=frame.transaction_id,
                source_ip=client_ip,
                source_port=client_port,
                function_code=frame.function_code,
                action=LogAction.ERROR,
                reason=integrity_error,
                unit_id=frame.unit_id
            )
            return
        
        # Evaluate security policy
        policy_result = self.policy_engine.evaluate(frame, client_ip)
        
        if policy_result.is_allowed:
            # Forward to PLC
            self.total_allowed += 1
            if conn_stats:
                conn_stats.allowed += 1
            
            self.logger.log_transaction(
                transaction_id=frame.transaction_id,
                source_ip=client_ip,
                source_port=client_port,
                function_code=frame.function_code,
                action=LogAction.ALLOW,
                reason=policy_result.reason,
                unit_id=frame.unit_id,
                data_length=len(frame.data)
            )
            
            # Forward request to PLC
            plc_writer.write(data)
            await plc_writer.drain()
            
            # Wait for response from PLC
            try:
                response = await asyncio.wait_for(
                    plc_reader.read(260),
                    timeout=5.0
                )
                
                if response:
                    # Forward response to client
                    client_writer.write(response)
                    await client_writer.drain()
            except asyncio.TimeoutError:
                self.logger.log_warning(f"Timeout waiting for PLC response (TxID: {frame.transaction_id})")
        
        else:
            # Block request
            self.total_blocked += 1
            if conn_stats:
                conn_stats.blocked += 1
            
            self.logger.log_transaction(
                transaction_id=frame.transaction_id,
                source_ip=client_ip,
                source_port=client_port,
                function_code=frame.function_code,
                action=LogAction.BLOCK,
                reason=policy_result.reason,
                unit_id=frame.unit_id,
                data_length=len(frame.data)
            )
            
            # Send exception response to client
            exception_response = self.dpi_engine.create_exception_response(
                frame,
                ModbusException.ILLEGAL_FUNCTION
            )
            client_writer.write(exception_response)
            await client_writer.drain()
    
    async def start(self):
        """Start the firewall server"""
        self.logger.print_banner()
        
        # Print configuration
        self.console.print(f"\n[bold cyan]Configuration:[/bold cyan]")
        self.console.print(f"  Listen: {self.config.network.firewall_host}:{self.config.network.firewall_port}")
        self.console.print(f"  PLC: {self.config.network.plc_host}:{self.config.network.plc_port}")
        self.console.print()
        
        # Print security policy
        self.console.print(Panel(
            self.policy_engine.get_policy_summary(),
            title="Security Policy",
            border_style="yellow"
        ))
        
        self.running = True
        
        # Start server
        self.server = await asyncio.start_server(
            self.handle_client,
            self.config.network.firewall_host,
            self.config.network.firewall_port
        )
        
        addr = self.server.sockets[0].getsockname()
        self.console.print(f"\n[green]✓[/green] Firewall listening on {addr[0]}:{addr[1]}")
        self.console.print(f"[green]✓[/green] Ready to proxy Modbus traffic\n")
        self.console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        async with self.server:
            try:
                await self.server.serve_forever()
            except asyncio.CancelledError:
                pass
    
    async def stop(self):
        """Stop the firewall server"""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Print final statistics
        self.print_statistics()
    
    def print_statistics(self):
        """Print firewall statistics"""
        table = Table(title="Firewall Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right")
        
        table.add_row("Total Requests", str(self.total_requests))
        table.add_row("Allowed", f"[green]{self.total_allowed}[/green]")
        table.add_row("Blocked", f"[red]{self.total_blocked}[/red]")
        table.add_row("Errors", f"[yellow]{self.total_errors}[/yellow]")
        
        self.console.print(table)
        
        # DPI stats
        dpi_stats = self.dpi_engine.get_stats()
        self.console.print(f"\n[dim]DPI Stats: {dpi_stats}[/dim]")


async def main():
    """Main entry point"""
    firewall = ModbusFirewall()
    
    # Handle shutdown
    loop = asyncio.get_event_loop()
    
    def shutdown():
        loop.create_task(firewall.stop())
    
    # Note: signal handling in asyncio on Windows is limited
    # We'll handle it via KeyboardInterrupt
    
    try:
        await firewall.start()
    except KeyboardInterrupt:
        pass
    finally:
        await firewall.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nFirewall stopped.")
