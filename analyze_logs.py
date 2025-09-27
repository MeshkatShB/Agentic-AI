#!/usr/bin/env python3
"""Analyze AI Agent logs for insights and issues."""

import re
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

class LogAnalyzer:
    def __init__(self, logs_dir="logs"):
        self.logs_dir = Path(logs_dir)
    
    def analyze_errors(self):
        """Analyze error patterns."""
        error_log = self.logs_dir / "errors.log"
        if not error_log.exists():
            return {"message": "No error log found"}
        
        with open(error_log, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract error patterns
        error_patterns = re.findall(r'ERROR - (.+?)\n', content)
        error_counts = Counter(error_patterns)
        
        return {
            "total_errors": len(error_patterns),
            "unique_errors": len(error_counts),
            "top_errors": error_counts.most_common(5)
        }
    
    def analyze_tool_usage(self):
        """Analyze tool usage patterns."""
        app_log = self.logs_dir / "app.log"
        if not app_log.exists():
            return {"message": "No app log found"}
        
        with open(app_log, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract tool usage
        tool_patterns = re.findall(r'ToolSelector selected tool: (\w+)', content)
        tool_counts = Counter(tool_patterns)
        
        # Extract allowed tools info
        allowed_tools_patterns = re.findall(r'allowed_tools: \[(.*?)\]', content)
        
        return {
            "total_tool_calls": len(tool_patterns),
            "unique_tools": len(tool_counts),
            "tool_usage": dict(tool_counts),
            "allowed_tools_logs": len(allowed_tools_patterns)
        }
    
    def analyze_user_activity(self):
        """Analyze user activity patterns."""
        app_log = self.logs_dir / "app.log"
        if not app_log.exists():
            return {"message": "No app log found"}
        
        with open(app_log, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract user activity
        user_patterns = re.findall(r'User (\w+) allowed_tools:', content)
        user_counts = Counter(user_patterns)
        
        return {
            "active_users": list(user_counts.keys()),
            "user_activity": dict(user_counts)
        }
    
    def analyze_performance(self):
        """Analyze performance metrics."""
        app_log = self.logs_dir / "app.log"
        if not app_log.exists():
            return {"message": "No app log found"}
        
        with open(app_log, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract response times (if logged)
        response_times = re.findall(r'response_time: ([0-9.]+)', content)
        response_times = [float(t) for t in response_times]
        
        # Extract execution times
        exec_times = re.findall(r'execution_time: ([0-9.]+)', content)
        exec_times = [float(t) for t in exec_times]
        
        result = {}
        
        if response_times:
            result["response_times"] = {
                "avg_response_time": sum(response_times) / len(response_times),
                "max_response_time": max(response_times),
                "min_response_time": min(response_times),
                "total_requests": len(response_times)
            }
        
        if exec_times:
            result["execution_times"] = {
                "avg_execution_time": sum(exec_times) / len(exec_times),
                "max_execution_time": max(exec_times),
                "min_execution_time": min(exec_times),
                "total_executions": len(exec_times)
            }
        
        if not result:
            result = {"message": "No performance data found"}
        
        return result
    
    def generate_report(self):
        """Generate comprehensive analysis report."""
        print("\n" + "="*50)
        print("AI AGENT LOG ANALYSIS REPORT")
        print("="*50)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Error analysis
        print("\nERROR ANALYSIS:")
        errors = self.analyze_errors()
        for key, value in errors.items():
            print(f"   {key}: {value}")
        
        # Tool usage analysis
        print("\nTOOL USAGE ANALYSIS:")
        tools = self.analyze_tool_usage()
        for key, value in tools.items():
            print(f"   {key}: {value}")
        
        # User activity analysis
        print("\nUSER ACTIVITY ANALYSIS:")
        users = self.analyze_user_activity()
        for key, value in users.items():
            print(f"   {key}: {value}")
        
        # Performance analysis
        print("\nPERFORMANCE ANALYSIS:")
        perf = self.analyze_performance()
        for key, value in perf.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for subkey, subvalue in value.items():
                    print(f"     {subkey}: {subvalue}")
            else:
                print(f"   {key}: {value}")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    analyzer = LogAnalyzer()
    analyzer.generate_report()
