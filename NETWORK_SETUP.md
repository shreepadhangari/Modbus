# Network Configuration Guide

## Scenario 1: All on Same WiFi Network (Easiest)
If all laptops are on the SAME WiFi network (e.g., all connected to your home WiFi):

### Laptop 1 (PLC Server)
```bash
# Find your local IP address
ipconfig  # Look for IPv4 Address (e.g., 192.168.1.100)

# Edit config.py
host: str = "0.0.0.0"  # Listen on all interfaces
port: int = 5020

# Run server
python modbus_server.py
```

### Laptop 2 (Firewall)
```bash
# Find your local IP address
ipconfig  # (e.g., 192.168.1.101)

# Edit config.py - NetworkConfig
firewall_host: str = "0.0.0.0"
firewall_port: int = 502
plc_host: str = "192.168.1.100"  # IP of Laptop 1
plc_port: int = 5020

# Run firewall
python modbus_firewall.py
```

### Laptop 3 (Client)
```bash
# Run client pointing to Firewall IP
python modbus_client.py --host 192.168.1.101 --port 502
```

---

## Scenario 2: Different WiFi Networks (Over Internet)

### Requirements
- Port forwarding on routers
- Public IP addresses or Dynamic DNS

### Laptop 1 (PLC Server)
1. Configure router port forwarding:
   - External Port: 5020
   - Internal IP: Your laptop's local IP
   - Internal Port: 5020

2. Find public IP: Visit https://whatismyip.com
   - Example: 203.0.113.50

3. Edit config.py:
   ```python
   host: str = "0.0.0.0"
   port: int = 5020
   ```

### Laptop 2 (Firewall)
1. Configure router port forwarding:
   - External Port: 502
   - Internal IP: Your laptop's local IP
   - Internal Port: 502

2. Find public IP: Visit https://whatismyip.com
   - Example: 198.51.100.75

3. Edit config.py:
   ```python
   firewall_host: str = "0.0.0.0"
   firewall_port: int = 502
   plc_host: str = "203.0.113.50"  # Public IP of Laptop 1
   plc_port: int = 5020
   ```

### Laptop 3 (Client)
```bash
python modbus_client.py --host 198.51.100.75 --port 502
```

---

## Scenario 3: Using VPN (RECOMMENDED)

### Setup Tailscale (Free & Easy)
1. Install Tailscale on all 3 laptops: https://tailscale.com/download
2. Sign in with same account on all devices
3. Each device gets a VPN IP (e.g., 100.x.x.x)

### Laptop 1 (PLC)
```bash
# Check Tailscale IP
tailscale ip  # Example: 100.64.0.1

# Edit config.py
host: str = "0.0.0.0"
port: int = 5020
```

### Laptop 2 (Firewall)
```bash
# Check Tailscale IP
tailscale ip  # Example: 100.64.0.2

# Edit config.py
firewall_host: str = "0.0.0.0"
plc_host: str = "100.64.0.1"  # Tailscale IP of Laptop 1
```

### Laptop 3 (Client)
```bash
python modbus_client.py --host 100.64.0.2 --port 502
```

---

## Security Considerations

⚠️ **WARNING**: Exposing Modbus directly to the internet is DANGEROUS!

### Why?
- No encryption (traffic is plaintext)
- No authentication (anyone can connect)
- Vulnerable to attacks

### Recommendations:
1. **Use VPN** (Tailscale, ZeroTier, WireGuard)
2. **Use SSH Tunneling** if VPN not possible
3. **Never expose PLC directly** - always use the firewall
4. **Use strong firewall rules** on routers
5. **Monitor logs** for suspicious activity

---

## Testing Connectivity

### Test 1: Can Client reach Firewall?
```bash
ping <firewall_ip>
telnet <firewall_ip> 502
```

### Test 2: Can Firewall reach PLC?
```bash
ping <plc_ip>
telnet <plc_ip> 5020
```

### Test 3: Run Attack Simulator
```bash
python attack_simulator.py --host <firewall_ip> --port 502
```

---

## Troubleshooting

### "Connection refused"
- Check firewall/antivirus on target laptop
- Verify port forwarding configured correctly
- Ensure server is running and listening on 0.0.0.0

### "Connection timeout"
- Check if public IP is correct
- Verify router port forwarding
- Check if ISP blocks the port

### "Permission denied on port 502"
- Port 502 requires admin privileges on some systems
- Change to port 5002 instead (edit config.py)

### Windows Firewall
```bash
# Allow Python through firewall
netsh advfirewall firewall add rule name="Modbus Server" dir=in action=allow program="C:\Path\To\Python\python.exe" enable=yes
```
