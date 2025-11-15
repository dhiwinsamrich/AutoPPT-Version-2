import threading
import time
import uuid
from typing import Dict, List, Optional, Any, Callable


class InMemoryJob:
    def __init__(self, kind: str, params: Dict[str, Any]):
        self.id: str = str(uuid.uuid4())
        self.kind: str = kind
        self.params: Dict[str, Any] = params
        self.status: str = "queued"  # queued | running | succeeded | failed
        self.logs: List[str] = []
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at: float = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None

    def append_log(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.logs.append(f"{timestamp} | {message}")


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, InMemoryJob] = {}
        self._lock = threading.Lock()

    def create(self, kind: str, params: Dict[str, Any]) -> InMemoryJob:
        job = InMemoryJob(kind, params)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[InMemoryJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._serialize(j) for j in self._jobs.values()]

    def _serialize(self, job: InMemoryJob) -> Dict[str, Any]:
        return {
            "id": job.id,
            "kind": job.kind,
            "status": job.status,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }

    def attach_logger_handler(self, job: InMemoryJob):
        import logging

        class JobLogHandler(logging.Handler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                except Exception:
                    msg = record.getMessage()
                job.append_log(msg)

        handler = JobLogHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        return handler


