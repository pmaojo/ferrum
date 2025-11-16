import streamlit as st


def authentication_page() -> None:
    """Display authentication page."""
    st.header("🔐 Authentication")

    st.markdown(
        """
    Welcome to PermaGraph! This is a GraphRAG platform for building and querying knowledge graphs.

    To get started, please enter your API key below:
    """
    )

    # Simple API key authentication for demo
    api_key = st.text_input(
        "Enter API Key:", type="password", help="Enter your PermaGraph API key"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Login", use_container_width=True):
            if api_key:
                st.session_state.api_key = api_key
                st.session_state.is_authenticated = True
                st.success("Authentication successful!")
                st.rerun()
            else:
                st.error("Please enter an API key")

    with col2:
        if st.button("🔑 Use Demo Mode", use_container_width=True):
            st.session_state.api_key = "demo-key"
            st.session_state.is_authenticated = True
            st.success("Demo mode activated!")
            st.rerun()

    st.markdown("---")
    st.info(
        "💡 **Demo Mode**: Click 'Use Demo Mode' to explore the interface without an API key."
    )
