"""
RBAC Service — Role detection, scope resolution, and caching.

Resolves an employee's roles and data-access scope by querying MySQL views/procedures:
  - v_user_roles                → role detection
  - sp_accessible_employees     → employee-level scope (stored procedure)
  - v_department_tree       → department hierarchy (HOD)
  - v_reporting_tree        → reporting line (Line Manager)

The resolved RBACContext is cached in a dedicated LRU cache (default TTL 60s).
On any failure the service falls back to EMPLOYEE + self_only (fail-safe).
"""

import logging
import time
import asyncio
from typing import Set, List, Tuple

from sqlalchemy import text, Engine

from module.rbac_models import RBACRole, ScopeType, RBACContext
from module.cache_service import LRUCache
from module.utils import config

logger = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────────────────

_rbac_cfg = config["production"].get("rbac_config", {})
_AUTH_SCHEMA = _rbac_cfg.get("auth_schema", "hcmatrix-utility-db")
_CACHE_TTL = int(_rbac_cfg.get("rbac_cache_ttl", 60))
_CACHE_CAPACITY = int(_rbac_cfg.get("rbac_cache_capacity", 500))
_LARGE_DEPT_THRESHOLD = int(_rbac_cfg.get("large_department_threshold", 200))

# Dedicated RBAC cache — separate from the agent executor cache.
_rbac_cache = LRUCache(capacity=_CACHE_CAPACITY, ttl=_CACHE_TTL)


# ─── Public API ─────────────────────────────────────────────────────────────

async def resolve_rbac_context(
    company_id: str,
    employee_id: str,
    engine: Engine,
) -> RBACContext:
    """
    Resolve the full RBAC context for a company/employee pair.

    Returns a cached result if available, otherwise queries the database
    and caches the new context.  Falls back to EMPLOYEE / self_only on
    any unexpected error.

    Args:
        company_id: The company identifier.
        employee_id: The employee identifier.
        engine: SQLAlchemy engine connected to the chatbot DB.

    Returns:
        RBACContext with roles, scope, accessible IDs, and salary visibility.
    """
    cache_key = f"rbac::{company_id}::{employee_id}"

    cached = _rbac_cache.get(cache_key)
    if not (isinstance(cached, int) and cached == -1):
        logger.debug("RBAC cache HIT for %s::%s", company_id, employee_id)
        return cached

    logger.info("RBAC cache MISS — resolving for %s::%s", company_id, employee_id)

    try:
        ctx = await asyncio.to_thread(
            _resolve_sync, company_id, employee_id, engine
        )
    except Exception as exc:
        logger.error(
            "RBAC resolution FAILED for %s::%s — falling back to EMPLOYEE/self_only: %s",
            company_id, employee_id, exc,
        )
        ctx = RBACContext(
            company_id=company_id,
            employee_id=employee_id,
            roles={RBACRole.EMPLOYEE},
            scope_type=ScopeType.SELF_ONLY,
            accessible_employee_ids=[employee_id],
            can_view_salary=False,
        )

    _rbac_cache.put(cache_key, ctx)
    return ctx


def invalidate_rbac_cache(company_id: str, employee_id: str) -> bool:
    """Remove a specific RBAC context from the cache."""
    cache_key = f"rbac::{company_id}::{employee_id}"
    removed = _rbac_cache.delete(cache_key)
    if removed:
        logger.info("RBAC cache invalidated for %s::%s", company_id, employee_id)
    return removed


def invalidate_all_rbac_cache() -> None:
    """Clear the entire RBAC cache."""
    _rbac_cache.clear()
    logger.info("RBAC cache fully cleared")


# ─── Synchronous resolution (runs inside asyncio.to_thread) ────────────────

def _resolve_sync(
    company_id: str,
    employee_id: str,
    engine: Engine,
) -> RBACContext:
    """Full synchronous RBAC resolution pipeline."""
    with engine.connect() as conn:
        roles = _detect_roles(company_id, employee_id, conn)
        scope_type, emp_ids, dept_ids = _resolve_scope(
            company_id, employee_id, roles, conn
        )
        can_view_salary = _determine_salary_visibility(roles)
        dept_names = _fetch_department_names(company_id, dept_ids, conn) if dept_ids else []

    return RBACContext(
        company_id=company_id,
        employee_id=employee_id,
        roles=roles,
        scope_type=scope_type,
        accessible_employee_ids=emp_ids,
        accessible_department_ids=dept_ids,
        accessible_department_names=dept_names,
        can_view_salary=can_view_salary,
    )


# ─── Step 1: Role Detection ────────────────────────────────────────────────

def _detect_roles(
    company_id: str,
    employee_id: str,
    conn,
) -> Set[RBACRole]:
    """
    Query v_user_roles to determine all roles for this employee.

    The view returns:
      - roleName / roleLabel: text role identifier (e.g. 'Admin', 'Employee')
      - isAdmin, isLineManager, isHodFlag, isDeptHead, hasDirectReports: boolean flags
      - effectiveAccessTier: computed tier ('admin', 'hod', 'line_manager', 'employee')

    We use BOTH the roleName text AND the boolean flags for maximum reliability.
    """
    roles: Set[RBACRole] = {RBACRole.EMPLOYEE}  # always present

    schema = _AUTH_SCHEMA
    query = text(
        f"SELECT roleName, isAdmin, isLineManager, isHodFlag, isDeptHead, hasDirectReports "
        f"FROM `{schema}`.`v_user_roles` "
        f"WHERE companyId = :cid AND employeeId = :eid"
    )
    rows = conn.execute(query, {"cid": company_id, "eid": employee_id}).fetchall()

    _ROLE_MAP = {
        "admin": RBACRole.ADMIN,
        "linemanager": RBACRole.LINE_MANAGER,
        "line_manager": RBACRole.LINE_MANAGER,
        "hod": RBACRole.HOD,
        "employee": RBACRole.EMPLOYEE,
    }

    for row in rows:
        role_name = str(row[0]).strip().lower()
        is_admin = bool(row[1])
        is_line_manager = bool(row[2])
        is_hod_flag = bool(row[3])
        is_dept_head = bool(row[4])
        has_direct_reports = bool(row[5])
 
        # Map from roleName text
        mapped = _ROLE_MAP.get(role_name)
        if mapped:
            roles.add(mapped)
        else:
            logger.warning("Unknown role '%s' for %s::%s — skipping", row[0], company_id, employee_id)

        # Also check boolean flags for extra reliability
        if is_admin:
            roles.add(RBACRole.ADMIN)
        if is_line_manager or has_direct_reports:
            roles.add(RBACRole.LINE_MANAGER)
        if is_hod_flag or is_dept_head:
            roles.add(RBACRole.HOD)

    logger.info("Detected roles for %s::%s -> %s", company_id, employee_id,
                sorted(r.value for r in roles))
    return roles


# ─── Step 2: Scope Resolution ──────────────────────────────────────────────

def _resolve_scope(
    company_id: str,
    employee_id: str,
    roles: Set[RBACRole],
    conn,
) -> Tuple[ScopeType, List[str], List[str]]:
    """
    Determine the broadest scope for this user based on their roles.

    Priority: Admin > HOD > Line Manager > Employee.

    Returns:
        (scope_type, accessible_employee_ids, accessible_department_ids)
    """
    schema = _AUTH_SCHEMA

    # ── Admin → company-wide access ──────────────────────────────────────
    if RBACRole.ADMIN in roles:
        logger.info("Scope: COMPANY (Admin) for %s::%s", company_id, employee_id)
        return ScopeType.COMPANY, [], []

    # ── HOD → department subtree ─────────────────────────────────────────
    if RBACRole.HOD in roles:
        # 1. Get all descendant department IDs from the department tree
        dept_query = text(
            f"SELECT DISTINCT departmentId "
            f"FROM `{schema}`.`v_department_tree` "
            f"WHERE rootDepartmentId IN ("
            f"  SELECT departmentId FROM `{schema}`.`v_public_departments` "
            f"  WHERE companyId = :cid AND departmentHeadId = :eid"
            f") AND companyId = :cid"
        )
        dept_rows = conn.execute(dept_query, {"cid": company_id, "eid": employee_id}).fetchall()
        dept_ids = [str(r[0]) for r in dept_rows]

        # 2. Get accessible employee IDs from the stored procedure
        # Use raw DBAPI connection to properly exhaust result sets (prevents "Commands out of sync" error)
        raw_conn = conn.connection
        cursor = raw_conn.cursor()
        
        # Save original DB, switch to auth schema, use callproc (which properly populates stored_results)
        cursor.execute("SELECT DATABASE()")
        original_db = cursor.fetchone()[0]
        
        cursor.execute(f"USE `{schema}`")
        cursor.callproc("sp_accessible_employees", (employee_id, company_id))
        
        emp_ids = []
        for result in cursor.stored_results():
            emp_ids.extend([str(r[1]) for r in result.fetchall()]) # r[1] is employeeId
            
        if original_db:
            cursor.execute(f"USE `{original_db}`")
            
        cursor.close()


        # Ensure self is always included
        if employee_id not in emp_ids:
            emp_ids.append(employee_id)

        # Decide between department vs department_large
        if len(emp_ids) > _LARGE_DEPT_THRESHOLD:
            scope = ScopeType.DEPARTMENT_LARGE
            logger.info(
                "Scope: DEPARTMENT_LARGE for %s::%s (%d employees, %d departments)",
                company_id, employee_id, len(emp_ids), len(dept_ids),
            )
            return scope, emp_ids, dept_ids
        else:
            scope = ScopeType.DEPARTMENT
            logger.info(
                "Scope: DEPARTMENT for %s::%s (%d employees, %d departments)",
                company_id, employee_id, len(emp_ids), len(dept_ids),
            )
            return scope, emp_ids, dept_ids

    # ── Line Manager → reporting tree ────────────────────────────────────
    if RBACRole.LINE_MANAGER in roles:
        # v_reporting_tree columns: rootManagerId, rootManagerName,
        # employeeId, employeeName, depthLevel, reportingPath, companyId
        report_query = text(
            f"SELECT DISTINCT employeeId "
            f"FROM `{schema}`.`v_reporting_tree` "
            f"WHERE rootManagerId = :eid AND companyId = :cid"
        )
        report_rows = conn.execute(report_query, {"cid": company_id, "eid": employee_id}).fetchall()
        emp_ids = [str(r[0]) for r in report_rows]

        # Ensure self is always included
        if employee_id not in emp_ids:
            emp_ids.append(employee_id)

        logger.info(
            "Scope: TEAM for %s::%s (%d team members)",
            company_id, employee_id, len(emp_ids),
        )
        return ScopeType.TEAM, emp_ids, []

    # ── Employee → self only ─────────────────────────────────────────────
    logger.info("Scope: SELF_ONLY for %s::%s", company_id, employee_id)
    return ScopeType.SELF_ONLY, [employee_id], []


# ─── Step 3: Salary Visibility ──────────────────────────────────────────────

def _determine_salary_visibility(roles: Set[RBACRole]) -> bool:
    """
    Only Admins can view salary data for other employees.
    All other roles can only see their own salary (enforced in the prompt).
    """
    return RBACRole.ADMIN in roles


# ─── Step 4: Fetch Department Names ─────────────────────────────────────────

def _fetch_department_names(
    company_id: str,
    dept_ids: List[str],
    conn,
) -> List[str]:
    """
    Look up human-readable department names for the given department IDs.

    Used to populate the secure context so the LLM knows which department(s)
    the HOD belongs to (e.g. "Data Engineering & Analytics").
    """
    if not dept_ids:
        return []

    schema = _AUTH_SCHEMA
    placeholders = ", ".join([f":d{i}" for i in range(len(dept_ids))])
    query = text(
        f"SELECT DISTINCT departmentName "
        f"FROM `{schema}`.`v_public_departments` "
        f"WHERE companyId = :cid AND departmentId IN ({placeholders})"
    )
    params = {"cid": company_id}
    for i, did in enumerate(dept_ids):
        params[f"d{i}"] = did

    rows = conn.execute(query, params).fetchall()
    names = [str(r[0]) for r in rows if r[0]]
    logger.info("Resolved %d department name(s) for company %s: %s", len(names), company_id, names)
    return names
