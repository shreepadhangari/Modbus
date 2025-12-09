"""
Modbus Firewall - Simulated PLC Server

A Modbus TCP server that simulates a PLC with various register types.
"""

import time
import threading
import signal
import sys
import random
from pyModbusTCP.server import ModbusServer, DataBank
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live

from config import DEFAULT_CONFIG


class SimulatedPLC:
    """Simulated PLC with dynamic process values"""
    
    def __init__(self, config=None):
        self.config = config or DEFAULT_CONFIG.plc
        self.console = Console()
        self.running = False
        self.server = None
        self.simulation_thread = None
        
        # Initialize data bank
        self.data_bank = DataBank()
        
    def initialize_registers(self):
        """Initialize register map with simulated values"""
        # Coils (0x): Digital outputs (pumps, valves, motors)
        # 0: Pump 1, 1: Pump 2, 2: Valve 1, 3: Valve 2, etc.
        initial_coils = [False] * self.config.num_coils
        initial_coils[0] = True   # Pump 1 ON
        initial_coils[2] = True   # Valve 1 OPEN
        self.data_bank.set_coils(0, initial_coils)
        
        # Discrete Inputs (1x): Digital sensors (limit switches, buttons)
        initial_discrete = [False] * self.config.num_discrete_inputs
        initial_discrete[0] = True   # High level sensor
        initial_discrete[5] = True   # Emergency stop OK
        self.data_bank.set_discrete_inputs(0, initial_discrete)
        
        # Input Registers (3x): Analog sensors (read-only)
        # Temperature, pressure, flow rate, level, etc.
        initial_input_regs = [
            250,   # 0: Temperature (25.0°C * 10)
            1013,  # 1: Pressure (101.3 kPa * 10)
            500,   # 2: Flow rate (50.0 L/min * 10)
            750,   # 3: Tank level (75.0% * 10)
            480,   # 4: Voltage (48.0V * 10)
            100,   # 5: Current (10.0A * 10)
        ] + [0] * (self.config.num_input_registers - 6)
        self.data_bank.set_input_registers(0, initial_input_regs)
        
        # Holding Registers (4x): Setpoints and configuration
        initial_holding_regs = [
            300,   # 0: Temperature setpoint (30.0°C)
            1000,  # 1: Pressure setpoint (100.0 kPa)
            600,   # 2: Flow rate setpoint (60.0 L/min)
            800,   # 3: Level setpoint (80.0%)
            100,   # 4: Motor speed (10.0%)
            0,     # 5: Operating mode (0=Auto, 1=Manual)
        ] + [0] * (self.config.num_holding_registers - 6)
        self.data_bank.set_holding_registers(0, initial_holding_regs)
    
    def simulate_process(self):
        """Background thread to simulate dynamic process values"""
        while self.running:
            try:
                # Read current input registers
                current = self.data_bank.get_input_registers(0, 6)
                if current:
                    # Simulate temperature fluctuation
                    current[0] = max(200, min(350, current[0] + random.randint(-5, 5)))
                    # Simulate pressure fluctuation
                    current[1] = max(900, min(1100, current[1] + random.randint(-10, 10)))
                    # Simulate flow rate
                    current[2] = max(0, min(1000, current[2] + random.randint(-20, 20)))
                    # Simulate tank level
                    current[3] = max(0, min(1000, current[3] + random.randint(-5, 5)))
                    
                    self.data_bank.set_input_registers(0, current)
                
                time.sleep(self.config.update_interval)
            except Exception as e:
                print(f"Simulation error: {e}")
                break
    
    def start(self):
        """Start the PLC server"""
        self.console.print(Panel(
            f"[bold cyan]Simulated PLC Server[/bold cyan]\n"
            f"[dim]Modbus TCP Server for Testing[/dim]",
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
            
            self.console.print(f"[green]✓[/green] Server is running. Press Ctrl+C to stop.")
            self.console.print()
            
            # Display register map
            self.print_register_map()
            
            # Keep running
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            self.console.print(f"[red]✗[/red] Error starting server: {e}")
            return False
        
        return True
    
    def stop(self):
        """Stop the PLC server"""
        self.running = False
        if self.server:
            self.server.stop()
        self.console.print("\n[yellow]Server stopped.[/yellow]")
    
    def print_register_map(self):
        """Print the register map"""
        table = Table(title="Register Map")
        table.add_column("Type", style="cyan")
        table.add_column("Address", justify="right")
        table.add_column("Description")
        table.add_column("Value", justify="right")
        
        # Coils
        coils = self.data_bank.get_coils(0, 5)
        coil_names = ["Pump 1", "Pump 2", "Valve 1", "Valve 2", "Motor 1"]
        if coils:
            for i, (name, val) in enumerate(zip(coil_names, coils)):
                table.add_row("Coil (0x)", str(i), name, "[green]ON[/green]" if val else "[red]OFF[/red]")
        
        table.add_row("", "", "", "")
        
        # Input Registers
        input_regs = self.data_bank.get_input_registers(0, 6)
        input_names = ["Temperature", "Pressure", "Flow Rate", "Tank Level", "Voltage", "Current"]
        input_units = ["°C", "kPa", "L/min", "%", "V", "A"]
        if input_regs:
            for i, (name, val, unit) in enumerate(zip(input_names, input_regs, input_units)):
                table.add_row("Input Reg (3x)", str(i), name, f"{val/10:.1f} {unit}")
        
        table.add_row("", "", "", "")
        
        # Holding Registers
        holding_regs = self.data_bank.get_holding_registers(0, 6)
        holding_names = ["Temp Setpoint", "Pressure SP", "Flow SP", "Level SP", "Motor Speed", "Mode"]
        if holding_regs:
            for i, (name, val) in enumerate(zip(holding_names, holding_regs)):
                if i == 5:
                    table.add_row("Holding Reg (4x)", str(i), name, "Auto" if val == 0 else "Manual")
                else:
                    table.add_row("Holding Reg (4x)", str(i), name, str(val))
        
        self.console.print(table)


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
