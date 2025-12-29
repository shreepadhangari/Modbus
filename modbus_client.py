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
from rich.prompt import Prompt, IntPrompt, Confirm

from config import DEFAULT_CONFIG, ModbusFunctionCode


class ModbusHMI:
    """Interactive HMI Client for Modbus operations"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 502):
        self.console = Console()
        self.host = host
        self.port = port
        self.client = None
        self.security_policy = DEFAULT_CONFIG.security
    
    def get_operation_status(self, function_code: int) -> str:
        """Get the allowed/blocked status for a function code based on security policy"""
        if function_code in self.security_policy.allowed_function_codes:
            return "[green]✓ Allowed[/green]"
        elif function_code in self.security_policy.blocked_function_codes:
            return "[red]✗ Blocked[/red]"
        else:
            return "[yellow]? Unknown[/yellow]"
    
    def is_operation_allowed(self, function_code: int) -> bool:
        """Check if a function code is allowed by security policy"""
        return function_code in self.security_policy.allowed_function_codes
        
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
            table.add_column("Name", width=12)
            table.add_column("Raw", justify="right")
            table.add_column("Scaled", justify="right")
            
            # Same scaling as server
            reg_info = {
                0: ("Temp SP", "°C", 10),
                1: ("Press SP", "kPa", 10),
                2: ("Flow SP", "L/min", 10),
                3: ("Level SP", "%", 10),
                4: ("Motor Spd", "%", 10),
                5: ("Mode", "", 1),
            }
            
            for i, val in enumerate(result):
                addr = start_addr + i
                if addr in reg_info:
                    name, unit, scale = reg_info[addr]
                    if addr == 5:
                        scaled = "Auto" if val == 0 else "Manual"
                    elif unit:
                        scaled = f"{val/scale:.1f} {unit}"
                    else:
                        scaled = str(val)
                else:
                    name = f"HR {addr}"
                    scaled = str(val)
                table.add_row(str(addr), name, str(val), scaled)
            
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
            table.add_column("Name", width=12)
            table.add_column("Raw", justify="right")
            table.add_column("Scaled", justify="right")
            
            # Same scaling as server
            reg_info = {
                0: ("Temperature", "°C", 10),
                1: ("Pressure", "kPa", 10),
                2: ("Flow Rate", "L/min", 10),
                3: ("Tank Level", "%", 10),
                4: ("Voltage", "V", 10),
                5: ("Current", "A", 10),
                6: ("Power", "kW", 10),
                7: ("Frequency", "Hz", 10),
            }
            
            for i, val in enumerate(result):
                addr = start_addr + i
                if addr in reg_info:
                    name, unit, scale = reg_info[addr]
                    scaled = f"{val/scale:.1f} {unit}"
                else:
                    name = f"IR {addr}"
                    scaled = str(val)
                table.add_row(str(addr), name, str(val), scaled)
            
            self.console.print(table)
        else:
            self.console.print("[red]✗[/red] Read failed (possibly blocked by firewall)")
    
    def write_single_coil(self, address: int, value: bool):
        """Write single coil (FC 05)"""
        self.console.print(f"\n[yellow]⚠ Attempting to write coil {address} = {value}...[/yellow]")
        
        is_allowed = self.is_operation_allowed(ModbusFunctionCode.WRITE_SINGLE_COIL)
        if not is_allowed:
            self.console.print("[dim]This operation is blocked by security policy[/dim]")
        
        result = self.client.write_single_coil(address, value)
        
        if result:
            self.console.print(f"[green]✓[/green] Write succeeded! Coil {address} set to {value}")
        else:
            # Debug: show actual error
            last_error = self.client.last_error
            last_error_txt = self.client.last_error_as_txt
            self.console.print(f"[dim]Debug: error_code={last_error}, error_txt={last_error_txt}[/dim]")
            
            if is_allowed:
                self.console.print("[red]✗[/red] Write failed (see debug info above)")
            else:
                self.console.print("[green]✓[/green] Write was blocked by firewall (as expected)")
    
    def write_single_register(self, address: int, value: int):
        """Write single register (FC 06)"""
        self.console.print(f"\n[yellow]⚠ Attempting to write register {address} = {value}...[/yellow]")
        
        is_allowed = self.is_operation_allowed(ModbusFunctionCode.WRITE_SINGLE_REGISTER)
        if not is_allowed:
            self.console.print("[dim]This operation is blocked by security policy[/dim]")
        
        result = self.client.write_single_register(address, value)
        
        if result:
            self.console.print(f"[green]✓[/green] Write succeeded! Register {address} set to {value}")
        else:
            if is_allowed:
                self.console.print("[red]✗[/red] Write failed (connection issue)")
            else:
                self.console.print("[green]✓[/green] Write was blocked by firewall (as expected)")
    
    def write_multiple_registers(self, start_addr: int, values: list):
        """Write multiple registers (FC 16)"""
        self.console.print(f"\n[yellow]⚠ Attempting to write {len(values)} registers from address {start_addr}...[/yellow]")
        self.console.print(f"[dim]Values: {values}[/dim]")
        
        is_allowed = self.is_operation_allowed(ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS)
        if not is_allowed:
            self.console.print("[dim]This operation is blocked by security policy[/dim]")
        
        result = self.client.write_multiple_registers(start_addr, values)
        
        if result:
            self.console.print(f"[green]✓[/green] Write succeeded! Registers {start_addr}-{start_addr + len(values) - 1} updated")
        else:
            if is_allowed:
                self.console.print("[red]✗[/red] Write failed (connection issue)")
            else:
                self.console.print("[green]✓[/green] Write was blocked by firewall (as expected)")
    
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
            self.console.print(f"  [1] Read Coils (FC 01) {self.get_operation_status(ModbusFunctionCode.READ_COILS)}")
            self.console.print(f"  [2] Read Discrete Inputs (FC 02) {self.get_operation_status(ModbusFunctionCode.READ_DISCRETE_INPUTS)}")
            self.console.print(f"  [3] Read Holding Registers (FC 03) {self.get_operation_status(ModbusFunctionCode.READ_HOLDING_REGISTERS)}")
            self.console.print(f"  [4] Read Input Registers (FC 04) {self.get_operation_status(ModbusFunctionCode.READ_INPUT_REGISTERS)}")
            self.console.print(f"  [5] Write Single Coil (FC 05) {self.get_operation_status(ModbusFunctionCode.WRITE_SINGLE_COIL)}")
            self.console.print(f"  [6] Write Single Register (FC 06) {self.get_operation_status(ModbusFunctionCode.WRITE_SINGLE_REGISTER)}")
            self.console.print(f"  [7] Write Multiple Registers (FC 16) {self.get_operation_status(ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS)}")
            self.console.print("  [8] Run All Tests")
            self.console.print("  [9] Show Security Policy")
            self.console.print("  [0] Exit")
            
            try:
                choice = Prompt.ask("\nSelect operation", default="0")
                
                if choice == "1":
                    addr = IntPrompt.ask("Start address", default=0)
                    count = IntPrompt.ask("Number of coils", default=10)
                    self.read_coils(addr, count)
                elif choice == "2":
                    addr = IntPrompt.ask("Start address", default=0)
                    count = IntPrompt.ask("Number of inputs", default=10)
                    self.read_discrete_inputs(addr, count)
                elif choice == "3":
                    addr = IntPrompt.ask("Start address", default=0)
                    count = IntPrompt.ask("Number of registers", default=10)
                    self.read_holding_registers(addr, count)
                elif choice == "4":
                    addr = IntPrompt.ask("Start address", default=0)
                    count = IntPrompt.ask("Number of registers", default=10)
                    self.read_input_registers(addr, count)
                elif choice == "5":
                    addr = IntPrompt.ask("Coil address", default=0)
                    val_str = Prompt.ask("Value (true/false)", default="true")
                    val = val_str.lower() in ("true", "1", "yes", "on")
                    self.write_single_coil(addr, val)
                elif choice == "6":
                    addr = IntPrompt.ask("Register address", default=0)
                    val = IntPrompt.ask("Value (0-65535)", default=0)
                    self.write_single_register(addr, val)
                elif choice == "7":
                    addr = IntPrompt.ask("Start address", default=0)
                    val_str = Prompt.ask("Values (comma-separated)", default="100,200,300")
                    values = [int(v.strip()) for v in val_str.split(",")]
                    self.write_multiple_registers(addr, values)
                elif choice == "8":
                    self.run_all_tests()
                elif choice == "9":
                    self.show_security_policy()
                elif choice == "0":
                    break
                else:
                    self.console.print("[red]Invalid choice[/red]")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
        
        self.disconnect()
    
    def show_security_policy(self):
        """Display current security policy configuration"""
        from config import get_function_code_name
        
        lines = ["[bold cyan]Current Security Policy[/bold cyan]\n"]
        
        lines.append("[green]Allowed Function Codes:[/green]")
        for fc in sorted(self.security_policy.allowed_function_codes):
            lines.append(f"  • 0x{fc:02X}: {get_function_code_name(fc)}")
        
        lines.append("\n[red]Blocked Function Codes:[/red]")
        for fc in sorted(self.security_policy.blocked_function_codes):
            lines.append(f"  • 0x{fc:02X}: {get_function_code_name(fc)}")
        
        lines.append(f"\n[yellow]Write-Allowed IPs:[/yellow] {self.security_policy.write_allowed_ips or 'None'}")
        lines.append(f"[yellow]Rate Limit:[/yellow] {self.security_policy.rate_limit} req/s per client")
        
        self.console.print(Panel("\n".join(lines), border_style="cyan"))
    
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
    parser.add_argument("--remote", metavar="URL", help="Remote HTTP Bridge URL (e.g., https://xxx.loca.lt)")
    parser.add_argument("--test", action="store_true", help="Run automated tests")
    
    args = parser.parse_args()
    
    # Check if using remote HTTP mode
    if args.remote:
        from http_client import ModbusHttpClient
        console = Console()
        
        console.print(f"\n[bold cyan]Connecting to Remote HTTP Bridge[/bold cyan]")
        console.print(f"URL: {args.remote}\n")
        
        # Create HTTP-based HMI
        hmi = ModbusHMI(host=args.host, port=args.port)
        hmi.client = ModbusHttpClient(args.remote)
        
        if hmi.client.open():
            console.print(f"[green]✓[/green] Connected to HTTP Bridge")
            if args.test:
                hmi.run_all_tests()
            else:
                hmi.run_interactive()
            hmi.client.close()
        else:
            console.print(f"[red]✗[/red] Failed to connect to HTTP Bridge")
            console.print(f"[dim]Error: {hmi.client.last_error_as_txt}[/dim]")
    else:
        # Normal TCP mode
        hmi = ModbusHMI(host=args.host, port=args.port)
        
        if args.test:
            if hmi.connect():
                hmi.run_all_tests()
                hmi.disconnect()
        else:
            hmi.run_interactive()


if __name__ == "__main__":
    main()
