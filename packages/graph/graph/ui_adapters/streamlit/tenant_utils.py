from typing import Any, Dict, Optional

import streamlit as st


def get_tenant_context() -> Optional[Dict[str, Any]]:
    """Get current user's tenant context from session state."""
    if "user_context" in st.session_state:
        user_context = st.session_state.user_context
        return {
            "tenant_id": user_context.get("tenant_id")
            or user_context.get("organization_id"),
            "user_id": user_context.get("user_id"),
            "username": user_context.get("username"),
            "role": user_context.get("role", "viewer"),
        }
    return None


def check_replit_auth() -> Optional[Dict[str, Any]]:
    """Check for Replit authentication headers and extract user info."""
    # In Streamlit, we can check for query params that might contain auth info
    query_params = st.query_params

    # Check if we have Replit user info in query params (for demo)
    if "replit_user" in query_params:
        username = query_params.get("replit_user", "demo-user")
        return {
            "user_id": f"replit-{username}",
            "username": username,
            "tenant_id": f"replit-org-{username}",
            "organization_id": f"replit-org-{username}",
            "role": "admin",
        }

    # In production, this would extract from actual Replit headers
    return {
        "user_id": "replit-demo-user",
        "username": "demo-user",
        "tenant_id": "replit-org-demo",
        "organization_id": "replit-org-demo",
        "role": "admin",
    }


def get_replit_auth_script() -> str:
    """Generate Replit Auth script for authentication."""
    return """
    <script>
        // Simulate Replit auth for demo
        if (!window.location.search.includes('replit_user')) {
            const username = prompt('Enter your username for demo:') || 'demo-user';
            const url = new URL(window.location);
            url.searchParams.set('replit_user', username);
            window.location.href = url.toString();
        }
    </script>
    """
