"""
SQL Validator — Deterministic RBAC enforcement layer for SQL queries.

This module provides a validated query tool that wraps LangChain's
QuerySQLDatabaseTool. Before any SQL query is executed against the database,
the validator checks it against the current user's RBAC context to prevent
data leaks.

Defense Layer 2: Even if the LLM ignores prompt instructions, this layer
will block unauthorized queries deterministically.
"""

import re
import logging
from typing import Set, List, Optional

from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from module.rbac_models import RBACContext, ScopeType

logger = logging.getLogger(__name__)

# ─── Constants ──────────────────────────────────────────────────────────────

# Views that contain salary/payroll data
SALARY_PROTECTED_VIEWS = {
    "v_employee_payslips",
    "v_employee_payslip_components",
    "v_employee_pay_structure",
    "v_employee_loan_repayments",
}

# Views that are truly public (no employeeId column) — but still need
# department-level scoping for non-admin users
PUBLIC_VIEWS = {
    "v_public_employee_directory",
    "v_public_departments",
    "holidays",
    "v_employee_hmo_hospitals",
}

# Aggregated views that need department filtering for HOD scope
DEPARTMENT_SCOPED_VIEWS = {
    "v_department_summary",
}

# All views that contain employee-scoped data (require employeeId filtering)
EMPLOYEE_SCOPED_VIEWS = {
    "v_employee_profile", "v_employee_emergency_contacts", "v_employee_education",
    "v_employee_employment_history", "v_employee_leave_summary", "v_employee_leaves",
    "v_employee_payslips", "v_employee_payslip_components", "v_employee_pay_structure",
    "v_employee_hmo_profile", "v_employee_hmo_dependents",
    "v_employee_loan_eligibility", "v_employee_loans",
    "v_employee_loan_requests", "v_employee_loan_repayments",
    "v_employee_assets", "v_employee_vehicles",
    "v_employee_daily_attendance", "v_employee_latest_clock",
    "v_team_headcount", "v_team_leave_summary", "v_team_attendance_summary",
    "v_team_asset_summary",
}

# Salary aggregate functions that should be blocked when salary is restricted
SALARY_AGGREGATE_PATTERN = re.compile(
    r"\b(SUM|AVG|MIN|MAX|COUNT)\s*\(\s*[`\"]?"
    r"(grossPay|netPay|basicSalary|totalDeductions|totalEarnings|"
    r"salary|gross|net|amount|loanAmount|repaymentAmount|"
    r"employerPension|employeePension|tax|nhf)"
    r"[`\"]?\s*\)",
    re.IGNORECASE,
)


# ─── SQL Parsing Helpers ───────────────────────────────────────────────────

def _extract_tables_from_sql(sql: str) -> Set[str]:
    """
    Extract view/table names referenced in a SQL query.

    Handles backtick-quoted schema.table patterns like:
        `hcmatrix-utility-db`.`v_employee_profile`
    """
    # Match `schema`.`table` patterns
    schema_table = re.findall(r'`[^`]+`\.`([^`]+)`', sql)

    # Match plain table names after FROM/JOIN keywords
    plain_table = re.findall(
        r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        sql, re.IGNORECASE,
    )

    return set(schema_table + plain_table)


def _sql_has_employee_id_filter(sql: str) -> bool:
    """Check if the SQL contains an employeeId filter (IN or =)."""
    return bool(re.search(
        r'employeeId\s*(IN\s*\(|=\s*)',
        sql, re.IGNORECASE,
    ))


def _sql_has_department_id_filter(sql: str) -> bool:
    """Check if the SQL contains a departmentId filter (IN or =)."""
    return bool(re.search(
        r'departmentId\s*(IN\s*\(|=\s*)',
        sql, re.IGNORECASE,
    ))


def _extract_employee_ids_from_sql(sql: str) -> Set[str]:
    """
    Extract employeeId values from IN(...) or = clauses in the SQL.

    Returns the set of IDs found. If the pattern is too complex to parse
    reliably, returns an empty set (which triggers a conservative block).
    """
    ids = set()

    # Match employeeId IN (1, 2, 3, ...)
    in_match = re.search(
        r'employeeId\s+IN\s*\(([^)]+)\)',
        sql, re.IGNORECASE,
    )
    if in_match:
        raw = in_match.group(1)
        # Extract numeric and quoted string IDs
        ids.update(re.findall(r"'([^']+)'", raw))
        ids.update(re.findall(r'\b(\d+)\b', raw))

    # Match employeeId = 116 or employeeId = '116'
    eq_match = re.findall(
        r"employeeId\s*=\s*'?(\d+)'?",
        sql, re.IGNORECASE,
    )
    ids.update(eq_match)

    return ids


def _has_salary_aggregates(sql: str) -> bool:
    """Check if the SQL uses aggregate functions on salary-related columns."""
    return bool(SALARY_AGGREGATE_PATTERN.search(sql))


# ─── Core Validation Logic ──────────────────────────────────────────────────

def validate_sql_query(sql: str, rbac_ctx: RBACContext) -> Optional[str]:
    """
    Validate a SQL query against the RBAC context.

    Returns None if the query is valid, or an error message string
    if the query violates RBAC rules.

    Args:
        sql: The SQL query to validate.
        rbac_ctx: The resolved RBAC context for the current user.

    Returns:
        None if valid, or an error message string if blocked.
    """
    sql_upper = sql.upper().strip()

    # ── 0. Block all non-SELECT statements ────────────────────────────────
    if not sql_upper.startswith("SELECT"):
        return (
            "SECURITY VIOLATION: Only SELECT statements are permitted. "
            "This query has been blocked."
        )

    tables = _extract_tables_from_sql(sql)

    # ── 1. Company scope — no additional filtering required ──────────────
    if rbac_ctx.scope_type == ScopeType.COMPANY:
        # Admin users have full access, but still enforce salary visibility
        # (salary visibility is determined by can_view_salary, not scope)
        # Admin always has can_view_salary=True, so no blocking needed here
        return None

    # ── 2. Salary protection ─────────────────────────────────────────────
    salary_tables_hit = tables & SALARY_PROTECTED_VIEWS
    if salary_tables_hit and not rbac_ctx.can_view_salary:
        # Check if the query ONLY targets the current user's own data
        extracted_ids = _extract_employee_ids_from_sql(sql)
        own_id = str(rbac_ctx.employee_id)

        if not extracted_ids:
            # Can't determine who is being queried — block conservatively
            return (
                "RBAC BLOCK: Salary-related data was requested but no employeeId filter "
                "was found. You may only view your own salary data. "
                f"Please add: WHERE employeeId = {own_id}"
            )

        other_ids = extracted_ids - {own_id}
        if other_ids:
            return (
                "RBAC BLOCK: You do not have permission to view salary or payroll data "
                "for other employees. Salary information is confidential. "
                "You may only view your own salary data."
            )

        # Check for salary aggregates that would include other employees
        if _has_salary_aggregates(sql) and len(extracted_ids) > 1:
            return (
                "RBAC BLOCK: Aggregate salary calculations (SUM, AVG, etc.) across "
                "multiple employees are not permitted when salary visibility is restricted. "
                "You may only view your own individual salary data."
            )

    # ── 3. Department-scoped views (v_department_summary) ────────────────
    dept_views_hit = tables & DEPARTMENT_SCOPED_VIEWS
    if dept_views_hit:
        if rbac_ctx.scope_type in (ScopeType.DEPARTMENT, ScopeType.DEPARTMENT_LARGE):
            if not _sql_has_department_id_filter(sql):
                dept_id_list = ", ".join(rbac_ctx.accessible_department_ids)
                return (
                    f"RBAC BLOCK: When querying {', '.join(dept_views_hit)}, you must filter "
                    f"by your accessible departments. "
                    f"Add: WHERE departmentId IN ({dept_id_list})"
                )
        elif rbac_ctx.scope_type in (ScopeType.TEAM, ScopeType.SELF_ONLY):
            return (
                "RBAC BLOCK: You do not have access to department-level summary views. "
                "These are only available to HOD and Admin roles."
            )

    # ── 4. Employee-scoped views — enforce employeeId filter ─────────────
    employee_views_hit = tables & EMPLOYEE_SCOPED_VIEWS
    if employee_views_hit:
        if not _sql_has_employee_id_filter(sql):
            emp_id_sample = ", ".join(rbac_ctx.accessible_employee_ids[:5])
            ellipsis = "..." if len(rbac_ctx.accessible_employee_ids) > 5 else ""
            return (
                f"RBAC BLOCK: Queries on {', '.join(employee_views_hit)} must include "
                f"an employeeId filter. You only have access to these employees: "
                f"({emp_id_sample}{ellipsis}). "
                f"Add: WHERE employeeId IN (...) using the Accessible Employee IDs "
                f"from the SECURE CONTEXT."
            )

        # Verify the IDs in the query are a subset of accessible IDs
        extracted_ids = _extract_employee_ids_from_sql(sql)
        if extracted_ids:
            allowed_ids = set(str(eid) for eid in rbac_ctx.accessible_employee_ids)
            unauthorized_ids = extracted_ids - allowed_ids
            if unauthorized_ids:
                return (
                    f"RBAC BLOCK: Your query references employee IDs that are outside "
                    f"your access scope: {', '.join(sorted(unauthorized_ids))}. "
                    f"You may only query employees within your authorized scope."
                )

    # ── 5. Public views — enforce department scoping for non-admin ────────
    public_views_hit = tables & PUBLIC_VIEWS - {"holidays", "v_employee_hmo_hospitals"}
    if public_views_hit:
        # For public directory/department views, HOD/team/self should be
        # limited to their department scope. We check if there's a department
        # filter present.
        if rbac_ctx.scope_type in (ScopeType.DEPARTMENT, ScopeType.DEPARTMENT_LARGE):
            # HOD can view their department subtree — check for dept filter
            # We allow it if they have a department name or ID filter
            has_dept_filter = (
                _sql_has_department_id_filter(sql)
                or any(
                    name.lower() in sql.lower()
                    for name in rbac_ctx.accessible_department_names
                )
            )
            if not has_dept_filter:
                # Check if this is a company-wide aggregation
                if re.search(r'\b(SUM|COUNT|AVG)\s*\(', sql, re.IGNORECASE):
                    dept_names = ", ".join(rbac_ctx.accessible_department_names)
                    return (
                        f"RBAC BLOCK: Company-wide aggregations on {', '.join(public_views_hit)} "
                        f"are not permitted for your scope. You only have access to: "
                        f"{dept_names}. Please filter by your department(s)."
                    )
        elif rbac_ctx.scope_type in (ScopeType.TEAM, ScopeType.SELF_ONLY):
            # Team/self scopes should not get company-wide directory aggregations
            if re.search(r'\b(SUM|COUNT|AVG)\s*\(', sql, re.IGNORECASE):
                return (
                    "RBAC BLOCK: Company-wide aggregations are not permitted for your "
                    "access scope. You may only view information within your team."
                )

    # ── All checks passed ────────────────────────────────────────────────
    return None


# ─── Validated Query Tool ────────────────────────────────────────────────────

# Patterns that indicate the database returned no rows
_EMPTY_RESULT_PATTERNS = [
    "",           # Completely empty string
    "[]",         # Empty list serialization
    "()",         # Empty tuple serialization
]

_EMPTY_RESULT_MESSAGE = (
    "QUERY RETURNED 0 ROWS. The SQL query was syntactically correct and executed "
    "successfully against the database, but no matching records were found. "
    "DO NOT fabricate, invent, or hallucinate any data. DO NOT generate sample "
    "or example records. You MUST inform the user that no records were found "
    "for the requested criteria. Suggest they check the date range or confirm "
    "the employee name."
)


def _is_empty_result(result: str) -> bool:
    """
    Determine if a query result string represents an empty / zero-row result.

    LangChain's QuerySQLDatabaseTool returns result rows as a string.
    An empty result is either a blank string, an empty collection literal,
    or whitespace only.
    """
    if not result or not result.strip():
        return True
    stripped = result.strip()
    if stripped in _EMPTY_RESULT_PATTERNS:
        return True
    return False


class RBACQueryTool(QuerySQLDatabaseTool):
    """
    A drop-in replacement for LangChain's QuerySQLDatabaseTool that validates
    every SQL query against the RBAC context before execution.

    If the query violates RBAC rules, returns an error message to the LLM
    instead of executing the query. The LLM can then reformulate or inform
    the user.

    Additionally, if the query executes successfully but returns zero rows,
    this tool returns a deterministic "no records found" message to prevent
    the LLM from hallucinating fabricated data.
    """

    rbac_ctx: Optional[RBACContext] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, query: str, **kwargs) -> str:
        """Validate and execute a SQL query."""
        if self.rbac_ctx is not None:
            error = validate_sql_query(query, self.rbac_ctx)
            if error:
                logger.warning(
                    "SQL BLOCKED for employee %s: %s | Query: %s",
                    self.rbac_ctx.employee_id, error, query[:200],
                )
                return error

        result = super()._run(query, **kwargs)

        # ── Anti-hallucination guard: intercept empty results ────────────
        if _is_empty_result(result):
            logger.info(
                "EMPTY RESULT for employee %s | Query: %s",
                self.rbac_ctx.employee_id if self.rbac_ctx else "unknown",
                query[:200],
            )
            return _EMPTY_RESULT_MESSAGE

        return result

    async def _arun(self, query: str, **kwargs) -> str:
        """Async validate and execute a SQL query."""
        if self.rbac_ctx is not None:
            error = validate_sql_query(query, self.rbac_ctx)
            if error:
                logger.warning(
                    "SQL BLOCKED for employee %s: %s | Query: %s",
                    self.rbac_ctx.employee_id, error, query[:200],
                )
                return error

        result = await super()._arun(query, **kwargs)

        # ── Anti-hallucination guard: intercept empty results ────────────
        if _is_empty_result(result):
            logger.info(
                "EMPTY RESULT for employee %s | Query: %s",
                self.rbac_ctx.employee_id if self.rbac_ctx else "unknown",
                query[:200],
            )
            return _EMPTY_RESULT_MESSAGE

        return result
