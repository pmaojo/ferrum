import streamlit as st

from ui_adapters.streamlit.indexing import indexing_interface
from ui_adapters.streamlit.permaculture import permaculture_interface
from ui_adapters.streamlit.query import query_page as _query_page


def check_replit_auth():
    """Check for Replit authentication - simplified version."""
    return None


def get_replit_auth_script():
    """Get Replit auth script - simplified version."""
    return ""


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="PermaGraph - Enterprise GraphRAG Platform",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Check for Replit authentication
    replit_user = check_replit_auth()
    if replit_user:
        st.session_state.user_context = replit_user
        st.success(
            f"👋 Welcome {replit_user['username']}! You're authenticated via Replit."
        )
    else:
        st.info("🔐 Please authenticate with Replit to access the full platform.")
        st.markdown(get_replit_auth_script(), unsafe_allow_html=True)
        return

    st.sidebar.title("🧠 PermaGraph")

    # Navigation
    page = st.sidebar.selectbox(
        "Navigate",
        ["🔍 Query", "📊 Indexing", "🌱 Permaculture", "📈 Analytics", "🔧 Settings"],
    )

    if page == "🔍 Query":
        _query_page()
    elif page == "📊 Indexing":
        indexing_interface()

    elif page == "🌱 Permaculture":
        permaculture_interface()
    elif page == "📈 Analytics":
        st.info("Analytics page coming soon!")
    elif page == "🔧 Settings":
        st.info("Settings page coming soon!")


if __name__ == "__main__":
    main()
