"""
Modbus Firewall - Real-time Dashboard

Web-based dashboard for monitoring firewall activity.
"""

import asyncio
import json
import os
from datetime import datetime
from aiohttp import web
from rich.console import Console

from config import DEFAULT_CONFIG


# HTML template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Modbus Firewall Dashboard</title>
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-tertiary: #1a1a25;
            --text-primary: #e0e0e0;
            --text-secondary: #888;
            --accent-green: #00ff88;
            --accent-red: #ff4444;
            --accent-yellow: #ffaa00;
            --accent-cyan: #00ccff;
            --border-color: #2a2a35;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }
        
        header {
            background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary));
            padding: 20px 30px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        h1 {
            font-size: 1.5rem;
            color: var(--accent-cyan);
        }
        
        .status-badge {
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        
        .status-active {
            background: rgba(0, 255, 136, 0.15);
            color: var(--accent-green);
            border: 1px solid var(--accent-green);
        }
        
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 20px;
        }
        
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }
        
        .card h2 {
            font-size: 1rem;
            color: var(--text-secondary);
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .stat-item {
            text-align: center;
            padding: 15px;
            background: var(--bg-tertiary);
            border-radius: 8px;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
        }
        
        .stat-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 5px;
        }
        
        .green { color: var(--accent-green); }
        .red { color: var(--accent-red); }
        .yellow { color: var(--accent-yellow); }
        .cyan { color: var(--accent-cyan); }
        
        .log-container {
            grid-column: 1 / -1;
        }
        
        .log-entries {
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Consolas', monospace;
            font-size: 0.85rem;
        }
        
        .log-entry {
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .log-entry:hover {
            background: var(--bg-tertiary);
        }
        
        .log-time {
            color: var(--text-secondary);
            white-space: nowrap;
        }
        
        .log-action {
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.75rem;
        }
        
        .log-action.allow {
            background: rgba(0, 255, 136, 0.2);
            color: var(--accent-green);
        }
        
        .log-action.block {
            background: rgba(255, 68, 68, 0.2);
            color: var(--accent-red);
        }
        
        .log-fc {
            color: var(--accent-cyan);
        }
        
        .log-source {
            color: var(--text-secondary);
        }
        
        .policy-list {
            list-style: none;
        }
        
        .policy-list li {
            padding: 8px 0;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
        }
        
        .policy-list .fc-code {
            font-family: monospace;
            color: var(--accent-cyan);
        }
        
        .refresh-btn {
            background: var(--accent-cyan);
            color: var(--bg-primary);
            border: none;
            padding: 8px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
        }
        
        .refresh-btn:hover {
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <header>
        <h1>🛡️ Modbus Firewall Dashboard</h1>
        <div>
            <span class="status-badge status-active">● Active</span>
            <button class="refresh-btn" onclick="refreshData()">Refresh</button>
        </div>
    </header>
    
    <div class="dashboard">
        <div class="card">
            <h2>Statistics</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value cyan" id="stat-total">0</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value green" id="stat-allowed">0</div>
                    <div class="stat-label">Allowed</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value red" id="stat-blocked">0</div>
                    <div class="stat-label">Blocked</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value yellow" id="stat-errors">0</div>
                    <div class="stat-label">Errors</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Security Policy</h2>
            <h3 style="color: var(--accent-green); margin-bottom: 10px;">✓ Allowed (Whitelist)</h3>
            <ul class="policy-list" id="whitelist">
                <li><span class="fc-code">0x01</span> <span>Read Coils</span></li>
                <li><span class="fc-code">0x02</span> <span>Read Discrete Inputs</span></li>
                <li><span class="fc-code">0x03</span> <span>Read Holding Registers</span></li>
                <li><span class="fc-code">0x04</span> <span>Read Input Registers</span></li>
            </ul>
            <h3 style="color: var(--accent-red); margin: 15px 0 10px;">✗ Blocked (Blacklist)</h3>
            <ul class="policy-list" id="blacklist">
                <li><span class="fc-code">0x05</span> <span>Write Single Coil</span></li>
                <li><span class="fc-code">0x06</span> <span>Write Single Register</span></li>
                <li><span class="fc-code">0x0F</span> <span>Write Multiple Coils</span></li>
                <li><span class="fc-code">0x10</span> <span>Write Multiple Registers</span></li>
            </ul>
        </div>
        
        <div class="card log-container">
            <h2>Live Transaction Log</h2>
            <div class="log-entries" id="log-entries">
                <div class="log-entry">
                    <span class="log-time">Waiting for connections...</span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let logEntries = [];
        
        async function refreshData() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('stat-total').textContent = data.total || 0;
                document.getElementById('stat-allowed').textContent = data.allowed || 0;
                document.getElementById('stat-blocked').textContent = data.blocked || 0;
                document.getElementById('stat-errors').textContent = data.errors || 0;
            } catch (e) {
                console.error('Failed to fetch stats:', e);
            }
            
            try {
                const response = await fetch('/api/logs');
                const data = await response.json();
                updateLogs(data.logs || []);
            } catch (e) {
                console.error('Failed to fetch logs:', e);
            }
        }
        
        function updateLogs(logs) {
            const container = document.getElementById('log-entries');
            
            if (logs.length === 0) {
                container.innerHTML = '<div class="log-entry"><span class="log-time">No transactions yet...</span></div>';
                return;
            }
            
            container.innerHTML = logs.map(log => `
                <div class="log-entry">
                    <span class="log-time">${log.timestamp || ''}</span>
                    <span class="log-action ${log.action?.toLowerCase()}">${log.action}</span>
                    <span class="log-fc">FC:${log.function_code?.toString(16).toUpperCase().padStart(2, '0')} (${log.function_name})</span>
                    <span class="log-source">${log.source_ip}:${log.source_port}</span>
                    <span>${log.reason || ''}</span>
                </div>
            `).join('');
        }
        
        // Auto-refresh every 2 seconds
        setInterval(refreshData, 2000);
        refreshData();
    </script>
</body>
</html>
"""


class FirewallDashboard:
    """Web-based dashboard for monitoring"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8080, log_file: str = None):
        self.host = host
        self.port = port
        self.log_file = log_file or DEFAULT_CONFIG.logging.log_file
        self.console = Console()
        self.app = web.Application()
        self._setup_routes()
        
        # Stats (in-memory for demo)
        self.stats = {
            'total': 0,
            'allowed': 0,
            'blocked': 0,
            'errors': 0
        }
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/', self._handle_index)
        self.app.router.add_get('/api/stats', self._handle_stats)
        self.app.router.add_get('/api/logs', self._handle_logs)
    
    async def _handle_index(self, request):
        """Serve main dashboard page"""
        return web.Response(text=DASHBOARD_HTML, content_type='text/html')
    
    async def _handle_stats(self, request):
        """Return current statistics"""
        # Read from log file to get actual stats
        stats = self._read_stats_from_log()
        return web.json_response(stats)
    
    async def _handle_logs(self, request):
        """Return recent log entries"""
        logs = self._read_recent_logs(limit=50)
        return web.json_response({'logs': logs})
    
    def _read_stats_from_log(self) -> dict:
        """Read statistics from log file"""
        stats = {'total': 0, 'allowed': 0, 'blocked': 0, 'errors': 0}
        
        if not os.path.exists(self.log_file):
            return stats
        
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()[1:]  # Skip header
                
                for line in lines:
                    parts = line.strip().split(',')
                    if len(parts) >= 7:
                        action = parts[6]
                        stats['total'] += 1
                        if action == 'ALLOW':
                            stats['allowed'] += 1
                        elif action == 'BLOCK':
                            stats['blocked'] += 1
                        elif action == 'ERROR':
                            stats['errors'] += 1
        except Exception as e:
            self.console.print(f"[red]Error reading log: {e}[/red]")
        
        return stats
    
    def _read_recent_logs(self, limit: int = 50) -> list:
        """Read recent log entries"""
        logs = []
        
        if not os.path.exists(self.log_file):
            return logs
        
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()[1:]  # Skip header
                
                for line in lines[-limit:]:
                    parts = line.strip().split(',')
                    if len(parts) >= 8:
                        logs.append({
                            'timestamp': parts[0].split('T')[1][:8] if 'T' in parts[0] else parts[0],
                            'transaction_id': int(parts[1]) if parts[1].isdigit() else 0,
                            'source_ip': parts[2],
                            'source_port': int(parts[3]) if parts[3].isdigit() else 0,
                            'function_code': int(parts[4]) if parts[4].isdigit() else 0,
                            'function_name': parts[5],
                            'action': parts[6],
                            'reason': parts[7] if len(parts) > 7 else ''
                        })
        except Exception as e:
            self.console.print(f"[red]Error reading logs: {e}[/red]")
        
        return list(reversed(logs))  # Most recent first
    
    def run(self):
        """Run the dashboard server"""
        self.console.print(f"\n[bold cyan]Dashboard starting at http://{self.host}:{self.port}[/bold cyan]")
        web.run_app(self.app, host=self.host, port=self.port, print=None)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Modbus Firewall Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Dashboard host")
    parser.add_argument("--port", type=int, default=8080, help="Dashboard port")
    parser.add_argument("--log", default="modbus_firewall.log", help="Log file path")
    
    args = parser.parse_args()
    
    dashboard = FirewallDashboard(host=args.host, port=args.port, log_file=args.log)
    dashboard.run()


if __name__ == "__main__":
    main()
