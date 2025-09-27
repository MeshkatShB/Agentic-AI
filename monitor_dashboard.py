#!/usr/bin/env python3
"""Simple monitoring dashboard for the AI Agent."""

import time
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import requests

class AgentMonitor:
    def __init__(self):
        self.db_path = "local_agent.db"
        self.api_base = "http://localhost:8000"
        
    def check_database_stats(self):
        """Get database statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user count
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            # Get conversation count
            cursor.execute("SELECT COUNT(*) FROM conversations")
            conversation_count = cursor.fetchone()[0]
            
            # Get message count
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            
            # Get recent activity (last 24 hours)
            yesterday = datetime.now() - timedelta(days=1)
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE created_at > ?", 
                (yesterday.isoformat(),)
            )
            recent_messages = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "users": user_count,
                "conversations": conversation_count,
                "total_messages": message_count,
                "recent_messages_24h": recent_messages
            }
        except Exception as e:
            return {"error": str(e)}
    
    def check_api_health(self):
        """Check API health."""
        try:
            response = requests.get(f"{self.api_base}/docs", timeout=5)
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            return {"status": "down", "error": str(e)}
    
    def check_ollama_health(self):
        """Check Ollama health."""
        try:
            response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return {
                    "status": "healthy",
                    "models": [m.get("name", "unknown") for m in models]
                }
            else:
                return {"status": "unhealthy", "code": response.status_code}
        except Exception as e:
            return {"status": "down", "error": str(e)}
    
    def get_log_summary(self):
        """Get recent log summary."""
        try:
            logs_dir = Path("logs")
            if not logs_dir.exists():
                return {"error": "Logs directory not found"}
            
            error_log = logs_dir / "errors.log"
            app_log = logs_dir / "app.log"
            
            summary = {"errors": 0, "recent_activity": []}
            
            # Count recent errors
            if error_log.exists():
                with open(error_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Count errors in last 100 lines
                    summary["errors"] = len([l for l in lines[-100:] if "ERROR" in l])
            
            # Get recent activity
            if app_log.exists():
                with open(app_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    summary["recent_activity"] = lines[-5:]  # Last 5 log entries
            
            return summary
        except Exception as e:
            return {"error": str(e)}
    
    def display_dashboard(self):
        """Display monitoring dashboard."""
        print("\n" + "="*60)
        print("AI AGENT MONITORING DASHBOARD")
        print("="*60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Database stats
        print("\nDATABASE STATS:")
        db_stats = self.check_database_stats()
        for key, value in db_stats.items():
            print(f"   {key}: {value}")
        
        # API health
        print("\nAPI HEALTH:")
        api_health = self.check_api_health()
        status_emoji = "OK" if api_health.get("status") == "healthy" else "FAIL"
        print(f"   Status: [{status_emoji}] {api_health.get('status', 'unknown')}")
        if "response_time_ms" in api_health:
            print(f"   Response time: {api_health['response_time_ms']:.2f}ms")
        
        # Ollama health
        print("\nOLLAMA HEALTH:")
        ollama_health = self.check_ollama_health()
        status_emoji = "OK" if ollama_health.get("status") == "healthy" else "FAIL"
        print(f"   Status: [{status_emoji}] {ollama_health.get('status', 'unknown')}")
        if "models" in ollama_health:
            print(f"   Models: {', '.join(ollama_health['models'])}")
        
        # Log summary
        print("\nLOG SUMMARY:")
        log_summary = self.get_log_summary()
        if "errors" in log_summary:
            error_status = "WARN" if log_summary["errors"] > 0 else "OK"
            print(f"   Recent errors: [{error_status}] {log_summary['errors']}")
        
        if "recent_activity" in log_summary and log_summary["recent_activity"]:
            print("   Recent activity:")
            for line in log_summary["recent_activity"]:
                print(f"     {line.strip()[:80]}...")
        
        print("\n" + "="*60)

def main():
    """Run monitoring dashboard."""
    monitor = AgentMonitor()
    
    try:
        while True:
            monitor.display_dashboard()
            print("\nRefreshing in 30 seconds... (Ctrl+C to exit)")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()
