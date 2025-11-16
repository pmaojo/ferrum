import os
import traceback

import streamlit as st


def indexing_interface(
    api_key: str,
    model_type: str,
    kg_id: str,
    tenant_id: str,
    graphrag_engine: str,
    falkordb_host: str = "127.0.0.1",
    falkordb_port: int = 6379,
    falkordb_username: str = "",
    falkordb_password: str = "",
):
    """Indexing interface for documents."""
    st.header("📊 Index Documents")

    # File upload
    uploaded_files = st.file_uploader(
        "Upload documents to index",
        accept_multiple_files=True,
        type=["txt", "pdf", "docx", "md"],
    )

    # Text input
    document_text = st.text_area(
        "Or enter text directly:",
        placeholder="Enter document content here...",
        height=200,
    )

    if st.button("🔄 Index Documents", type="primary"):
        if not api_key:
            st.error("Please provide an API key in the sidebar.")
            return

        if not uploaded_files and not document_text.strip():
            st.warning("Please upload files or enter text to index.")
            return

        with st.spinner("Indexing documents..."):
            try:
                from adapters.retrievers.falkordb_graphrag_sdk_adapter import (
                    FalkorDBGraphRAGAdapter,
                )

                # Set environment variable for API key
                if model_type.startswith("gemini/"):
                    os.environ["GEMINI_API_KEY"] = api_key
                elif model_type.startswith("openai/"):
                    os.environ["OPENAI_API_KEY"] = api_key

                adapter = FalkorDBGraphRAGAdapter(
                    host=falkordb_host,
                    port=falkordb_port,
                    username=falkordb_username if falkordb_username else None,
                    password=falkordb_password if falkordb_password else None,
                )

                # Process uploaded files
                documents = []
                if uploaded_files:
                    for file in uploaded_files:
                        content = file.read().decode("utf-8")
                        documents.append(
                            {"content": content, "metadata": {"filename": file.name}}
                        )

                # Process text input
                if document_text.strip():
                    documents.append(
                        {
                            "content": document_text,
                            "metadata": {"source": "manual_input"},
                        }
                    )

                # Index documents
                result = adapter.index_documents(
                    documents=documents, kg_id=kg_id, tenant_id=tenant_id
                )

                if result.success:
                    st.success(f"✅ Successfully indexed {len(documents)} documents!")
                    st.info(f"Knowledge graph '{kg_id}' has been updated.")
                else:
                    st.error(
                        f"❌ Indexing failed: {getattr(result, 'error_message', 'Unknown error')}"
                    )

            except Exception as e:
                st.error(f"❌ Error during indexing: {str(e)}")
                with st.expander("Error Details"):
                    st.text(traceback.format_exc())
