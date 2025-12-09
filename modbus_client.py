"""
Modbus Firewall - HMI Client

Interactive Modbus client for testing the firewall.
"""

import sys
import time
from pyModbusTCP.client import ModbusClient
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt

from config import DEFAULT_CONFIG, ModbusFunctionCode


class ModbusHMI:
    """Interactive HMI Client for Modbus operations"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 502):
        self.console = Console()
        self.host = host
        self.port = port
        self.client = None
        
    def connect(self) -> bool:
        """Connect to the Modbus server (through firewall)"""
        self.client = ModbusClient(host=self.host, port=self.port, auto_open=True)
        self.client.timeout = 5.0
        
        if self.client.open():
            self.console.print(f"[green]✓[/green] Connected to {self.host}:{self.port}")
            return True
        else:
            self.console.print(f"[red]✗[/red] Failed to connect to {self.host}:{self.port}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        if self.client:
            self.client.close()
            self.console.print("[yellow]Disconnected[/yellow]")
    
    def read_coils(self, start_addr: int = 0, count: int = 10):
        """Read coils (FC 01)"""
        self.console.print(f"\n[cyan]Reading {count} coils from address {start_addr}...[/cyan]")
        
        result = self.client.read_coils(start_addr, count)
        
        if result is not None:
            table = Table(title="Coils (FC 01)")
            table.add_column("Address", justify="right")
            table.add_column("Value")
            
            for i, val in enumerate(result):
                status = "[green]ON[/green]" if val else "[red]OFF[/red]"
                table.add_row(str(start_addr + i), status)
            
            self.console.print(table)
        else:
            self.console.print("[red]✗[/red] Read failed (possibly blocked by firewall)")
    
    def read_discrete_inputs(self, start_addr: int = 0, count: int = 10):
        """Read discrete inputs (FC 02)"""
        self.console.print(f"\n[cyan]Reading {count} discrete inputs from address {start_addr}...[/cyan]")
        
        result = self.client.read_discrete_inputs(start_addr, count)
        
        if result is not None:
            table = Table(title="Discrete Inputs (FC 02)")
            table.add_column("Address", justify="right")
            table.add_column("Value")
            
            for i, val in enumerate(result):
                status = "[green]ON[/green]" if val else "[red]OFF[/red]"
                table.add_row(str(start_addr + i), status)
            
            self.console.print(table)
        else:
            self.console.print("[red]✗[/red] Read failed (possibly blocked by firewall)")
    
    def read_holding_registers(self, start_addr: int = 0, count: int = 10):
        """Read holding registers (FC 03)"""
        self.console.print(f"\n[cyan]Reading {count} holding registers from address {start_addr}...[/cyan]")
        
        result = self.client.read_holding_registers(start_addr, count)
        
        if result is not None:
            table = Table(title="Holding Registers (FC 03)")
            table.add_column("Address", justify="right")
            table.add_column("Value", justify="right")
            table.add_column("Hex", justify="right")
            
            for i, val in enumerate(result):
                table.add_row(str(start_addr + i), str(val), f"0x{val:04X}")
            
            self.console.print(table)
        else:
            self.console.print("[red]✗[/red] Read failed (possibly blocked by firewall)")
    
    def read_input_registers(self, start_addr: int = 0, count: int = 10):
        """Read input registers (FC 04)"""
        self.console.print(f"\n[cyan]Reading {count} input registers from address {start_addr}...[/cyan]")
        
        result = self.client.read_input_registers(start_addr, count)
        
        if result is not None:
            table = Table(title="Input Registers (FC 04)")
            table.add_column("Address", justify="right")
            table.add_column("Value", justify="right")
            table.add_column("Scaled", justify="right")
            
            names = ["Temp (°C)", "Pressure (kPa)", "Flow (L/min)", "Level (%)", "Voltage (V)", "Current (A)"]
            
            for i, val in enumerate(result):
                scaled = f"{val/10:.1f}" if i < len(names) else str(val)
                name = names[i] if i < len(names) else ""
                table.add_row(f"{start_addr + i} {name}", str(val), scaled)
            
            self.console.print(table)
        else:
            self.console.print("[red]✗[/red] Read failed (possibly blocked by firewall)")
    
    def write_single_coil(self, address: int, value: bool):
        """Write single coil (FC 05) - Should be blocked by firewall"""
        self.console.print(f"\n[yellow]⚠ Attempting to write coil {address} = {value}...[/yellow]")
        self.console.print("[dim]This should be BLOCKED by the firewall[/dim]")
        
        result = self.client.write_single_coil(address, value)
        
        if result:
            self.console.print("[red]⚠ WARNING: Write succeeded! Firewall may not be working![/red]")
        else:
            self.console.print("[green]✓[/green] Write was blocked (as expected)")
    
    def write_single_register(self, address: int, value: int):
        """Write single register (FC 06) - Should be blocked by firewall"""
        self.console.print(f"\n[yellow]⚠ Attempting to write register {address} = {value}...[/yellow]")
        self.console.print("[dim]This should be BLOCKED by the firewall[/dim]")
        
        result = self.client.write_single_register(address, value)
        
        if result:
            self.console.print("[red]⚠ WARNING: Write succeeded! Firewall may not be working![/red]")
        else:
            self.console.print("[green]✓[/green] Write was blocked (as expected)")
    
    def write_multiple_registers(self, start_addr: int, values: list):
        """Write multiple registers (FC 16) - Should be blocked by firewall"""
        self.console.print(f"\n[yellow]⚠ Attempting to write {len(values)} registers from address {start_addr}...[/yellow]")
        self.console.print("[dim]This should be BLOCKED by the firewall[/dim]")
        
        result = self.client.write_multiple_registers(start_addr, values)
        
        if result:
            self.console.print("[red]⚠ WARNING: Write succeeded! Firewall may not be working![/red]")
        else:
            self.console.print("[green]✓[/green] Write was blocked (as expected)")
    
    def run_interactive(self):
        """Run interactive menu"""
        self.console.print(Panel(
            "[bold cyan]Modbus HMI Client[/bold cyan]\n"
            "[dim]Interactive client for testing Modbus Firewall[/dim]",
            border_style="cyan"
        ))
        
        if not self.connect():
            return
        
        while True:
            self.console.print("\n[bold]Operations:[/bold]")
            self.console.print("  [1] Read Coils (FC 01) [green]✓ Allowed[/green]")
            self.console.print("  [2] Read Discrete Inputs (FC 02) [green]✓ Allowed[/green]")
            self.console.print("  [3] Read Holding Registers (FC 03) [green]✓ Allowed[/green]")
            self.console.print("  [4] Read Input Registers (FC 04) [green]✓ Allowed[/green]")
            self.console.print("  [5] Write Single Coil (FC 05) [red]✗ Blocked[/red]")
            self.console.print("  [6] Write Single Register (FC 06) [red]✗ Blocked[/red]")
            self.console.print("  [7] Write Multiple Registers (FC 16) [red]✗ Blocked[/red]")
            self.console.print("  [8] Run All Tests")
            self.console.print("  [0] Exit")
            
            try:
                choice = Prompt.ask("\nSelect operation", default="0")
                
                if choice == "1":
                    self.read_coils()
                elif choice == "2":
                    self.read_discrete_inputs()
                elif choice == "3":
                    self.read_holding_registers()
                elif choice == "4":
                    self.read_input_registers()
                elif choice == "5":
                    self.write_single_coil(0, True)
                elif choice == "6":
                    self.write_single_register(0, 999)
                elif choice == "7":
                    self.write_multiple_registers(0, [100, 200, 300])
                elif choice == "8":
                    self.run_all_tests()
                elif choice == "0":
                    break
                else:
                    self.console.print("[red]Invalid choice[/red]")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
        
        self.disconnect()
    
    def run_all_tests(self):
        """Run all tests sequentially"""
        self.console.print("\n[bold cyan]Running All Tests...[/bold cyan]")
        self.console.print("=" * 50)
        
        # Read operations (should succeed)
        self.console.print("\n[bold green]--- Read Operations (Should Pass) ---[/bold green]")
        self.read_coils(0, 5)
        time.sleep(0.5)
        self.read_discrete_inputs(0, 5)
        time.sleep(0.5)
        self.read_holding_registers(0, 6)
        time.sleep(0.5)
        self.read_input_registers(0, 6)
        time.sleep(0.5)
        
        # Write operations (should be blocked)
        self.console.print("\n[bold red]--- Write Operations (Should Be Blocked) ---[/bold red]")
        self.write_single_coil(0, True)
        time.sleep(0.5)
        self.write_single_register(0, 999)
        time.sleep(0.5)
        self.write_multiple_registers(0, [100, 200, 300])
        
        self.console.print("\n[bold cyan]Tests Complete![/bold cyan]")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Modbus HMI Client")
    parser.add_argument("--host", default="127.0.0.1", help="Firewall host address")
    parser.add_argument("--port", type=int, default=502, help="Firewall port")
    parser.add_argument("--test", action="store_true", help="Run automated tests")
    
    args = parser.parse_args()
    
    hmi = ModbusHMI(host=args.host, port=args.port)
    
    if args.test:
        if hmi.connect():
            hmi.run_all_tests()
            hmi.disconnect()
    else:
        hmi.run_interactive()


if __name__ == "__main__":
    main()
