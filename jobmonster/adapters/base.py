from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from jobmonster.models import ApplyMode, ApplyPlan, ApplyResult, CandidateProfile, Documents, JobLead


class ApplyAdapter(ABC):
    name: str
    default_mode: ApplyMode = ApplyMode.ASSISTED

    @abstractmethod
    def can_handle(self, job: JobLead, page_text: str = "") -> bool:
        raise NotImplementedError

    @abstractmethod
    def build_plan(self, job: JobLead, candidate: CandidateProfile, docs: Documents) -> ApplyPlan:
        raise NotImplementedError

    def submit(self, plan: ApplyPlan, approve: bool = False) -> ApplyResult:
        raise NotImplementedError(f"{self.name} does not support direct submission yet")


class AdapterRegistry:
    def __init__(self, adapters: Iterable[ApplyAdapter]):
        self._adapters = list(adapters)

    def resolve(self, job: JobLead, page_text: str = "") -> ApplyAdapter:
        for adapter in self._adapters:
            if adapter.can_handle(job, page_text):
                return adapter
        raise LookupError(f"No adapter found for {job.apply_url}")

    def names(self) -> list[str]:
        return [adapter.name for adapter in self._adapters]

