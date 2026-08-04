"""
RBAC Data Models for the HCMatrix Chatbot.

Defines the role/scope enums, the core RBACContext dataclass, and the
Pydantic response models used by the diagnostic endpoint.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Set, Optional
from pydantic import BaseModel
import time


# ─── Role & Scope Enums ─────────────────────────────────────────────────────

class RBACRole(str, Enum):
    """Roles a user can hold within the RBAC system."""
    ADMIN = "ADMIN"
    LINE_MANAGER = "LINE_MANAGER"
    HOD = "HOD"
    EMPLOYEE = "EMPLOYEE"


class ScopeType(str, Enum):
    """
    Determines how the SQL agent filters data.

    self_only         – Regular employee; can only see own records.
    team              – Line Manager; can see direct/indirect reports (via v_reporting_tree).
    department        – HOD; can see all employees in their department subtree (≤ threshold).
    department_large  – HOD with a large org; filtering switches to department IDs instead of
                        individual employee IDs (> threshold, default 200).
    company           – Admin; no employee/department filtering required.
    """
    SELF_ONLY = "self_only"
    TEAM = "team"
    DEPARTMENT = "department"
    DEPARTMENT_LARGE = "department_large"
    COMPANY = "company"


# ─── Core RBAC Context ──────────────────────────────────────────────────────

@dataclass
class RBACContext:
    """
    Fully resolved RBAC context for a single request.

    Built by ``rbac_service.resolve_rbac_context()`` and consumed by
    ``secure_context.build_secure_context()`` to inject runtime security
    information into the AI agent's input.
    """
    company_id: str
    employee_id: str
    roles: Set[RBACRole] = field(default_factory=lambda: {RBACRole.EMPLOYEE})
    scope_type: ScopeType = ScopeType.SELF_ONLY
    accessible_employee_ids: List[str] = field(default_factory=list)
    accessible_department_ids: List[str] = field(default_factory=list)
    can_view_salary: bool = False
    resolved_at: float = field(default_factory=time.time)

    @property
    def is_admin(self) -> bool:
        return RBACRole.ADMIN in self.roles

    @property
    def is_line_manager(self) -> bool:
        return RBACRole.LINE_MANAGER in self.roles

    @property
    def is_hod(self) -> bool:
        return RBACRole.HOD in self.roles

    @property
    def role_names(self) -> List[str]:
        """Sorted list of role names for deterministic display."""
        return sorted(r.value for r in self.roles)


# ─── Pydantic Models for API Endpoints ──────────────────────────────────────

class RBACDiagnosticResponse(BaseModel):
    """Response model for the ``GET /rbac-diagnostic`` endpoint."""
    company_id: str
    employee_id: str
    roles: List[str]
    scope_type: str
    accessible_employee_count: int
    accessible_department_count: int
    sample_employee_ids: List[str]
    can_view_salary: bool
    resolved_at: float


class RBACInvalidateRequest(BaseModel):
    """Request model for the ``POST /rbac-invalidate`` endpoint."""
    company_id: Optional[str] = None
    employee_id: Optional[str] = None
