"""
Secure Context Builder — constructs the runtime security block
prepended to every user query before it reaches the SQL agent.

This replaces the old 3-line ``--- SECURE CONTEXT ---`` wrapper with
an RBAC-aware block that includes roles, scope, accessible IDs,
salary visibility, and conversation history.
"""

from module.rbac_models import RBACContext, ScopeType


def build_secure_context(rbac_ctx: RBACContext, query: str, chat_history: list = None) -> str:
    """
    Build the full input string for the SQL agent, including the RBAC
    security context, optional conversation history, and the user query.

    Args:
        rbac_ctx: Resolved RBAC context for the current user.
        query: The raw user query.
        chat_history: Optional list of prior Q&A dicts with 'question' and 'answer' keys.

    Returns:
        A single string ready to be passed as the agent's ``input``.
    """
    lines = [
        "--- SECURE CONTEXT ---",
        f"Current Company ID: {rbac_ctx.company_id}",
        f"Current Employee ID: {rbac_ctx.employee_id}",
        f"User Roles: {', '.join(rbac_ctx.role_names)}",
        f"Scope Type: {rbac_ctx.scope_type.value}",
    ]

    # ── Scope-specific access information ────────────────────────────────
    if rbac_ctx.scope_type == ScopeType.COMPANY:
        lines.append("Access: Full company access — no employee filtering required")
    elif rbac_ctx.scope_type == ScopeType.DEPARTMENT_LARGE:
        dept_str = ", ".join(rbac_ctx.accessible_department_ids)
        lines.append(f"Accessible Department IDs: {dept_str}")
        emp_str = ", ".join(rbac_ctx.accessible_employee_ids)
        lines.append(f"Accessible Employee IDs: {emp_str}")
    elif rbac_ctx.scope_type in (ScopeType.TEAM, ScopeType.DEPARTMENT):
        emp_str = ", ".join(rbac_ctx.accessible_employee_ids)
        lines.append(f"Accessible Employee IDs: {emp_str}")
    else:
        # SELF_ONLY
        lines.append(f"Accessible Employee IDs: {rbac_ctx.employee_id}")

    # ── Salary visibility ────────────────────────────────────────────────
    if rbac_ctx.can_view_salary:
        lines.append("Salary Visibility: FULL")
    else:
        lines.append("Salary Visibility: RESTRICTED (own data only)")

    lines.append("----------------------")

    # ── Conversation history ─────────────────────────────────────────────
    history_block = ""
    if chat_history:
        history_lines = []
        for pair in chat_history:
            history_lines.append(f"User: {pair['question']}")
            history_lines.append(f"Assistant: {pair['answer']}")
        history_block = (
            "--- CONVERSATION HISTORY ---\n"
            + "\n".join(history_lines)
            + "\n----------------------------\n"
        )

    # ── Assemble final input ─────────────────────────────────────────────
    secure_block = "\n".join(lines)
    return f"{secure_block}\n{history_block}User Query: {query}"
