# Modbus Firewall

A cybersecurity solution for Operational Technology (OT) environments implementing Deep Packet Inspection & Filtering for the legacy Modbus TCP protocol.

## Overview

This project implements a "Modbus Firewall" that acts as a transparent proxy between a Modbus client (HMI) and server (PLC). It enforces security policies to protect against unauthorized write operations while allowing legitimate read operations.

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│  HMI Client │────▶│  Modbus Firewall │────▶│  PLC Server │
│  (Port 502) │◀────│  (DPI + Policy)  │◀────│  (Port 5020)│
└─────────────┘     └─────────────────┘     └─────────────┘
```

## Components

| File | Description |
|------|-------------|
| `modbus_server.py` | Simulated PLC with registers |
| `modbus_firewall.py` | Main firewall with DPI |
| `modbus_client.py` | Interactive HMI client |
| `attack_simulator.py` | Security testing suite |
| `dashboard.py` | Web-based monitoring |
| `dpi_engine.py` | Packet inspection engine |
| `security_policy.py` | Policy enforcement |
| `logging_system.py` | File-based logging |
| `config.py` | Configuration settings |

## Quick Start

### 1. Start the PLC Server (Terminal 1)
```bash
cd d:\Modbus
.venv\Scripts\activate
python modbus_server.py
```

### 2. Start the Firewall (Terminal 2)
```bash
cd d:\Modbus
.venv\Scripts\activate
python modbus_firewall.py
```

### 3. Run the HMI Client (Terminal 3)
```bash
cd d:\Modbus
.venv\Scripts\activate
python modbus_client.py
```

### 4. Run Attack Simulation (Terminal 4)
```bash
cd d:\Modbus
.venv\Scripts\activate
python attack_simulator.py
```

### 5. View Dashboard (Optional)
```bash
python dashboard.py
# Open http://127.0.0.1:8080 in browser
```

## Security Policy

### Allowed (Whitelist)
| FC | Name | Description |
|----|------|-------------|
| 0x01 | Read Coils | Digital outputs |
| 0x02 | Read Discrete Inputs | Digital sensors |
| 0x03 | Read Holding Registers | Setpoints |
| 0x04 | Read Input Registers | Analog sensors |

### Blocked (Blacklist)
| FC | Name | Risk |
|----|------|------|
| 0x05 | Write Single Coil | Actuator control |
| 0x06 | Write Single Register | Setpoint change |
| 0x0F | Write Multiple Coils | Bulk control |
| 0x10 | Write Multiple Registers | Bulk setpoint |
| 0x17 | Read/Write Multiple | Combined access |

## Features

- **Deep Packet Inspection**: Parses Modbus TCP ADU structure
- **Policy Enforcement**: Whitelist/blacklist function codes
- **Rate Limiting**: Prevents DoS attacks
- **Maintenance Windows**: Time-based write permissions
- **IP Whitelisting**: Authorized engineering stations
- **Forensic Logging**: CSV format for analysis
- **Real-time Dashboard**: Web-based monitoring
- **Attack Simulation**: Security testing suite

## Logs

- `modbus_firewall.log` - Transaction log (CSV)
- `security_alerts.log` - Blocked operation alerts

## Testing

The attack simulator tests:
- Normal read operations (should pass)
- Write attacks (should be blocked)
- Malformed packets (should be rejected)
- Flood attacks (DoS protection)
- Replay attacks (should be blocked)

## Configuration

Edit `config.py` to customize:
- Network ports
- Security policies
- Logging preferences
- Rate limits
