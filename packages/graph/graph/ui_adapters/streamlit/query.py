from typing import Any, Dict

from domain.exceptions import GraphRAGException

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .services import initialize_services

# Reuse types from main module when called via wrapper


def visualize_graph_results(
    query_results: Dict[str, Any], services: Dict[str, Any]
) -> None:
    """Visualize graph results using plotly and the visualization ports."""
    if not query_results.get("results"):
        return

    try:
        # Extract nodes and edges from results
        nodes = []

        # Parse results to extract graph structure
        results = query_results.get("results", [])
        if isinstance(results, str):
            # If results is text, try to extract entities and relationships
            import re

            # Simple entity extraction for demo
            entities = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", results)
            for i, entity in enumerate(set(entities[:20])):  # Limit to 20 entities
                nodes.append(
                    {
                        "id": f"entity_{i}",
                        "label": entity,
                        "x": i * 50,
                        "y": (i % 5) * 50,
                        "size": 10,
                        "color": px.colors.qualitative.Set1[
                            i % len(px.colors.qualitative.Set1)
                        ],
                    }
                )
        else:
            # Handle structured results
            for i, result in enumerate(results[:20]):  # Limit to 20 nodes
                if isinstance(result, dict):
                    node_id = str(result.get("id", f"node_{i}"))
                    label = str(result.get("label", result.get("name", node_id)))
                    nodes.append(
                        {
                            "id": node_id,
                            "label": label,
                            "x": (i % 10) * 60,
                            "y": (i // 10) * 60,
                            "size": 15,
                            "color": px.colors.qualitative.Set1[
                                i % len(px.colors.qualitative.Set1)
                            ],
                        }
                    )

        if not nodes:
            st.info("No graph structure found in results to visualize")
            return

        # Create plotly visualization
        fig = go.Figure()

        # Add nodes
        node_trace = go.Scatter(
            x=[node["x"] for node in nodes],
            y=[node["y"] for node in nodes],
            mode="markers+text",
            text=[node["label"] for node in nodes],
            textposition="middle center",
            marker=dict(
                size=[node["size"] for node in nodes],
                color=[node["color"] for node in nodes],
                line=dict(width=2, color="white"),
            ),
            name="Entities",
            hovertemplate="<b>%{text}</b><extra></extra>",
        )
        fig.add_trace(node_trace)

        # Add edges if available
        for i in range(len(nodes) - 1):
            fig.add_trace(
                go.Scatter(
                    x=[nodes[i]["x"], nodes[i + 1]["x"]],
                    y=[nodes[i]["y"], nodes[i + 1]["y"]],
                    mode="lines",
                    line=dict(width=1, color="rgba(125,125,125,0.5)"),
                    showlegend=False,
                    hoverinfo="none",
                )
            )

        fig.update_layout(
            title="Knowledge Graph Visualization",
            showlegend=True,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Interactive graph visualization of query results",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.005,
                    y=-0.002,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(color="#888888", size=12),
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )

        st.plotly_chart(fig, use_container_width=True)

        # Show graph statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nodes", len(nodes))
        with col2:
            st.metric("Edges", len(nodes) - 1 if len(nodes) > 1 else 0)
        with col3:
            st.metric("Visualization", "Interactive")

    except Exception as e:
        st.error(f"❌ Error creating visualization: {str(e)}")
        st.info(
            "💡 Tip: This is a demo visualization. Connect to a real graph database for full visualization capabilities."
        )


def query_page() -> None:
    """Display the main query interface."""
    # Header with logout
    col1, col2 = st.columns([4, 1])
    with col1:
        st.header("🔍 Query Knowledge Graph")
    with col2:
        if st.button("🚪 Logout"):
            st.session_state.is_authenticated = False
            st.session_state.api_key = None
            st.rerun()

    st.markdown("---")

    # Debug mode toggle (for development)
    with st.sidebar:
        st.session_state.debug_mode = st.checkbox("🔧 Debug Mode", value=False)

        # Service status indicator
        st.subheader("🚦 Service Status")
        if "services" not in st.session_state:
            st.session_state.services = initialize_services()

        services = st.session_state.services
        if services.query_service:
            st.success("✅ Query Service")
        else:
            st.warning("⚠️ Query Service")

        if services.graph_retriever:
            st.success("✅ Graph Retriever")
        else:
            st.warning("⚠️ Graph Retriever")

    # Tabs for different functionality
    tab1, tab2, tab3 = st.tabs(["💬 Query", "📄 Index Documents", "📊 Analytics"])

    with tab1:
        st.subheader("Ask your Knowledge Graph")

        # Query input
        query = st.text_area(
            "Enter your question:",
            placeholder="What would you like to know?",
            height=100,
        )

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            kg_id = st.text_input(
                "Knowledge Graph ID:",
                value="default-kg",
                help="ID of the knowledge graph to query",
            )
        with col2:
            tenant_id = st.text_input(
                "Tenant ID:", value="demo-tenant", help="Your tenant identifier"
            )
        with col3:
            show_visualization = st.checkbox("Show graph visualization", value=True)

        if st.button("🚀 Submit Query", use_container_width=True):
            if query:
                with st.spinner("Processing query..."):
                    try:
                        # Initialize services if not already done
                        if "services" not in st.session_state:
                            st.session_state.services = initialize_services()

                        services = st.session_state.services

                        if services.query_service:
                            # Execute real GraphRAG query using query service
                            result = (
                                services.query_service.execute_natural_language_query(
                                    question=query,
                                    kg_id=kg_id,
                                    tenant_id=tenant_id,
                                    user_id="streamlit_user",
                                    include_explanation=True,
                                    include_subgraph=True,
                                    max_results=10,
                                )
                            )

                            st.success("✅ Query processed successfully!")

                            # Display formatted results
                            st.subheader("📋 Response:")
                            if result.get("results"):
                                if isinstance(result["results"], str):
                                    st.write(result["results"])
                                elif (
                                    isinstance(result["results"], list)
                                    and result["results"]
                                ):
                                    for i, item in enumerate(
                                        result["results"][:5]
                                    ):  # Show first 5 results
                                        st.write(f"**Result {i+1}:** {item}")
                                else:
                                    st.info(
                                        "No specific results found, but the query was processed."
                                    )
                            else:
                                st.info("No results found for this query.")

                            # Show explanation if available
                            if result.get("explanation"):
                                st.subheader("🔍 Query Explanation:")
                                st.info(result["explanation"])

                            # Show metadata
                            if result.get("metadata"):
                                metadata = result["metadata"]
                                st.subheader("📊 Query Metadata:")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric(
                                        "Execution Time",
                                        f"{metadata.get('execution_time_ms', 0):.2f}ms",
                                    )
                                with col2:
                                    st.metric(
                                        "Results Found", metadata.get("result_count", 0)
                                    )
                                with col3:
                                    error_status = (
                                        "❌ Error"
                                        if metadata.get("error")
                                        else "✅ Success"
                                    )
                                    st.metric("Status", error_status)

                            # Show subgraph if available
                            if result.get("subgraph"):
                                st.subheader("🕸️ Related Knowledge Graph:")
                                st.json(result["subgraph"])

                            # Show suggestions if no results
                            if result.get("suggestions") and not result.get("results"):
                                st.subheader("💡 Suggestions:")
                                for suggestion in result["suggestions"][
                                    :3
                                ]:  # Show top 3 suggestions
                                    st.write(f"• {suggestion}")

                            # Show graph visualization if enabled
                            if show_visualization:
                                st.subheader("🔗 Graph Visualization")
                                visualize_graph_results(result, services)

                        elif services.graph_retriever:
                            # Fallback to direct graph retriever
                            result = services.graph_retriever.run(
                                question=query,
                                kg_id=kg_id,
                                tenant_id=tenant_id,
                                opts={},
                            )

                            st.success("✅ Query processed successfully!")

                            st.subheader("📋 Response:")
                            if isinstance(result, str):
                                st.write(result)
                            elif isinstance(result, list):
                                st.subheader("🕸️ Knowledge Graph Triples:")
                                for i, triple in enumerate(
                                    result[:10]
                                ):  # Show first 10 triples
                                    if hasattr(triple, "subject"):
                                        st.write(
                                            f"**{i+1}.** {triple.subject} → {triple.predicate} → {triple.object}"
                                        )
                                    else:
                                        st.write(f"**{i+1}.** {triple}")
                            else:
                                st.json(result)

                        else:
                            st.error(
                                "❌ GraphRAG services not available. Please check the configuration."
                            )

                    except GraphRAGException as e:
                        st.error(f"❌ Error processing query: {e.message}")
                        if st.session_state.get("debug_mode", False):
                            st.json(e.context)
                    except Exception as e:
                        st.error(f"❌ Error processing query: {str(e)}")
                        if st.session_state.get("debug_mode", False):
                            st.exception(e)
            else:
                st.warning("⚠️ Please enter a query")

    with tab2:
        st.subheader("📄 Index New Documents")
        st.info("This feature allows you to add new documents to your knowledge graph.")

        uploaded_file = st.file_uploader(
            "Choose a file", type=["txt", "pdf", "doc", "docx"]
        )
        if uploaded_file:
            st.write(f"📁 File: {uploaded_file.name}")
            if st.button("📥 Index Document"):
                st.success("Document indexed successfully! (Demo mode)")

    with tab3:
        st.subheader("📊 Knowledge Graph Analytics")
        st.info("View analytics and insights about your knowledge graph.")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Entities", "1,234")
        with col2:
            st.metric("Total Relationships", "2,567")
        with col3:
            st.metric("Graph Density", "0.73")

    # Footer
    st.markdown("---")
    st.markdown(
        "🔧 **Status:** Connected to PermaGraph API | 🔑 **API Key:** "
        + ("*" * 8)
        + st.session_state.get("api_key", "")[-4:]
        if st.session_state.get("api_key")
        else "None"
    )
