"""Streamlit demo page for unified agent coordination."""

from datetime import datetime
from typing import Any, Dict

import streamlit as st

from domain.unified_agent_coordinator import (
    AgentSystemType,
    CoordinationStrategy,
    UnifiedAgentCoordinator,
    UnifiedAgentRequest,
)


def unified_agent_demo_page(coordinator: UnifiedAgentCoordinator):
    """Display unified agent coordination demo page."""

    st.title("🤖 Unified Agent Coordination System")
    st.markdown(
        "Coordinate queries across multiple agent systems with fallback strategies."
    )

    # Configuration section
    with st.expander("⚙️ Configuration", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            primary_system = st.selectbox(
                "Primary Agent System",
                options=[system.value for system in AgentSystemType],
                index=0,
                help="The primary agent system to try first",
            )

            coordination_strategy = st.selectbox(
                "Coordination Strategy",
                options=[strategy.value for strategy in CoordinationStrategy],
                index=0,
                help="How multiple agent systems should coordinate",
            )

        with col2:
            fallback_systems = st.multiselect(
                "Fallback Systems",
                options=[
                    system.value
                    for system in AgentSystemType
                    if system.value != primary_system
                ],
                default=[],
                help="Systems to try if primary system fails",
            )

            timeout_seconds = st.slider(
                "Timeout (seconds)",
                min_value=30,
                max_value=300,
                value=120,
                help="Maximum time to wait for response",
            )

    # Query section
    with st.expander("📝 Query Configuration", expanded=True):
        query_text = st.text_area(
            "Enter your query:",
            height=100,
            placeholder="Ask a question that can be processed by multiple agent systems...",
        )

        col1, col2 = st.columns(2)
        with col1:
            kg_id = st.text_input("Knowledge Graph ID", value="default")
            tenant_id = st.text_input("Tenant ID", value="demo_tenant")

        with col2:
            user_id = st.text_input("User ID", value="demo_user")
            workflow_id = st.text_input(
                "Workflow ID",
                value=f"unified_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            )

    # Document upload for StructRAG
    with st.expander("📄 Documents (for StructRAG)", expanded=False):
        uploaded_files = st.file_uploader(
            "Upload documents",
            accept_multiple_files=True,
            type=["txt", "md", "pdf"],
            help="Documents to process with StructRAG system",
        )

        documents = []
        if uploaded_files:
            for file in uploaded_files:
                content = file.read().decode("utf-8")
                documents.append(content)
                st.success(f"Loaded: {file.name}")

    # Execute button
    if st.button("🚀 Execute Unified Coordination", type="primary"):
        if not query_text:
            st.error("Please enter a query")
            return

        # Create unified request
        request = UnifiedAgentRequest(
            system_type=AgentSystemType(primary_system),
            operation=(
                "process_query" if primary_system == "structrag" else "coordinate_query"
            ),
            parameters={
                "query": query_text,
                "kg_id": kg_id,
                "documents": documents,
                "opts": {},
            },
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            user_id=user_id,
            timeout_seconds=timeout_seconds,
        )

        # Execute coordination
        with st.spinner("Coordinating across agent systems..."):
            try:
                session_id = coordinator.coordinate_unified_workflow(
                    workflow_type="unified_query",
                    primary_system=AgentSystemType(primary_system),
                    fallback_systems=[AgentSystemType(sys) for sys in fallback_systems],
                    request=request,
                    coordination_strategy=CoordinationStrategy(coordination_strategy),
                )

                st.success(f"✅ Coordination completed! Session ID: {session_id}")

                # Display session status
                status = coordinator.get_session_status(session_id)
                display_coordination_results(
                    status, coordinator.active_sessions[session_id]
                )

            except Exception as e:
                st.error(f"❌ Coordination failed: {str(e)}")


def display_coordination_results(status: Dict[str, Any], session_data: Dict[str, Any]):
    """Display coordination results and session information."""

    st.subheader("📊 Coordination Results")

    # Status overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Status",
            (
                status["status"].value
                if hasattr(status["status"], "value")
                else status["status"]
            ),
        )
    with col2:
        st.metric("Active System", status.get("active_system", "N/A"))
    with col3:
        st.metric("Responses", status["responses_count"])
    with col4:
        duration = datetime.now() - datetime.fromisoformat(status["created_at"])
        st.metric("Duration", f"{duration.total_seconds():.1f}s")

    # Response details
    if "responses" in session_data:
        st.subheader("🔍 Individual System Responses")

        for system_name, response in session_data["responses"].items():
            with st.expander(f"📋 {system_name.upper()} Response"):
                col1, col2 = st.columns([1, 3])

                with col1:
                    success_icon = "✅" if response.success else "❌"
                    st.write(
                        f"**Status:** {success_icon} {'Success' if response.success else 'Failed'}"
                    )
                    st.write(
                        f"**Processing Time:** {response.processing_time_ms:.1f}ms"
                    )

                    if response.metadata:
                        st.write("**Metadata:**")
                        st.json(response.metadata)

                with col2:
                    if response.success:
                        st.write("**Result:**")
                        st.json(response.result)
                    else:
                        st.error(f"**Error:** {response.error_message}")

    # Primary or synthesized response
    if "primary_response" in session_data:
        st.subheader("🎯 Primary Response")
        response = session_data["primary_response"]
        if response.success and "answer" in response.result:
            st.success("**Answer:**")
            st.write(response.result["answer"])
        else:
            st.json(response.result)

    elif "synthesized_response" in session_data:
        st.subheader("🔄 Synthesized Response")
        response = session_data["synthesized_response"]
        st.info(f"**Consensus Score:** {response.result.get('consensus_score', 0):.2f}")
        st.json(response.result)

    # Session timeline
    with st.expander("⏱️ Session Timeline"):
        st.json(
            {
                "session_id": status["session_id"],
                "workflow_type": status["workflow_type"],
                "created_at": status["created_at"],
                "coordination_strategy": session_data.get(
                    "coordination_strategy", "unknown"
                ),
                "systems_attempted": list(session_data.get("responses", {}).keys()),
            }
        )
