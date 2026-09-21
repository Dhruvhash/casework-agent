"""Deployment compatibility wrapper around strict JSON transport."""
from .storage import CaseStore


class GraphClient(CaseStore):
    _request = CaseStore.request
    check_echo = CaseStore.ready
