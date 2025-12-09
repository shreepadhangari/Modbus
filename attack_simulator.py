"""
Modbus Firewall - Attack Simulator

Security testing suite for validating firewall effectiveness.
"""

import socket
import struct
import time
import random
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import ModbusFunctionCode


class AttackSimulator:
    """Security testing suite for Modbus Firewall"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 502):
        self.console = Console()
        self.host = host
        self.port = port
        self.transaction_id = 0
        
        # Test results
        self.results = {
            'passed': 0,
            'failed': 0,
            'tests': []
        }
    
    def _get_transaction_id(self) -> int:
        """Get next transaction ID"""
        self.transaction_id = (self.transaction_id + 1) % 65536
        return self.transaction_id
    
    def _build_modbus_request(
        self,
        function_code: int,
        data: bytes,
        unit_id: int = 1
    ) -> bytes:
        """Build a Modbus TCP request frame"""
        pdu = bytes([function_code]) + data
        length = len(pdu) + 1  # PDU + Unit ID
        
        # MBAP Header
        header = struct.pack(
            '>HHHB',
            self._get_transaction_id(),  # Transaction ID
            0x0000,                       # Protocol ID
            length,                       # Length
            unit_id                       # Unit ID
        )
        
        return header + pdu
    
    def _send_request(self, request: bytes, timeout: float = 5.0) -> tuple:
        """
        Send a request and return (success, response or error)
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.host, self.port))
            sock.send(request)
            
            response = sock.recv(260)
            sock.close()
            
            return True, response
        except socket.timeout:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)
    
    def _is_exception_response(self, response: bytes) -> bool:
        """Check if response is an exception"""
        if len(response) >= 8:
            function_code = response[7]
            return function_code >= 0x80
        return False
    
    def _record_result(self, test_name: str, passed: bool, details: str):
        """Record test result"""
        self.results['tests'].append({
            'name': test_name,
            'passed': passed,
            'details': details
        })
        if passed:
            self.results['passed'] += 1
        else:
            self.results['failed'] += 1
    
    # ==================== Test Cases ====================
    
    def test_read_holding_registers(self) -> bool:
        """Test: Read Holding Registers (FC 03) - Should PASS"""
        test_name = "Read Holding Registers (FC 03)"
        self.console.print(f"\n[cyan]Testing:[/cyan] {test_name}")
        
        # Build read request: start=0, count=10
        data = struct.pack('>HH', 0, 10)
        request = self._build_modbus_request(
            ModbusFunctionCode.READ_HOLDING_REGISTERS,
            data
        )
        
        success, response = self._send_request(request)
        
        if success and not self._is_exception_response(response):
            self.console.print("[green]  ✓ PASS[/green] - Read allowed through firewall")
            self._record_result(test_name, True, "Read allowed as expected")
            return True
        else:
            self.console.print(f"[red]  ✗ FAIL[/red] - Read was blocked (unexpected)")
            self._record_result(test_name, False, f"Read blocked: {response}")
            return False
    
    def test_read_input_registers(self) -> bool:
        """Test: Read Input Registers (FC 04) - Should PASS"""
        test_name = "Read Input Registers (FC 04)"
        self.console.print(f"\n[cyan]Testing:[/cyan] {test_name}")
        
        data = struct.pack('>HH', 0, 10)
        request = self._build_modbus_request(
            ModbusFunctionCode.READ_INPUT_REGISTERS,
            data
        )
        
        success, response = self._send_request(request)
        
        if success and not self._is_exception_response(response):
            self.console.print("[green]  ✓ PASS[/green] - Read allowed through firewall")
            self._record_result(test_name, True, "Read allowed as expected")
            return True
        else:
            self.console.print(f"[red]  ✗ FAIL[/red] - Read was blocked (unexpected)")
            self._record_result(test_name, False, f"Read blocked: {response}")
            return False
    
    def test_write_single_register(self) -> bool:
        """Test: Write Single Register (FC 06) - Should be BLOCKED"""
        test_name = "Write Single Register Attack (FC 06)"
        self.console.print(f"\n[cyan]Testing:[/cyan] {test_name}")
        
        # Attempt to write register 0 with value 999
        data = struct.pack('>HH', 0, 999)
        request = self._build_modbus_request(
            ModbusFunctionCode.WRITE_SINGLE_REGISTER,
            data
        )
        
        success, response = self._send_request(request)
        
        if success and self._is_exception_response(response):
            self.console.print("[green]  ✓ PASS[/green] - Write blocked by firewall (exception returned)")
            self._record_result(test_name, True, "Write blocked as expected")
            return True
        elif not success:
            self.console.print("[green]  ✓ PASS[/green] - Write blocked (connection dropped)")
            self._record_result(test_name, True, "Write blocked as expected")
            return True
        else:
            self.console.print(f"[red]  ✗ FAIL[/red] - Write was allowed! SECURITY BREACH!")
            self._record_result(test_name, False, "Write allowed - firewall bypassed!")
            return False
    
    def test_write_multiple_registers(self) -> bool:
        """Test: Write Multiple Registers (FC 16) - Should be BLOCKED"""
        test_name = "Write Multiple Registers Attack (FC 16)"
        self.console.print(f"\n[cyan]Testing:[/cyan] {test_name}")
        
        # Attempt to write 3 registers starting at address 0
        values = [100, 200, 300]
        data = struct.pack('>HHB', 0, len(values), len(values) * 2)
        for v in values:
            data += struct.pack('>H', v)
        
        request = self._build_modbus_request(
            ModbusFunctionCode.WRITE_MULTIPLE_REGISTERS,
            data
        )
        
        success, response = self._send_request(request)
        
        if success and self._is_exception_response(response):
            self.console.print("[green]  ✓ PASS[/green] - Write blocked by firewall")
            self._record_result(test_name, True, "Write blocked as expected")
            return True
        elif not success:
            self.console.print("[green]  ✓ PASS[/green] - Write blocked (connection dropped)")
            self._record_result(test_name, True, "Write blocked as expected")
            return True
        else:
            self.console.print(f"[red]  ✗ FAIL[/red] - Write was allowed! SECURITY BREACH!")
            self._record_result(test_name, False, "Write allowed - firewall bypassed!")
            return False
    
    def test_write_single_coil(self) -> bool:
        """Test: Write Single Coil (FC 05) - Should be BLOCKED"""
        test_name = "Write Single Coil Attack (FC 05)"
        self.console.print(f"\n[cyan]Testing:[/cyan] {test_name}")
        
        # Attempt to write coil 0 ON (0xFF00)
        data = struct.pack('>HH', 0, 0xFF00)
        request = self._build_modbus_request(
            ModbusFunctionCode.WRITE_SINGLE_COIL,
            data
        )
        
        success, response = self._send_request(request)
        
        if success and self._is_exception_response(response):
            self.console.print("[green]  ✓ PASS[/green] - Write blocked by firewall")
            self._record_result(test_name, True, "Write blocked as expected")
            return True
        elif not success:
            self.console.print("[green]  ✓ PASS[/green] - Write blocked")
            self._record_result(test_name, True, "Write blocked as expected")
            return True
        else:
            self.console.print(f"[red]  ✗ FAIL[/red] - Write was allowed! SECURITY BREACH!")
            self._record_result(test_name, False, "Write allowed - firewall bypassed!")
            return False
    
    def test_malformed_protocol_id(self) -> bool:
        """Test: Malformed packet with invalid protocol ID"""
        test_name = "Malformed Packet - Invalid Protocol ID"
        self.console.print(f"\n[cyan]Testing:[/cyan] {test_name}")
        
        # Build packet with wrong protocol ID (should be 0x0000)
        malformed = struct.pack(
            '>HHHBB',
            self._get_transaction_id(),
            0x0001,  # Invalid protocol ID!
            2,
            1,
            ModbusFunctionCode.READ_HOLDING_REGISTERS
        ) + struct.pack('>HH', 0, 10)
        
        success, response = self._send_request(malformed, timeout=2.0)
        
        if not success or (success and self._is_exception_response(response)):
            self.console.print("[green]  ✓ PASS[/green] - Malformed packet rejected")
            self._record_result(test_name, True, "Malformed packet rejected")
            return True
        else:
            self.console.print("[yellow]  ⚠ WARNING[/yellow] - Malformed packet was processed")
            self._record_result(test_name, False, "Malformed packet accepted")
            return False
    
    def test_flood_attack(self, count: int = 100) -> bool:
        """Test: DoS flood attack with rapid write attempts"""
        test_name = f"Flood Attack ({count} requests)"
        self.console.print(f"\n[cyan]Testing:[/cyan] {test_name}")
        
        blocked = 0
        allowed = 0
        errors = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Sending flood...", total=count)
            
            for i in range(count):
                data = struct.pack('>HH', random.randint(0, 99), random.randint(0, 65535))
                request = self._build_modbus_request(
                    ModbusFunctionCode.WRITE_SINGLE_REGISTER,
                    data
                )
                
                success, response = self._send_request(request, timeout=1.0)
                
                if not success:
                    errors += 1
                elif self._is_exception_response(response):
                    blocked += 1
                else:
                    allowed += 1
                
                progress.update(task, advance=1)
        
        self.console.print(f"  Results: [green]Blocked={blocked}[/green] [red]Allowed={allowed}[/red] Errors={errors}")
        
        if allowed == 0:
            self.console.print("[green]  ✓ PASS[/green] - All flood attack packets blocked")
            self._record_result(test_name, True, f"All {count} packets blocked")
            return True
        else:
            self.console.print(f"[red]  ✗ FAIL[/red] - {allowed} packets got through!")
            self._record_result(test_name, False, f"{allowed}/{count} packets allowed")
            return False
    
    def test_replay_attack(self) -> bool:
        """Test: Replay attack - resend captured write command"""
        test_name = "Replay Attack"
        self.console.print(f"\n[cyan]Testing:[/cyan] {test_name}")
        
        # Simulated "captured" write command
        captured_write = self._build_modbus_request(
            ModbusFunctionCode.WRITE_SINGLE_REGISTER,
            struct.pack('>HH', 0, 9999)
        )
        
        # Replay it multiple times
        blocked = 0
        for _ in range(5):
            success, response = self._send_request(captured_write)
            if not success or self._is_exception_response(response):
                blocked += 1
            time.sleep(0.1)
        
        if blocked == 5:
            self.console.print("[green]  ✓ PASS[/green] - All replay attempts blocked")
            self._record_result(test_name, True, "All replay attempts blocked")
            return True
        else:
            self.console.print(f"[red]  ✗ FAIL[/red] - {5-blocked} replay attempts succeeded!")
            self._record_result(test_name, False, f"{5-blocked}/5 replays succeeded")
            return False
    
    # ==================== Test Suite ====================
    
    def run_all_tests(self):
        """Run complete test suite"""
        self.console.print(Panel(
            "[bold cyan]Modbus Firewall - Attack Simulation Suite[/bold cyan]\n"
            "[dim]Testing firewall security against various attack vectors[/dim]",
            border_style="red"
        ))
        
        self.console.print(f"\n[bold]Target:[/bold] {self.host}:{self.port}")
        self.console.print("=" * 60)
        
        # Normal operation tests
        self.console.print("\n[bold yellow]═══ Normal Operation Tests ═══[/bold yellow]")
        self.test_read_holding_registers()
        self.test_read_input_registers()
        
        # Write attack tests
        self.console.print("\n[bold red]═══ Write Attack Tests ═══[/bold red]")
        self.test_write_single_register()
        self.test_write_multiple_registers()
        self.test_write_single_coil()
        
        # Advanced attack tests
        self.console.print("\n[bold red]═══ Advanced Attack Tests ═══[/bold red]")
        self.test_malformed_protocol_id()
        self.test_replay_attack()
        self.test_flood_attack(50)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        self.console.print("\n" + "=" * 60)
        
        table = Table(title="Attack Simulation Results")
        table.add_column("Test", style="cyan")
        table.add_column("Result", justify="center")
        table.add_column("Details")
        
        for test in self.results['tests']:
            result = "[green]PASS[/green]" if test['passed'] else "[red]FAIL[/red]"
            table.add_row(test['name'], result, test['details'])
        
        self.console.print(table)
        
        total = self.results['passed'] + self.results['failed']
        pass_rate = (self.results['passed'] / total * 100) if total > 0 else 0
        
        if self.results['failed'] == 0:
            status = "[bold green]ALL TESTS PASSED[/bold green]"
        else:
            status = f"[bold red]{self.results['failed']} TESTS FAILED[/bold red]"
        
        self.console.print(f"\nSummary: {self.results['passed']}/{total} passed ({pass_rate:.1f}%)")
        self.console.print(status)


def main():
    parser = argparse.ArgumentParser(description="Modbus Firewall Attack Simulator")
    parser.add_argument("--host", default="127.0.0.1", help="Firewall host")
    parser.add_argument("--port", type=int, default=502, help="Firewall port")
    
    args = parser.parse_args()
    
    simulator = AttackSimulator(host=args.host, port=args.port)
    simulator.run_all_tests()


if __name__ == "__main__":
    main()
