"""
Monitor - System monitoring tools for Athena
"""
import logging
import platform
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SystemInfo:
    """System information."""
    os: str
    os_version: str
    hostname: str
    python_version: str
    cpu_count: int
    total_memory_gb: float
    
    def to_dict(self) -> Dict:
        return {
            "os": self.os,
            "os_version": self.os_version,
            "hostname": self.hostname,
            "python_version": self.python_version,
            "cpu_count": self.cpu_count,
            "total_memory_gb": self.total_memory_gb,
        }


class SystemMonitor:
    """
    System monitoring tools.
    
    Example:
        >>> monitor = SystemMonitor()
        >>> info = monitor.get_system_info()
        >>> print(info.os, info.total_memory_gb)
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def get_system_info(self) -> SystemInfo:
        """Get basic system information."""
        import psutil
        
        return SystemInfo(
            os=platform.system(),
            os_version=platform.version(),
            hostname=platform.node(),
            python_version=platform.python_version(),
            cpu_count=psutil.cpu_count(),
            total_memory_gb=round(psutil.virtual_memory().total / (1024**3), 2),
        )
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage."""
        import psutil
        
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        }
    
    def get_cpu_usage(self, interval: float = 1.0) -> float:
        """Get CPU usage percentage."""
        import psutil
        return psutil.cpu_percent(interval=interval)
    
    def get_disk_usage(self, path: str = "/") -> Dict[str, float]:
        """Get disk usage."""
        import psutil
        
        try:
            disk = psutil.disk_usage(path)
            return {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent,
            }
        except Exception as e:
            logger.error(f"Failed to get disk usage: {e}")
            return {}
    
    def get_top_processes(self, n: int = 5) -> list:
        """Get top processes by memory usage."""
        import psutil
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'memory_info']):
            try:
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "memory_percent": round(proc.info['memory_percent'], 1),
                    "memory_mb": round(proc.info['memory_info'].rss / (1024**2), 1),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by memory usage
        processes.sort(key=lambda x: x['memory_mb'], reverse=True)
        return processes[:n]
    
    def get_gpu_info(self) -> Optional[Dict]:
        """Get GPU information (NVIDIA only)."""
        import subprocess
        
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                if len(parts) >= 5:
                    return {
                        "name": parts[0],
                        "memory_total_mb": int(parts[1]),
                        "memory_used_mb": int(parts[2]),
                        "temperature_c": int(parts[3]),
                        "utilization_percent": int(parts[4]),
                    }
        except Exception as e:
            logger.debug(f"GPU info not available: {e}")
        
        return None
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get network status."""
        import httpx
        
        status = {
            "internet": False,
            "ollama": False,
        }
        
        # Check internet
        try:
            response = httpx.get("https://httpbin.org/ip", timeout=5)
            status["internet"] = response.status_code == 200
        except Exception:
            pass
        
        # Check Ollama
        try:
            response = httpx.get("http://localhost:11434/api/tags", timeout=3)
            status["ollama"] = response.status_code == 200
        except Exception:
            pass
        
        return status
    
    def health_check(self) -> Dict[str, Any]:
        """Run a comprehensive health check."""
        info = {
            "system": self.get_system_info().to_dict(),
            "memory": self.get_memory_usage(),
            "cpu_percent": self.get_cpu_usage(interval=0.1),
            "disk": self.get_disk_usage(),
            "gpu": self.get_gpu_info(),
            "network": self.get_network_status(),
        }
        
        # Health score
        score = 100
        if info["memory"]["percent"] > 90:
            score -= 30
        elif info["memory"]["percent"] > 80:
            score -= 15
        
        if info["disk"]["percent"] > 90:
            score -= 20
        
        if info["gpu"] and info["gpu"]["temperature_c"] > 80:
            score -= 20
        
        info["health_score"] = score
        info["health_status"] = (
            "healthy" if score >= 80 else
            "warning" if score >= 60 else
            "critical"
        )
        
        return info


def register_monitor_tools(registry):
    """Register monitoring tools with a ToolRegistry."""
    monitor = SystemMonitor()
    
    @registry.register("system_info")
    def system_info() -> str:
        """Get system information (OS, CPU, memory)."""
        info = monitor.get_system_info()
        return (
            f"OS: {info.os} {info.os_version}\n"
            f"Hostname: {info.hostname}\n"
            f"Python: {info.python_version}\n"
            f"CPU: {info.cpu_count} cores\n"
            f"Memory: {info.total_memory_gb} GB"
        )
    
    @registry.register("memory_usage")
    def memory_usage() -> str:
        """Get memory usage statistics."""
        mem = monitor.get_memory_usage()
        return (
            f"Memory: {mem['used_gb']}/{mem['total_gb']} GB ({mem['percent']}%)\n"
            f"Available: {mem['available_gb']} GB"
        )
    
    @registry.register("disk_usage")
    def disk_usage() -> str:
        """Get disk usage statistics."""
        disk = monitor.get_disk_usage()
        return (
            f"Disk: {disk['used_gb']}/{disk['total_gb']} GB ({disk['percent']}%)\n"
            f"Free: {disk['free_gb']} GB"
        )
    
    @registry.register("gpu_info")
    def gpu_info() -> str:
        """Get GPU information (NVIDIA)."""
        gpu = monitor.get_gpu_info()
        if not gpu:
            return "No NVIDIA GPU detected or nvidia-smi not available"
        return (
            f"GPU: {gpu['name']}\n"
            f"Memory: {gpu['memory_used_mb']}/{gpu['memory_total_mb']} MB\n"
            f"Temperature: {gpu['temperature_c']}°C\n"
            f"Utilization: {gpu['utilization_percent']}%"
        )
    
    @registry.register("health_check")
    def health_check() -> str:
        """Run a comprehensive system health check."""
        health = monitor.health_check()
        return (
            f"Health Score: {health['health_score']}/100 ({health['health_status']})\n"
            f"CPU: {health['cpu_percent']}%\n"
            f"Memory: {health['memory']['percent']}%\n"
            f"Disk: {health['disk']['percent']}%\n"
            f"Internet: {'✓' if health['network']['internet'] else '✗'}\n"
            f"Ollama: {'✓' if health['network']['ollama'] else '✗'}"
        )
