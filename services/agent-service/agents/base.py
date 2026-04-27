"""
Base Agent Class for NeXo Multi-Agent System
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentResult:
    agent_name: str
    success: bool
    data: dict = field(default_factory=dict)
    summary: str = ""
    error: Optional[str] = None


@dataclass
class AgentIntent:
    action: str  # e.g. "analyze_subscriber", "monitor_cells"
    params: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)


class BaseAgent(ABC):
    name: str = "base"
    capabilities: list[str] = []

    @abstractmethod
    async def handle(self, intent: AgentIntent) -> AgentResult:
        """Handle an intent and return a structured result."""
        pass

    def check_capability(self, action: str) -> bool:
        return action in self.capabilities
