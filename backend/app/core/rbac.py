from enum import Enum
from typing import Dict, Any, Tuple, Optional
from fastapi import HTTPException, status, Depends
from app.core.security import get_current_user_role
import logging

logger = logging.getLogger("NexusAI-RBAC")

class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

# Hierarchy ranking: Higher numeric value means greater authority
ROLE_HIERARCHY: Dict[Role, int] = {
    Role.ADMIN: 3,
    Role.OPERATOR: 2,
    Role.VIEWER: 1,
}

# Alias mapping for legacy roles (e.g., 'user', 'guest')
ROLE_ALIASES: Dict[str, Role] = {
    "admin": Role.ADMIN,
    "operator": Role.OPERATOR,
    "viewer": Role.VIEWER,
    "user": Role.OPERATOR,   # Standard registered users have operator capabilities
    "guest": Role.VIEWER,    # Anonymous guests default to viewer
    "guest_user": Role.VIEWER,
}

# Minimum required role for executing specific tools
TOOL_PERMISSIONS: Dict[str, Role] = {
    "infra_calculation": Role.OPERATOR,
    "calculator": Role.OPERATOR,
    "code_architect": Role.VIEWER,
    "research": Role.VIEWER,
    "web_search": Role.VIEWER,
    "knowledge_retriever": Role.VIEWER,
}

def normalize_role(role_str: Optional[str]) -> Role:
    """Normalizes any role string into a canonical Role enum, defaulting to VIEWER."""
    if not role_str:
        return Role.VIEWER
    lowered = str(role_str).strip().lower()
    return ROLE_ALIASES.get(lowered, Role.VIEWER)

def has_role_permission(user_role: str, min_role: Role) -> bool:
    """
    Checks if a user's role satisfies the required minimum role level.
    """
    canonical_user = normalize_role(user_role)
    user_level = ROLE_HIERARCHY.get(canonical_user, 1)
    required_level = ROLE_HIERARCHY.get(min_role, 1)
    return user_level >= required_level

def can_execute_tool(user_role: str, tool_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validates whether the user's role allows executing the specified tool.
    Returns: (is_allowed: bool, rejection_reason: Optional[str])
    """
    required_role = TOOL_PERMISSIONS.get(tool_name, Role.VIEWER)
    if has_role_permission(user_role, required_role):
        return True, None

    reason = (
        f"Access Denied: Tool '{tool_name}' requires role '{required_role.value}' or higher. "
        f"Current role: '{normalize_role(user_role).value}'."
    )
    logger.warning(f"RBAC block: User with role '{user_role}' denied tool '{tool_name}'.")
    return False, reason

def require_role(min_role: Role):
    """
    FastAPI endpoint dependency to enforce minimum role authorization.
    Raises HTTP 403 Forbidden if user lacks necessary role level.
    """
    async def role_checker(user_role: str = Depends(get_current_user_role)) -> str:
        if not has_role_permission(user_role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: Action requires role '{min_role.value}' or higher. Current role: '{normalize_role(user_role).value}'."
            )
        return user_role

    return role_checker
