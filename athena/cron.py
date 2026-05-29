"""
Cron - Simple scheduler for Athena
Provides timed task execution without external dependencies.
"""
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class CronJob:
    """Represents a scheduled job."""
    id: str
    name: str
    command: str  # Python expression or shell command
    schedule: str  # Cron-like: "*/5 * * * *" or interval: "every 30m"
    enabled: bool = True
    status: JobStatus = JobStatus.PENDING
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "status": self.status.value,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "last_error": self.last_error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "CronJob":
        """Create from dictionary."""
        data["status"] = JobStatus(data.get("status", "pending"))
        return cls(**data)


class CronParser:
    """Parse cron expressions and intervals."""
    
    @staticmethod
    def parse_interval(schedule: str) -> Optional[int]:
        """Parse interval like '30m', '2h', '1d'. Returns seconds."""
        schedule = schedule.strip().lower()
        
        if schedule.startswith("every "):
            schedule = schedule[6:]
        
        multipliers = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
        }
        
        for suffix, mult in multipliers.items():
            if schedule.endswith(suffix):
                try:
                    value = int(schedule[:-1])
                    return value * mult
                except ValueError:
                    return None
        
        # Try plain number (assume seconds)
        try:
            return int(schedule)
        except ValueError:
            return None
    
    @staticmethod
    def parse_cron(schedule: str) -> Optional[Dict]:
        """Parse cron expression (minute hour day month weekday)."""
        parts = schedule.strip().split()
        if len(parts) != 5:
            return None
        
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "weekday": parts[4],
        }
    
    @staticmethod
    def should_run(cron_expr: Dict, last_run: Optional[datetime] = None) -> bool:
        """Check if a cron job should run now."""
        now = datetime.now()
        
        # Simple check: just compare minute/hour for basic scheduling
        minute_match = CronParser._match_field(cron_expr["minute"], now.minute)
        hour_match = CronParser._match_field(cron_expr["hour"], now.hour)
        
        if not (minute_match and hour_match):
            return False
        
        # Don't run if already ran this minute
        if last_run:
            last = datetime.fromisoformat(last_run) if isinstance(last_run, str) else last_run
            if (now - last).total_seconds() < 60:
                return False
        
        return True
    
    @staticmethod
    def _match_field(pattern: str, value: int) -> bool:
        """Match a cron field pattern."""
        if pattern == "*":
            return True
        
        if pattern.startswith("*/"):
            try:
                divisor = int(pattern[2:])
                return value % divisor == 0
            except ValueError:
                return False
        
        try:
            return int(pattern) == value
        except ValueError:
            return False


class CronScheduler:
    """
    Simple cron scheduler for Athena.
    
    Features:
    - Interval-based scheduling (every 30m, 2h)
    - Cron expression support
    - Persistent job storage
    - Thread-safe execution
    
    Example:
        >>> scheduler = CronScheduler()
        >>> scheduler.add_job("check_updates", "python check.py", schedule="every 2h")
        >>> scheduler.start()
    """
    
    def __init__(self, storage_path: str = "~/.athena/cron.json"):
        """
        Initialize scheduler.
        
        Args:
            storage_path: Path to job storage file
        """
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.jobs: Dict[str, CronJob] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, Callable] = {}
        
        # Load existing jobs
        self._load_jobs()
    
    def _load_jobs(self):
        """Load jobs from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                    for job_data in data.get("jobs", []):
                        job = CronJob.from_dict(job_data)
                        self.jobs[job.id] = job
                logger.info(f"Loaded {len(self.jobs)} jobs from storage")
            except Exception as e:
                logger.error(f"Failed to load jobs: {e}")
    
    def _save_jobs(self):
        """Save jobs to storage."""
        try:
            data = {
                "jobs": [job.to_dict() for job in self.jobs.values()]
            }
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save jobs: {e}")
    
    def add_job(
        self,
        name: str,
        command: str,
        schedule: str = "every 30m",
        enabled: bool = True,
    ) -> CronJob:
        """
        Add a new scheduled job.
        
        Args:
            name: Job name
            command: Command to execute
            schedule: Schedule (e.g., "every 30m", "0 * * * *")
            enabled: Whether job is enabled
            
        Returns:
            Created CronJob
        """
        job_id = f"job_{int(time.time() * 1000)}"
        
        job = CronJob(
            id=job_id,
            name=name,
            command=command,
            schedule=schedule,
            enabled=enabled,
        )
        
        # Calculate next run
        job.next_run = self._calculate_next_run(job)
        
        self.jobs[job_id] = job
        self._save_jobs()
        
        logger.info(f"Added job: {name} ({job_id})")
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a job."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save_jobs()
            logger.info(f"Removed job: {job_id}")
            return True
        return False
    
    def get_job(self, job_id: str) -> Optional[CronJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)
    
    def list_jobs(self) -> List[CronJob]:
        """List all jobs."""
        return list(self.jobs.values())
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a job."""
        job = self.jobs.get(job_id)
        if job:
            job.enabled = False
            job.status = JobStatus.PAUSED
            self._save_jobs()
            return True
        return False
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = self.jobs.get(job_id)
        if job:
            job.enabled = True
            job.status = JobStatus.PENDING
            job.next_run = self._calculate_next_run(job)
            self._save_jobs()
            return True
        return False
    
    def _calculate_next_run(self, job: CronJob) -> str:
        """Calculate next run time."""
        now = datetime.now()
        
        # Try interval
        interval = CronParser.parse_interval(job.schedule)
        if interval:
            next_run = now + timedelta(seconds=interval)
            return next_run.isoformat()
        
        # Try cron expression
        cron_expr = CronParser.parse_cron(job.schedule)
        if cron_expr:
            # Simple: next hour matching
            next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            return next_run.isoformat()
        
        # Default: 1 hour from now
        return (now + timedelta(hours=1)).isoformat()
    
    def start(self, check_interval: int = 60):
        """
        Start the scheduler.
        
        Args:
            check_interval: Seconds between checks
        """
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.thread = threading.Thread(
            target=self._run_loop,
            args=(check_interval,),
            daemon=True
        )
        self.thread.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _run_loop(self, check_interval: int):
        """Main scheduler loop."""
        while self.running:
            try:
                self._check_and_run_jobs()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            
            time.sleep(check_interval)
    
    def _check_and_run_jobs(self):
        """Check and run due jobs."""
        now = datetime.now()
        
        for job in self.jobs.values():
            if not job.enabled:
                continue
            
            if job.next_run:
                try:
                    next_run = datetime.fromisoformat(job.next_run)
                    if now >= next_run:
                        self._execute_job(job)
                except ValueError:
                    pass
    
    def _execute_job(self, job: CronJob):
        """Execute a job."""
        logger.info(f"Executing job: {job.name}")
        
        job.status = JobStatus.RUNNING
        job.last_run = datetime.now().isoformat()
        
        try:
            # Execute command
            import subprocess
            result = subprocess.run(
                job.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                job.status = JobStatus.COMPLETED
                job.run_count += 1
                logger.info(f"Job completed: {job.name}")
            else:
                job.status = JobStatus.FAILED
                job.last_error = result.stderr[:500]
                logger.error(f"Job failed: {job.name} - {result.stderr[:100]}")
        
        except subprocess.TimeoutExpired:
            job.status = JobStatus.FAILED
            job.last_error = "Execution timed out"
        
        except Exception as e:
            job.status = JobStatus.FAILED
            job.last_error = str(e)
            logger.error(f"Job error: {job.name} - {e}")
        
        # Calculate next run
        job.next_run = self._calculate_next_run(job)
        self._save_jobs()
    
    def run_job_now(self, job_id: str) -> bool:
        """Immediately run a job."""
        job = self.jobs.get(job_id)
        if job:
            self._execute_job(job)
            return True
        return False
