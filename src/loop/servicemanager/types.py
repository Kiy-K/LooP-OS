
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any

class ServiceType(Enum):
    GENERATOR = "generator"
    EXTERNAL = "external"
    PLUGIN = "plugin"

class ShutdownState(Enum):
    NOT_STARTED = "not_started"
    WARNING = "warning"
    GRACEFUL = "graceful"
    FORCE = "force"
    CLEANUP = "cleanup"
    COMPLETE = "complete"
    FAILED = "failed"

@dataclass
class ServiceMetadata:
    name: str
    type: ServiceType
    dependencies: List[str] = field(default_factory=list)
    graceful_timeout: float = 10.0
    force_timeout: float = 5.0
    critical: bool = False
    cleanup_handler: Optional[Callable] = None

@dataclass
class ShutdownReport:
    success: List[str] = field(default_factory=list)
    timed_out: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    total_time: float = 0.0
    errors: Dict[str, str] = field(default_factory=dict)
