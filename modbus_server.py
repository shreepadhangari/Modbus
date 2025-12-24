"""
Modbus Firewall - Simulated PLC Server

A Modbus TCP server that simulates a PLC with various register types.
Features live-updating display with activity tracking.
"""

import time
import threading
import signal
import sys
import random
from datetime import datetime
from pyModbusTCP.server import ModbusServer, DataBank
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

from config import DEFAULT_CONFIG


class ActivityTracker:
    """Tracks read/write activity on registers"""
    
    def __init__(self):
        self.last_access = {}  # {(type, addr): timestamp}
        self.access_count = {}  # {(type, addr): count}
    
    def record_access(self, reg_type: str, address: int):
        """Record an access to a register"""
        key = (reg_type, address)
        self.last_access[key] = datetime.now()
        self.access_count[key] = self.access_count.get(key, 0) + 1
    
    def get_status(self, reg_type: str, address: int) -> str:
        """Get activity status for a register"""
        key = (reg_type, address)
        if key not in self.last_access:
            return "[dim]idle[/dim]"
        
        elapsed = (datetime.now() - self.last_access[key]).total_seconds()
        count = self.access_count.get(key, 0)
        
        if elapsed < 2:
            return "[bold green]ACTIVE[/bold green]"
        elif elapsed < 10:
            return f"[yellow]{count}x[/yellow]"
        else:
            return f"[dim]{count}x[/dim]"


class SimulatedPLC:
    """Simulated PLC with dynamic process values and live display"""
    
    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG.plc
        self.console = Console()
        self.running = False
        self.server = None
        self.simulation_thread = None
        
        # Activity tracker - now uses polling to detect changes
        self.activity_tracker = ActivityTracker()
        
        # Use standard DataBank (TrackedDataBank was breaking write handling)
        self.data_bank = DataBank()
        
        # Store previous values for change detection
        self.prev_coils = None
        self.prev_holding = None
        
        # Coil and register names for display
        self.coil_names = {
            0: "Pump 1", 1: "Pump 2", 2: "Valve 1", 3: "Valve 2", 
            4: "Motor 1", 5: "Motor 2", 6: "Heater", 7: "Cooler",
            8: "Alarm", 9: "Light"
        }
        
        self.discrete_names = {
            0: "Hi Level", 1: "Lo Level", 2: "Hi Pressure", 3: "Lo Pressure",
            4: "Door Open", 5: "E-Stop OK", 6: "Run Mode", 7: "Fault"
        }
        
        self.input_reg_names = {
            0: ("Temperature", "°C", 10),
            1: ("Pressure", "kPa", 10),
            2: ("Flow Rate", "L/min", 10),
            3: ("Tank Level", "%", 10),
            4: ("Voltage", "V", 10),
            5: ("Current", "A", 10),
            6: ("Power", "kW", 10),
            7: ("Frequency", "Hz", 10),
        }
        
        self.holding_reg_names = {
            0: ("Temp SP", "°C", 10),
            1: ("Press SP", "kPa", 10),
            2: ("Flow SP", "L/min", 10),
            3: ("Level SP", "%", 10),
            4: ("Motor Spd", "%", 10),
            5: ("Mode", "", 1),
        }
        
    def initialize_registers(self):
        """Initialize register map with simulated values"""
        # Coils (0x): Digital outputs
        initial_coils = [False] * self.config.num_coils
        initial_coils[0] = True   # Pump 1 ON
        initial_coils[2] = True   # Valve 1 OPEN
        self.data_bank.set_coils(0, initial_coils)
        
        # Discrete Inputs (1x): Digital sensors
        initial_discrete = [False] * self.config.num_discrete_inputs
        initial_discrete[0] = True   # High level sensor
        initial_discrete[5] = True   # Emergency stop OK
        self.data_bank.set_discrete_inputs(0, initial_discrete)
        
        # Input Registers (3x): Analog sensors
        initial_input_regs = [
            250, 1013, 500, 750, 480, 100, 50, 600
        ] + [0] * (self.config.num_input_registers - 8)
        self.data_bank.set_input_registers(0, initial_input_regs)
        
        # Holding Registers (4x): Setpoints
        initial_holding_regs = [
            300, 1000, 600, 800, 100, 0
        ] + [0] * (self.config.num_holding_registers - 6)
        self.data_bank.set_holding_registers(0, initial_holding_regs)
        
        # Initialize previous values for change detection
        self.prev_coils = list(self.data_bank.get_coils(0, 100) or [])
        self.prev_holding = list(self.data_bank.get_holding_registers(0, 100) or [])
    
    def detect_changes(self):
        """Detect changes in coils and holding registers for activity tracking"""
        current_coils = self.data_bank.get_coils(0, 100) or []
        current_holding = self.data_bank.get_holding_registers(0, 100) or []
        
        # Check for coil changes
        for i in range(min(len(current_coils), len(self.prev_coils))):
            if current_coils[i] != self.prev_coils[i]:
                self.activity_tracker.record_access("coil", i)
                self.prev_coils[i] = current_coils[i]
        
        # Check for holding register changes
        for i in range(min(len(current_holding), len(self.prev_holding))):
            if current_holding[i] != self.prev_holding[i]:
                self.activity_tracker.record_access("holding", i)
                self.prev_holding[i] = current_holding[i]
    
    def simulate_process(self):
        """Background thread to simulate dynamic process values"""
        while self.running:
            try:
                current = self.data_bank.get_input_registers(0, 8)
                if current:
                    # Simulate fluctuations
                    current[0] = max(200, min(350, current[0] + random.randint(-5, 5)))
                    current[1] = max(900, min(1100, current[1] + random.randint(-10, 10)))
                    current[2] = max(0, min(1000, current[2] + random.randint(-20, 20)))
                    current[3] = max(0, min(1000, current[3] + random.randint(-5, 5)))
                    # Don't use set_ method to avoid marking as "active" from simulation
                    DataBank.set_input_registers(self.data_bank, 0, current)
                
                time.sleep(self.config.update_interval)
            except Exception as e:
                break
    
    def generate_display(self) -> Table:
        """Generate the live display table"""
        # Create main layout
        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_column()
        
        # === COILS TABLE ===
        coils_table = Table(title="[bold cyan]Coils (FC 01/05)[/bold cyan]", 
                           box=None, show_header=True, header_style="bold")
        coils_table.add_column("Addr", justify="right", width=5)
        coils_table.add_column("Name", width=12)
        coils_table.add_column("Value", width=8)
        
        coils = self.data_bank.get_coils(0, 20) or []
        for i in range(min(20, len(coils))):
            name = self.coil_names.get(i, f"Coil {i}")
            val = "[green]ON[/green]" if coils[i] else "[red]OFF[/red]"
            coils_table.add_row(str(i), name, val)
        
        # === DISCRETE INPUTS TABLE ===
        discrete_table = Table(title="[bold cyan]Discrete Inputs (FC 02)[/bold cyan]", 
                              box=None, show_header=True, header_style="bold")
        discrete_table.add_column("Addr", justify="right", width=5)
        discrete_table.add_column("Name", width=12)
        discrete_table.add_column("Value", width=8)
        
        discrete = self.data_bank.get_discrete_inputs(0, 10) or []
        for i in range(min(10, len(discrete))):
            name = self.discrete_names.get(i, f"DI {i}")
            val = "[green]ON[/green]" if discrete[i] else "[dim]OFF[/dim]"
            discrete_table.add_row(str(i), name, val)
        
        # === INPUT REGISTERS TABLE ===
        input_table = Table(title="[bold cyan]Input Registers (FC 04)[/bold cyan]", 
                           box=None, show_header=True, header_style="bold")
        input_table.add_column("Addr", justify="right", width=5)
        input_table.add_column("Name", width=12)
        input_table.add_column("Raw", justify="right", width=6)
        input_table.add_column("Scaled", justify="right", width=12)
        
        input_regs = self.data_bank.get_input_registers(0, 10) or []
        for i in range(min(10, len(input_regs))):
            if i in self.input_reg_names:
                name, unit, scale = self.input_reg_names[i]
                scaled = f"{input_regs[i]/scale:.1f} {unit}"
            else:
                name = f"IR {i}"
                scaled = str(input_regs[i])
            input_table.add_row(str(i), name, str(input_regs[i]), scaled)
        
        # === HOLDING REGISTERS TABLE ===
        holding_table = Table(title="[bold cyan]Holding Registers (FC 03/06/16)[/bold cyan]", 
                             box=None, show_header=True, header_style="bold")
        holding_table.add_column("Addr", justify="right", width=5)
        holding_table.add_column("Name", width=12)
        holding_table.add_column("Raw", justify="right", width=6)
        holding_table.add_column("Scaled", justify="right", width=12)
        
        holding_regs = self.data_bank.get_holding_registers(0, 20) or []
        for i in range(min(20, len(holding_regs))):
            if i in self.holding_reg_names:
                name, unit, scale = self.holding_reg_names[i]
                if i == 5:
                    scaled = "Auto" if holding_regs[i] == 0 else "Manual"
                elif unit:
                    scaled = f"{holding_regs[i]/scale:.1f} {unit}"
                else:
                    scaled = str(holding_regs[i])
            else:
                name = f"HR {i}"
                scaled = str(holding_regs[i])
            holding_table.add_row(str(i), name, str(holding_regs[i]), scaled)
        
        # Combine tables
        left = Table.grid()
        left.add_row(coils_table)
        left.add_row("")
        left.add_row(discrete_table)
        
        right = Table.grid()
        right.add_row(input_table)
        right.add_row("")
        right.add_row(holding_table)
        
        grid.add_row(left, right)
        
        return Panel(
            grid,
            title=f"[bold]PLC Registers[/bold] | {self.config.host}:{self.config.port} | {datetime.now().strftime('%H:%M:%S')}",
            border_style="cyan"
        )
    
    def start(self):
        """Start the PLC server with live display"""
        self.console.print(Panel(
            f"[bold cyan]Simulated PLC Server[/bold cyan]\n"
            f"[dim]Modbus TCP Server with Live Display[/dim]",
            border_style="cyan"
        ))
        
        # Initialize registers
        self.initialize_registers()
        
        # Create and start server
        self.server = ModbusServer(
            host=self.config.host,
            port=self.config.port,
            data_bank=self.data_bank,
            no_block=True
        )
        
        self.console.print(f"[green]✓[/green] Starting server on {self.config.host}:{self.config.port}")
        
        try:
            self.server.start()
            self.running = True
            
            # Start simulation thread
            self.simulation_thread = threading.Thread(target=self.simulate_process, daemon=True)
            self.simulation_thread.start()
            
            self.console.print(f"[green]✓[/green] Server running. Press Ctrl+C to stop.\n")
            
            # Live display loop
            with Live(self.generate_display(), refresh_per_second=2, console=self.console) as live:
                while self.running:
                    self.detect_changes()  # Poll for external writes
                    live.update(self.generate_display())
                    time.sleep(0.5)
                    
        except Exception as e:
            self.console.print(f"[red]✗[/red] Error: {e}")
            return False
        
        return True
    
    def stop(self):
        """Stop the PLC server"""
        self.running = False
        if self.server:
            self.server.stop()
        self.console.print("\n[yellow]Server stopped.[/yellow]")


def main():
    """Main entry point"""
    plc = SimulatedPLC()
    
    def signal_handler(sig, frame):
        plc.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    plc.start()


if __name__ == "__main__":
    main()

