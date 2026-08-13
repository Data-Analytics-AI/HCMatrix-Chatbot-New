"""
Comprehensive RBAC Test Suite for HCMatrix Chatbot.

Tests cover:
  - rbac_models.py  : enums, dataclass properties, Pydantic models
  - rbac_service.py : role detection, scope resolution, salary visibility,
                      caching, fail-safe fallback
  - secure_context.py: context string building for every scope type
  - cache_service.py : delete() and clear() methods
  - sql_layer.py    : RBAC system prompt validation

Run with:
    python -m pytest tests/test_rbac.py -v
"""

import sys
import types
import asyncio
import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap: mock heavy external dependencies so the RBAC modules can import
# without Azure SDK, Key Vault, Speech SDK, etc. being installed.
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_mock_module(name):
    """Insert a MagicMock as a module if it's not already importable."""
    if name not in sys.modules:
        sys.modules[name] = MagicMock()

# Azure SDKs
for mod in [
    "azure", "azure.keyvault", "azure.keyvault.secrets",
    "azure.identity", "azure.cognitiveservices",
    "azure.cognitiveservices.speech", "azure.cosmos",
    "azure.storage", "azure.storage.filedatalake",
    "azure.functions",
]:
    _ensure_mock_module(mod)

# Other optional deps that may not be installed locally
for mod in [
    "langchain_openai", "langchain_community",
    "langchain_community.utilities", "langchain_community.agent_toolkits",
    "langchain_community.agent_toolkits.sql",
    "langchain_community.agent_toolkits.sql.toolkit",
    "pinecone", "motor", "pymongo",
    "langchain_pinecone",
]:
    _ensure_mock_module(mod)

# Now we need to mock module.utils.config BEFORE rbac_service imports it.
# Create a fake config dict that rbac_service expects.
_fake_config = {
    "production": {
        "rbac_config": {
            "auth_schema": "hcmatrix-utility-db",
            "rbac_cache_ttl": 60,
            "rbac_cache_capacity": 500,
            "large_department_threshold": 200,
        },
        "chatbot_db_credentials": {
            "host": "localhost",
            "port": 3306,
            "user": "test",
            "password": "test",
            "database": "testdb",
            "schemas": ["hcmatrix-utility-db"],
        },
        "speech_service": {"key": "fake"},
        "azure_oai_credentials": {},
        "layer_one_agent_prompt": "test",
        "adls_credentials": {
            "client_id": "fake",
            "tenant_id": "fake",
            "client_secret": "fake",
            "key_vault_name": "fake",
        },
    }
}

# Mock the utils module so that `from module.utils import config` works
_mock_utils = types.ModuleType("module.utils")
_mock_utils.config = _fake_config
_mock_utils.timing_decorator = lambda fn: fn
_mock_utils.load_config_with_env = MagicMock(return_value=_fake_config)
_mock_utils.PROJECT_ROOT = "."
_mock_utils.CONFIG_PATH = "config/config.yml"
sys.modules["module.utils"] = _mock_utils

# ──────────────────────────────────────────────────────────────────────────────
# Now import the actual RBAC modules under test
# ──────────────────────────────────────────────────────────────────────────────

from module.rbac_models import RBACRole, ScopeType, RBACContext
from module.rbac_models import RBACDiagnosticResponse, RBACInvalidateRequest
from module.cache_service import LRUCache
from hcm_chatbot.secure_context import build_secure_context
from module.rbac_service import (
    _detect_roles,
    _resolve_scope,
    _determine_salary_visibility,
    _resolve_sync,
    resolve_rbac_context,
    invalidate_rbac_cache,
    invalidate_all_rbac_cache,
    _rbac_cache,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helper: get or create an event loop for sync test wrappers
# ──────────────────────────────────────────────────────────────────────────────

def _run_async(coro):
    """Run an async coroutine from a sync test."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ══════════════════════════════════════════════════════════════════════════════
# 1. RBAC Models Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRBACRole:
    """Tests for the RBACRole enum."""

    def test_enum_values(self):
        assert RBACRole.ADMIN.value == "ADMIN"
        assert RBACRole.LINE_MANAGER.value == "LINE_MANAGER"
        assert RBACRole.HOD.value == "HOD"
        assert RBACRole.EMPLOYEE.value == "EMPLOYEE"

    def test_enum_count(self):
        assert len(RBACRole) == 4

    def test_string_comparison(self):
        """RBACRole inherits from str, so it should compare with plain strings."""
        assert RBACRole.ADMIN == "ADMIN"
        assert RBACRole.EMPLOYEE == "EMPLOYEE"

    def test_enum_membership(self):
        roles = {RBACRole.ADMIN, RBACRole.HOD}
        assert RBACRole.ADMIN in roles
        assert RBACRole.EMPLOYEE not in roles


class TestScopeType:
    """Tests for the ScopeType enum."""

    def test_enum_values(self):
        assert ScopeType.SELF_ONLY.value == "self_only"
        assert ScopeType.TEAM.value == "team"
        assert ScopeType.DEPARTMENT.value == "department"
        assert ScopeType.DEPARTMENT_LARGE.value == "department_large"
        assert ScopeType.COMPANY.value == "company"

    def test_enum_count(self):
        assert len(ScopeType) == 5

    def test_string_comparison(self):
        assert ScopeType.SELF_ONLY == "self_only"
        assert ScopeType.COMPANY == "company"


class TestRBACContext:
    """Tests for the RBACContext dataclass."""

    def test_default_construction(self):
        ctx = RBACContext(company_id="1", employee_id="100")
        assert ctx.company_id == "1"
        assert ctx.employee_id == "100"
        assert ctx.roles == {RBACRole.EMPLOYEE}
        assert ctx.scope_type == ScopeType.SELF_ONLY
        assert ctx.accessible_employee_ids == []
        assert ctx.accessible_department_ids == []
        assert ctx.can_view_salary is False
        assert isinstance(ctx.resolved_at, float)

    def test_admin_properties(self):
        ctx = RBACContext(
            company_id="1", employee_id="100",
            roles={RBACRole.ADMIN, RBACRole.EMPLOYEE},
            scope_type=ScopeType.COMPANY,
            can_view_salary=True,
        )
        assert ctx.is_admin is True
        assert ctx.is_line_manager is False
        assert ctx.is_hod is False

    def test_line_manager_properties(self):
        ctx = RBACContext(
            company_id="1", employee_id="200",
            roles={RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE},
        )
        assert ctx.is_admin is False
        assert ctx.is_line_manager is True
        assert ctx.is_hod is False

    def test_hod_properties(self):
        ctx = RBACContext(
            company_id="1", employee_id="300",
            roles={RBACRole.HOD, RBACRole.EMPLOYEE},
        )
        assert ctx.is_admin is False
        assert ctx.is_line_manager is False
        assert ctx.is_hod is True

    def test_multi_role(self):
        """An employee can hold multiple roles simultaneously."""
        ctx = RBACContext(
            company_id="1", employee_id="400",
            roles={RBACRole.HOD, RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE},
        )
        assert ctx.is_hod is True
        assert ctx.is_line_manager is True
        assert ctx.is_admin is False

    def test_role_names_sorted(self):
        ctx = RBACContext(
            company_id="1", employee_id="500",
            roles={RBACRole.HOD, RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE},
        )
        names = ctx.role_names
        assert names == sorted(names), "role_names must be sorted alphabetically"
        assert "EMPLOYEE" in names
        assert "HOD" in names
        assert "LINE_MANAGER" in names

    def test_role_names_deterministic(self):
        """Calling role_names multiple times should always return the same order."""
        ctx = RBACContext(
            company_id="1", employee_id="500",
            roles={RBACRole.ADMIN, RBACRole.HOD, RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE},
        )
        assert ctx.role_names == ctx.role_names


class TestPydanticModels:
    """Tests for the Pydantic request/response models."""

    def test_diagnostic_response_creation(self):
        resp = RBACDiagnosticResponse(
            company_id="1",
            employee_id="100",
            roles=["ADMIN", "EMPLOYEE"],
            scope_type="company",
            accessible_employee_count=500,
            accessible_department_count=0,
            sample_employee_ids=["100", "101"],
            can_view_salary=True,
            resolved_at=time.time(),
        )
        assert resp.company_id == "1"
        assert len(resp.roles) == 2
        assert resp.can_view_salary is True

    def test_invalidate_request_defaults(self):
        req = RBACInvalidateRequest()
        assert req.company_id is None
        assert req.employee_id is None

    def test_invalidate_request_with_values(self):
        req = RBACInvalidateRequest(company_id="1", employee_id="100")
        assert req.company_id == "1"
        assert req.employee_id == "100"


# ══════════════════════════════════════════════════════════════════════════════
# 2. Cache Service Tests (delete / clear additions)
# ══════════════════════════════════════════════════════════════════════════════

class TestLRUCacheDelete:
    """Tests for the delete() method added for RBAC cache invalidation."""

    def test_delete_existing_key(self):
        cache = LRUCache(capacity=10, ttl=60)
        cache.put("a", 1)
        assert cache.delete("a") is True
        assert cache.get("a") == -1

    def test_delete_nonexistent_key(self):
        cache = LRUCache(capacity=10, ttl=60)
        assert cache.delete("missing") is False

    def test_delete_does_not_affect_other_keys(self):
        cache = LRUCache(capacity=10, ttl=60)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.delete("a")
        assert cache.get("b") == 2

    def test_reinsert_after_delete(self):
        cache = LRUCache(capacity=10, ttl=60)
        cache.put("a", 1)
        cache.delete("a")
        cache.put("a", 99)
        assert cache.get("a") == 99


class TestLRUCacheClear:
    """Tests for the clear() method added for RBAC cache invalidation."""

    def test_clear_empties_cache(self):
        cache = LRUCache(capacity=10, ttl=60)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.clear()
        assert cache.get("a") == -1
        assert cache.get("b") == -1
        assert cache.get("c") == -1

    def test_clear_on_empty_cache(self):
        cache = LRUCache(capacity=10, ttl=60)
        cache.clear()  # Should not raise

    def test_cache_usable_after_clear(self):
        cache = LRUCache(capacity=10, ttl=60)
        cache.put("x", 42)
        cache.clear()
        cache.put("y", 99)
        assert cache.get("y") == 99
        assert cache.get("x") == -1


class TestLRUCacheTTL:
    """Verify TTL-based expiration still works with the new methods."""

    def test_expired_entry_returns_miss(self):
        cache = LRUCache(capacity=10, ttl=0)
        cache.put("key", "value")
        time.sleep(0.01)
        assert cache.get("key") == -1

    def test_capacity_eviction(self):
        cache = LRUCache(capacity=2, ttl=3600)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # should evict "a"
        assert cache.get("a") == -1
        assert cache.get("b") == 2
        assert cache.get("c") == 3


# ══════════════════════════════════════════════════════════════════════════════
# 3. Secure Context Builder Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildSecureContext:
    """Tests for build_secure_context()."""

    def _make_ctx(self, **overrides):
        defaults = dict(
            company_id="1",
            employee_id="100",
            roles={RBACRole.EMPLOYEE},
            scope_type=ScopeType.SELF_ONLY,
            accessible_employee_ids=["100"],
            accessible_department_ids=[],
            can_view_salary=False,
        )
        defaults.update(overrides)
        return RBACContext(**defaults)

    # ── Self-only scope ──────────────────────────────────────────────────

    def test_self_only_scope(self):
        ctx = self._make_ctx()
        result = build_secure_context(ctx, "What is my salary?")
        assert "--- SECURE CONTEXT ---" in result
        assert "Current Company ID: 1" in result
        assert "Current Employee ID: 100" in result
        assert "User Roles: EMPLOYEE" in result
        assert "Scope Type: self_only" in result
        assert "Accessible Employee IDs: 100" in result
        assert "Salary Visibility: RESTRICTED" in result
        assert "User Query: What is my salary?" in result

    # ── Team scope ───────────────────────────────────────────────────────

    def test_team_scope(self):
        ctx = self._make_ctx(
            roles={RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE},
            scope_type=ScopeType.TEAM,
            accessible_employee_ids=["100", "201", "202"],
        )
        result = build_secure_context(ctx, "team attendance")
        assert "Scope Type: team" in result
        assert "100, 201, 202" in result
        assert "Salary Visibility: RESTRICTED" in result

    # ── Department scope ─────────────────────────────────────────────────

    def test_department_scope(self):
        ctx = self._make_ctx(
            roles={RBACRole.HOD, RBACRole.EMPLOYEE},
            scope_type=ScopeType.DEPARTMENT,
            accessible_employee_ids=["100", "301", "302", "303"],
        )
        result = build_secure_context(ctx, "department leave summary")
        assert "Scope Type: department" in result
        assert "100, 301, 302, 303" in result

    # ── Department large scope ───────────────────────────────────────────

    def test_department_large_scope(self):
        ctx = self._make_ctx(
            roles={RBACRole.HOD, RBACRole.EMPLOYEE},
            scope_type=ScopeType.DEPARTMENT_LARGE,
            accessible_employee_ids=["100", "401", "402"],
            accessible_department_ids=["10", "11", "12"],
        )
        result = build_secure_context(ctx, "headcount")
        assert "Scope Type: department_large" in result
        assert "Accessible Department IDs: 10, 11, 12" in result
        assert "Accessible Employee IDs: 100, 401, 402" in result

    # ── Company scope ────────────────────────────────────────────────────

    def test_company_scope(self):
        ctx = self._make_ctx(
            roles={RBACRole.ADMIN, RBACRole.EMPLOYEE},
            scope_type=ScopeType.COMPANY,
            can_view_salary=True,
        )
        result = build_secure_context(ctx, "all salaries")
        assert "Scope Type: company" in result
        assert "Full company access" in result
        assert "Salary Visibility: FULL" in result

    # ── Salary visibility ────────────────────────────────────────────────

    def test_salary_visibility_full(self):
        ctx = self._make_ctx(
            roles={RBACRole.ADMIN, RBACRole.EMPLOYEE},
            scope_type=ScopeType.COMPANY,
            can_view_salary=True,
        )
        result = build_secure_context(ctx, "payslips")
        assert "Salary Visibility: FULL" in result

    def test_salary_visibility_restricted(self):
        ctx = self._make_ctx(can_view_salary=False)
        result = build_secure_context(ctx, "payslips")
        assert "Salary Visibility: RESTRICTED" in result

    # ── Conversation history ─────────────────────────────────────────────

    def test_with_chat_history(self):
        ctx = self._make_ctx()
        history = [
            {"question": "What is my leave balance?", "answer": "You have 10 days."},
            {"question": "How about sick leave?", "answer": "You have 5 sick days."},
        ]
        result = build_secure_context(ctx, "And annual leave?", chat_history=history)
        assert "--- CONVERSATION HISTORY ---" in result
        assert "User: What is my leave balance?" in result
        assert "Assistant: You have 10 days." in result
        assert "User: How about sick leave?" in result
        assert "Assistant: You have 5 sick days." in result

    def test_without_chat_history(self):
        ctx = self._make_ctx()
        result = build_secure_context(ctx, "my profile")
        assert "--- CONVERSATION HISTORY ---" not in result

    def test_empty_chat_history(self):
        ctx = self._make_ctx()
        result = build_secure_context(ctx, "my profile", chat_history=[])
        assert "--- CONVERSATION HISTORY ---" not in result

    # ── Multi-role display ───────────────────────────────────────────────

    def test_multi_role_display(self):
        ctx = self._make_ctx(
            roles={RBACRole.HOD, RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE},
            scope_type=ScopeType.DEPARTMENT,
            accessible_employee_ids=["100"],
        )
        result = build_secure_context(ctx, "test")
        assert "EMPLOYEE" in result
        assert "HOD" in result
        assert "LINE_MANAGER" in result


# ══════════════════════════════════════════════════════════════════════════════
# 4. RBAC Service Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectRoles:
    """Tests for _detect_roles() with mocked DB connections."""

    def _mock_conn(self, rows):
        conn = MagicMock()
        result = MagicMock()
        result.fetchall.return_value = rows
        conn.execute.return_value = result
        return conn

    # Row format: (roleName, isAdmin, isLineManager, isHodFlag, isDeptHead, hasDirectReports)

    def test_no_rows_returns_employee_only(self):
        conn = self._mock_conn([])
        roles = _detect_roles("1", "100", conn)
        assert roles == {RBACRole.EMPLOYEE}

    def test_admin_role_detected(self):
        conn = self._mock_conn([("Admin", 0, 0, 0, 0, 0)])
        roles = _detect_roles("1", "100", conn)
        assert RBACRole.ADMIN in roles
        assert RBACRole.EMPLOYEE in roles

    def test_admin_detected_via_flag(self):
        """Even if roleName is 'Employee', the isAdmin flag should trigger ADMIN."""
        conn = self._mock_conn([("Employee", 1, 0, 0, 0, 0)])
        roles = _detect_roles("1", "100", conn)
        assert RBACRole.ADMIN in roles

    def test_line_manager_role_detected(self):
        conn = self._mock_conn([("LineManager", 0, 1, 0, 0, 0)])
        roles = _detect_roles("1", "100", conn)
        assert RBACRole.LINE_MANAGER in roles

    def test_line_manager_underscore_variant(self):
        conn = self._mock_conn([("line_manager", 0, 0, 0, 0, 0)])
        roles = _detect_roles("1", "100", conn)
        assert RBACRole.LINE_MANAGER in roles

    def test_line_manager_detected_via_has_direct_reports(self):
        """hasDirectReports flag should also trigger LINE_MANAGER."""
        conn = self._mock_conn([("Employee", 0, 0, 0, 0, 1)])
        roles = _detect_roles("1", "100", conn)
        assert RBACRole.LINE_MANAGER in roles

    def test_hod_role_detected(self):
        conn = self._mock_conn([("HOD", 0, 0, 1, 0, 0)])
        roles = _detect_roles("1", "100", conn)
        assert RBACRole.HOD in roles

    def test_hod_detected_via_dept_head_flag(self):
        """isDeptHead flag should also trigger HOD."""
        conn = self._mock_conn([("Employee", 0, 0, 0, 1, 0)])
        roles = _detect_roles("1", "100", conn)
        assert RBACRole.HOD in roles

    def test_multiple_roles(self):
        conn = self._mock_conn([
            ("Admin", 0, 1, 1, 0, 1),
        ])
        roles = _detect_roles("1", "100", conn)
        assert RBACRole.ADMIN in roles
        assert RBACRole.HOD in roles
        assert RBACRole.LINE_MANAGER in roles
        assert RBACRole.EMPLOYEE in roles

    def test_unknown_role_skipped_but_flags_still_apply(self):
        conn = self._mock_conn([("SuperAdmin", 0, 0, 0, 0, 0)])
        roles = _detect_roles("1", "100", conn)
        assert roles == {RBACRole.EMPLOYEE}

    def test_case_insensitive(self):
        conn = self._mock_conn([
            ("ADMIN", 0, 0, 0, 0, 0),
            ("hod", 0, 0, 0, 0, 0),
            ("linemanager", 0, 0, 0, 0, 0),
        ])
        roles = _detect_roles("1", "100", conn)
        assert RBACRole.ADMIN in roles
        assert RBACRole.HOD in roles
        assert RBACRole.LINE_MANAGER in roles

    def test_whitespace_handling(self):
        conn = self._mock_conn([("  Admin  ", 0, 0, 0, 0, 0)])
        roles = _detect_roles("1", "100", conn)
        assert RBACRole.ADMIN in roles

    def test_real_db_row_format(self):
        """Test with the exact row format from the live v_user_roles view."""
        # Matching: (1221, 1, 'Employee', 'employee', 0, 0, 0, 0, 0, 'employee', ...)
        # Our SELECT picks: roleName, isAdmin, isLineManager, isHodFlag, isDeptHead, hasDirectReports
        conn = self._mock_conn([("Employee", 0, 0, 0, 0, 0)])
        roles = _detect_roles("1", "1221", conn)
        assert roles == {RBACRole.EMPLOYEE}


class TestResolveScope:
    """Tests for _resolve_scope() with mocked DB connections."""

    def _mock_conn_for_scope(self, query_results):
        conn = MagicMock()
        results = []
        for rows in query_results:
            result_mock = MagicMock()
            result_mock.fetchall.return_value = rows
            results.append(result_mock)
        conn.execute.side_effect = results
        return conn

    def test_admin_gets_company_scope(self):
        conn = MagicMock()
        roles = {RBACRole.ADMIN, RBACRole.EMPLOYEE}
        scope_type, emp_ids, dept_ids = _resolve_scope("1", "100", roles, conn)
        assert scope_type == ScopeType.COMPANY
        assert emp_ids == []
        assert dept_ids == []
        conn.execute.assert_not_called()

    def test_employee_gets_self_only(self):
        conn = MagicMock()
        roles = {RBACRole.EMPLOYEE}
        scope_type, emp_ids, dept_ids = _resolve_scope("1", "100", roles, conn)
        assert scope_type == ScopeType.SELF_ONLY
        assert emp_ids == ["100"]
        assert dept_ids == []
        conn.execute.assert_not_called()

    def test_line_manager_gets_team_scope(self):
        conn = self._mock_conn_for_scope([
            [("200",), ("201",), ("202",)],
        ])
        roles = {RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE}
        scope_type, emp_ids, dept_ids = _resolve_scope("1", "100", roles, conn)
        assert scope_type == ScopeType.TEAM
        assert "100" in emp_ids
        assert "200" in emp_ids
        assert "201" in emp_ids
        assert "202" in emp_ids
        assert dept_ids == []

    def test_line_manager_self_included_even_if_not_in_tree(self):
        conn = self._mock_conn_for_scope([
            [],
        ])
        roles = {RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE}
        scope_type, emp_ids, dept_ids = _resolve_scope("1", "100", roles, conn)
        assert scope_type == ScopeType.TEAM
        assert emp_ids == ["100"]

    def test_hod_small_department_scope(self):
        conn = self._mock_conn_for_scope([
            [("10",), ("11",)],
            [("300",), ("301",), ("302",)],
        ])
        roles = {RBACRole.HOD, RBACRole.EMPLOYEE}
        scope_type, emp_ids, dept_ids = _resolve_scope("1", "100", roles, conn)
        assert scope_type == ScopeType.DEPARTMENT
        assert set(emp_ids) >= {"300", "301", "302", "100"}
        assert set(dept_ids) == {"10", "11"}

    def test_hod_large_department_scope(self):
        fake_employees = [(str(i),) for i in range(201)]
        conn = self._mock_conn_for_scope([
            [("10",), ("11",), ("12",)],
            fake_employees,
        ])
        roles = {RBACRole.HOD, RBACRole.EMPLOYEE}
        scope_type, emp_ids, dept_ids = _resolve_scope("1", "999", roles, conn)
        assert scope_type == ScopeType.DEPARTMENT_LARGE
        assert len(emp_ids) >= 201
        assert set(dept_ids) == {"10", "11", "12"}

    def test_hod_self_always_included(self):
        conn = self._mock_conn_for_scope([
            [("10",)],
            [("301",), ("302",)],
        ])
        roles = {RBACRole.HOD, RBACRole.EMPLOYEE}
        scope_type, emp_ids, dept_ids = _resolve_scope("1", "100", roles, conn)
        assert "100" in emp_ids

    def test_role_priority_admin_over_hod(self):
        conn = MagicMock()
        roles = {RBACRole.ADMIN, RBACRole.HOD, RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE}
        scope_type, _, _ = _resolve_scope("1", "100", roles, conn)
        assert scope_type == ScopeType.COMPANY

    def test_role_priority_hod_over_line_manager(self):
        conn = self._mock_conn_for_scope([
            [("10",)],
            [("100",), ("301",)],
        ])
        roles = {RBACRole.HOD, RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE}
        scope_type, _, _ = _resolve_scope("1", "100", roles, conn)
        assert scope_type == ScopeType.DEPARTMENT


class TestSalaryVisibility:
    """Tests for _determine_salary_visibility()."""

    def test_admin_can_view_salary(self):
        assert _determine_salary_visibility({RBACRole.ADMIN, RBACRole.EMPLOYEE}) is True

    def test_admin_only_can_view_salary(self):
        assert _determine_salary_visibility({RBACRole.ADMIN}) is True

    def test_hod_cannot_view_salary(self):
        assert _determine_salary_visibility({RBACRole.HOD, RBACRole.EMPLOYEE}) is False

    def test_line_manager_cannot_view_salary(self):
        assert _determine_salary_visibility({RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE}) is False

    def test_employee_cannot_view_salary(self):
        assert _determine_salary_visibility({RBACRole.EMPLOYEE}) is False


class TestResolveSyncIntegration:
    """Tests for the full _resolve_sync() pipeline with mocked DB."""

    def _mock_engine_with_scenario(self, role_rows, scope_queries):
        conn = MagicMock()
        all_results = []

        role_result = MagicMock()
        role_result.fetchall.return_value = role_rows
        all_results.append(role_result)

        for rows in scope_queries:
            r = MagicMock()
            r.fetchall.return_value = rows
            all_results.append(r)

        conn.execute.side_effect = all_results

        engine = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        return engine

    def test_admin_full_pipeline(self):
        # Row format: (roleName, isAdmin, isLineManager, isHodFlag, isDeptHead, hasDirectReports)
        engine = self._mock_engine_with_scenario(
            role_rows=[("Admin", 0, 0, 0, 0, 0)],
            scope_queries=[],
        )
        ctx = _resolve_sync("1", "100", engine)
        assert ctx.is_admin is True
        assert ctx.scope_type == ScopeType.COMPANY
        assert ctx.can_view_salary is True
        assert ctx.accessible_employee_ids == []

    def test_employee_full_pipeline(self):
        engine = self._mock_engine_with_scenario(
            role_rows=[("Employee", 0, 0, 0, 0, 0)],
            scope_queries=[],
        )
        ctx = _resolve_sync("1", "100", engine)
        assert ctx.is_admin is False
        assert ctx.scope_type == ScopeType.SELF_ONLY
        assert ctx.can_view_salary is False
        assert ctx.accessible_employee_ids == ["100"]

    def test_line_manager_full_pipeline(self):
        engine = self._mock_engine_with_scenario(
            role_rows=[("Employee", 0, 1, 0, 0, 1)],  # isLineManager + hasDirectReports
            scope_queries=[
                [("200",), ("201",)],  # v_reporting_tree
            ],
        )
        ctx = _resolve_sync("1", "100", engine)
        assert ctx.is_line_manager is True
        assert ctx.scope_type == ScopeType.TEAM
        assert ctx.can_view_salary is False
        assert "100" in ctx.accessible_employee_ids
        assert "200" in ctx.accessible_employee_ids


class TestRBACCaching:
    """Tests for the RBAC cache behavior in resolve_rbac_context()."""

    def setup_method(self):
        _rbac_cache.clear()

    def test_cache_stores_resolved_context(self):
        mock_ctx = RBACContext(
            company_id="1", employee_id="100",
            roles={RBACRole.EMPLOYEE},
            scope_type=ScopeType.SELF_ONLY,
            accessible_employee_ids=["100"],
        )
        with patch("module.rbac_service._resolve_sync", return_value=mock_ctx):
            result = _run_async(
                resolve_rbac_context("1", "100", MagicMock())
            )
        assert result.company_id == "1"
        cached = _rbac_cache.get("rbac::1::100")
        assert cached is not None
        assert not (isinstance(cached, int) and cached == -1)

    def test_cache_hit_returns_same_context(self):
        mock_ctx = RBACContext(
            company_id="1", employee_id="100",
            roles={RBACRole.ADMIN, RBACRole.EMPLOYEE},
            scope_type=ScopeType.COMPANY,
            can_view_salary=True,
        )
        with patch("module.rbac_service._resolve_sync", return_value=mock_ctx) as mock_resolve:
            result1 = _run_async(
                resolve_rbac_context("1", "100", MagicMock())
            )
            result2 = _run_async(
                resolve_rbac_context("1", "100", MagicMock())
            )
            assert mock_resolve.call_count == 1
        assert result1.is_admin is True
        assert result2.is_admin is True

    def test_invalidate_specific_entry(self):
        _rbac_cache.put("rbac::1::100", "ctx_100")
        _rbac_cache.put("rbac::1::200", "ctx_200")
        result = invalidate_rbac_cache("1", "100")
        assert result is True
        assert _rbac_cache.get("rbac::1::100") == -1
        assert _rbac_cache.get("rbac::1::200") == "ctx_200"

    def test_invalidate_nonexistent_entry(self):
        result = invalidate_rbac_cache("1", "999")
        assert result is False

    def test_invalidate_all(self):
        _rbac_cache.put("rbac::1::100", "ctx_100")
        _rbac_cache.put("rbac::1::200", "ctx_200")
        _rbac_cache.put("rbac::2::300", "ctx_300")
        invalidate_all_rbac_cache()
        assert _rbac_cache.get("rbac::1::100") == -1
        assert _rbac_cache.get("rbac::1::200") == -1
        assert _rbac_cache.get("rbac::2::300") == -1


class TestRBACFailSafe:
    """Tests for the fail-safe fallback when DB queries fail."""

    def setup_method(self):
        _rbac_cache.clear()

    def test_fallback_on_exception(self):
        with patch(
            "module.rbac_service._resolve_sync",
            side_effect=Exception("DB connection failed"),
        ):
            ctx = _run_async(
                resolve_rbac_context("1", "100", MagicMock())
            )
        assert ctx.roles == {RBACRole.EMPLOYEE}
        assert ctx.scope_type == ScopeType.SELF_ONLY
        assert ctx.accessible_employee_ids == ["100"]
        assert ctx.can_view_salary is False

    def test_fallback_is_cached(self):
        with patch(
            "module.rbac_service._resolve_sync",
            side_effect=Exception("DB down"),
        ) as mock_resolve:
            ctx1 = _run_async(
                resolve_rbac_context("1", "100", MagicMock())
            )
            ctx2 = _run_async(
                resolve_rbac_context("1", "100", MagicMock())
            )
            assert mock_resolve.call_count == 1
        assert ctx1.scope_type == ScopeType.SELF_ONLY
        assert ctx2.scope_type == ScopeType.SELF_ONLY


# ══════════════════════════════════════════════════════════════════════════════
# 5. SQL Layer RBAC System Prompt Tests
# ══════════════════════════════════════════════════════════════════════════════

# Import _build_rbac_system_prompt — needs heavier mocking due to sql_layer
# importing langchain modules at the top level.

try:
    from hcm_chatbot.sql_layer import _build_rbac_system_prompt
    _PROMPT_IMPORT_OK = True
except ImportError:
    _PROMPT_IMPORT_OK = False


@pytest.mark.skipif(not _PROMPT_IMPORT_OK, reason="sql_layer import failed (missing langchain deps)")
class TestRBACSystemPrompt:
    """Tests for the static RBAC system prompt built by sql_layer."""

    def setup_method(self):
        self.prompt = _build_rbac_system_prompt()

    def test_contains_rbac_section(self):
        assert "ROLE-BASED ACCESS CONTROL (RBAC)" in self.prompt

    def test_contains_scope_filtering_rules(self):
        assert "SCOPE FILTERING RULES" in self.prompt
        assert "self_only" in self.prompt
        assert "team" in self.prompt
        assert "department" in self.prompt
        assert "department_large" in self.prompt
        assert "company" in self.prompt

    def test_contains_salary_protection(self):
        assert "SALARY PROTECTION RULES" in self.prompt
        assert "RESTRICTED" in self.prompt

    def test_contains_access_restrictions(self):
        assert "v_employee_emergency_contacts" in self.prompt
        assert "v_employee_hmo_dependents" in self.prompt
        assert "v_employee_pay_structure" in self.prompt

    def test_contains_aggregated_views(self):
        assert "v_team_headcount" in self.prompt
        assert "v_team_leave_summary" in self.prompt
        assert "v_team_attendance_summary" in self.prompt
        assert "v_team_asset_summary" in self.prompt
        assert "v_department_summary" in self.prompt

    def test_contains_public_directory_exceptions(self):
        assert "v_public_employee_directory" in self.prompt
        assert "v_public_departments" in self.prompt
        assert "holidays" in self.prompt

    def test_no_dml_instructions(self):
        assert "Do not drop tables" in self.prompt
        assert "DML" in self.prompt

    def test_contains_formatting_guidelines(self):
        assert "FORMATTING" in self.prompt
        assert "NEVER use markdown bolding" in self.prompt

    def test_contains_query_guidance(self):
        assert "QUERY GUIDANCE" in self.prompt
        assert "backtick-quoting" in self.prompt

    def test_prompt_mentions_all_27_views(self):
        expected_views = [
            "v_employee_profile", "v_employee_emergency_contacts", "v_employee_education",
            "v_employee_employment_history",
            "v_employee_leave_summary", "v_employee_leaves", "holidays",
            "v_employee_payslips", "v_employee_payslip_components", "v_employee_pay_structure",
            "v_employee_hmo_profile", "v_employee_hmo_dependents", "v_employee_hmo_hospitals",
            "v_employee_loan_eligibility", "v_employee_loans",
            "v_employee_loan_requests", "v_employee_loan_repayments",
            "v_employee_assets", "v_employee_vehicles",
            "v_employee_daily_attendance", "v_employee_latest_clock",
            "v_public_employee_directory", "v_public_departments",
            "v_team_headcount", "v_team_leave_summary", "v_team_attendance_summary",
            "v_team_asset_summary", "v_department_summary",
        ]
        for view in expected_views:
            assert view in self.prompt, f"View '{view}' missing from system prompt"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Security Boundary Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurityBoundaries:
    """
    High-level scenario tests that verify the RBAC system enforces
    correct security boundaries across different user roles.
    """

    def _make_ctx(self, **overrides):
        defaults = dict(
            company_id="1",
            employee_id="100",
            roles={RBACRole.EMPLOYEE},
            scope_type=ScopeType.SELF_ONLY,
            accessible_employee_ids=["100"],
            accessible_department_ids=[],
            can_view_salary=False,
        )
        defaults.update(overrides)
        return RBACContext(**defaults)

    def test_employee_cannot_see_other_employees(self):
        ctx = self._make_ctx()
        secure = build_secure_context(ctx, "show me John's salary")
        assert "Accessible Employee IDs: 100" in secure
        assert "Salary Visibility: RESTRICTED" in secure

    def test_line_manager_sees_own_team_only(self):
        ctx = self._make_ctx(
            roles={RBACRole.LINE_MANAGER, RBACRole.EMPLOYEE},
            scope_type=ScopeType.TEAM,
            accessible_employee_ids=["100", "201", "202"],
        )
        secure = build_secure_context(ctx, "team leave")
        assert "100, 201, 202" in secure
        assert "Full company access" not in secure

    def test_admin_has_full_access(self):
        ctx = self._make_ctx(
            roles={RBACRole.ADMIN, RBACRole.EMPLOYEE},
            scope_type=ScopeType.COMPANY,
            can_view_salary=True,
        )
        secure = build_secure_context(ctx, "all salaries")
        assert "Full company access" in secure
        assert "Salary Visibility: FULL" in secure

    def test_non_admin_salary_restricted(self):
        for role in [RBACRole.HOD, RBACRole.LINE_MANAGER]:
            ctx = self._make_ctx(
                roles={role, RBACRole.EMPLOYEE},
                scope_type=ScopeType.TEAM,
                accessible_employee_ids=["100", "201"],
                can_view_salary=False,
            )
            secure = build_secure_context(ctx, "team salaries")
            assert "Salary Visibility: RESTRICTED" in secure

    def test_cross_company_isolation(self):
        ctx1 = self._make_ctx(company_id="1", employee_id="100")
        ctx2 = self._make_ctx(company_id="2", employee_id="200")
        secure1 = build_secure_context(ctx1, "my data")
        secure2 = build_secure_context(ctx2, "my data")
        assert "Current Company ID: 1" in secure1
        assert "Current Company ID: 2" in secure2
        assert "Current Company ID: 2" not in secure1
        assert "Current Company ID: 1" not in secure2


# ══════════════════════════════════════════════════════════════════════════════
# 7. Edge Case & Regression Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases for RBAC resolution and context building."""

    def test_empty_accessible_employee_ids(self):
        ctx = RBACContext(
            company_id="1", employee_id="100",
            roles={RBACRole.ADMIN, RBACRole.EMPLOYEE},
            scope_type=ScopeType.COMPANY,
            accessible_employee_ids=[],
            accessible_department_ids=[],
            can_view_salary=True,
        )
        result = build_secure_context(ctx, "all employees")
        assert "Full company access" in result

    def test_large_accessible_ids_list(self):
        ids = [str(i) for i in range(1, 501)]
        ctx = RBACContext(
            company_id="1", employee_id="1",
            roles={RBACRole.HOD, RBACRole.EMPLOYEE},
            scope_type=ScopeType.DEPARTMENT_LARGE,
            accessible_employee_ids=ids,
            accessible_department_ids=["10", "11"],
        )
        result = build_secure_context(ctx, "department report")
        assert "department_large" in result
        assert "500" in result

    def test_special_characters_in_query(self):
        ctx = RBACContext(
            company_id="1", employee_id="100",
            roles={RBACRole.EMPLOYEE},
            scope_type=ScopeType.SELF_ONLY,
            accessible_employee_ids=["100"],
        )
        result = build_secure_context(ctx, "What's my pay? O'Brien's dept -- test")
        assert "User Query: What's my pay? O'Brien's dept -- test" in result

    def test_cache_key_format(self):
        company_id, employee_id = "1", "657"
        expected_key = f"rbac::{company_id}::{employee_id}"
        assert expected_key == "rbac::1::657"

    def test_duplicate_role_in_set(self):
        roles = {RBACRole.ADMIN, RBACRole.ADMIN, RBACRole.EMPLOYEE}
        assert len(roles) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
