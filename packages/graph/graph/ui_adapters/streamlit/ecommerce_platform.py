from datetime import datetime

import requests
import streamlit as st


class EcommercePlatformUI:
    def __init__(self):
        self.api_base_url = "http://0.0.0.0:5000/api/v1/ecommerce"

    def render(self):
        st.title("🛒 E-commerce & Advertising Platform")

        # Sidebar for configuration
        with st.sidebar:
            st.header("Configuration")
            tenant_id = st.text_input("Tenant ID", value="demo_tenant")
            customer_id = st.text_input("Customer ID", value="customer_123")

        # Main tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "📊 Customer Context",
                "🎯 Event Tracking",
                "💰 Bid Optimization",
                "📈 Analytics",
                "⚙️ Configuration",
            ]
        )

        with tab1:
            self._render_customer_context(tenant_id, customer_id)

        with tab2:
            self._render_event_tracking(tenant_id, customer_id)

        with tab3:
            self._render_bid_optimization(tenant_id)

        with tab4:
            self._render_analytics(tenant_id)

        with tab5:
            self._render_configuration()

    def _render_customer_context(self, tenant_id: str, customer_id: str):
        st.subheader("Customer Context")

        if st.button("🔍 Get Customer Context"):
            try:
                response = requests.get(
                    f"{self.api_base_url}/customer-context/{tenant_id}/{customer_id}"
                )
                if response.status_code == 200:
                    context = response.json()

                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric(
                            "Lifetime Value", f"${context.get('lifetime_value', 0):.2f}"
                        )
                        st.write("**Intent Signals:**")
                        for signal in context.get("intent_signals", []):
                            st.write(f"• {signal}")

                    with col2:
                        st.write("**Segment Memberships:**")
                        for segment in context.get("segment_memberships", []):
                            st.write(f"• {segment}")

                        st.write("**Predicted Interests:**")
                        for interest in context.get("predicted_interests", []):
                            st.write(f"• {interest}")

                    st.write("**Purchase History:**")
                    st.json(context.get("purchase_history", []))

                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

    def _render_event_tracking(self, tenant_id: str, customer_id: str):
        st.subheader("Event Tracking")

        event_type = st.selectbox(
            "Event Type",
            [
                "ecommerce.product.view",
                "ecommerce.cart.add",
                "ecommerce.purchase",
                "advertising.impression",
                "advertising.click",
                "advertising.conversion",
            ],
        )

        # Dynamic form based on event type
        event_data = {}

        if "product" in event_type:
            event_data["product_id"] = st.text_input("Product ID", value="product_456")
            event_data["product_category"] = st.text_input(
                "Category", value="electronics"
            )

            if "cart.add" in event_type:
                event_data["quantity"] = st.number_input("Quantity", value=1)
                event_data["price"] = st.number_input("Price", value=99.99)
            elif "purchase" in event_type:
                event_data["transaction_id"] = st.text_input(
                    "Transaction ID", value="txn_123"
                )
                event_data["total_value"] = st.number_input("Total Value", value=199.99)

        elif "advertising" in event_type:
            event_data["campaign_id"] = st.text_input(
                "Campaign ID", value="campaign_789"
            )
            event_data["creative_id"] = st.text_input(
                "Creative ID", value="creative_101"
            )

            if "conversion" in event_type:
                event_data["value"] = st.number_input("Conversion Value", value=50.0)
                event_data["conversion_type"] = st.selectbox(
                    "Type", ["purchase", "signup", "lead"]
                )

        if st.button("📤 Send Event"):
            try:
                payload = {
                    "tenant_id": tenant_id,
                    "customer_id": customer_id,
                    "event_type": event_type,
                    "event_data": event_data,
                }

                response = requests.post(
                    f"{self.api_base_url}/track-event", json=payload
                )

                if response.status_code == 200:
                    st.success("✅ Event tracked successfully!")
                    st.json(response.json())
                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Error tracking event: {str(e)}")

    def _render_bid_optimization(self, tenant_id: str):
        st.subheader("DSP Bid Optimization")

        # Mock bid request
        bid_request = {
            "id": f"bid_{int(datetime.now().timestamp())}",
            "user_id": "customer_123",
            "campaign_id": "campaign_789",
            "creative_assets": [
                {"keywords": ["electronics", "phone"], "category": "mobile"}
            ],
            "max_bid": 2.0,
            "timeout_ms": 100,
        }

        st.write("**Bid Request:**")
        st.json(bid_request)

        if st.button("🎯 Optimize Bid"):
            try:
                payload = {
                    "tenant_id": tenant_id,
                    "bid_request": bid_request,
                    "timeout_ms": 100,
                }

                response = requests.post(
                    f"{self.api_base_url}/optimize-bid", json=payload
                )

                if response.status_code == 200:
                    result = response.json()

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            "Recommended Bid", f"${result['recommended_bid']:.4f}"
                        )
                        st.metric(
                            "Creative Match", f"{result['creative_match_score']:.2%}"
                        )

                    with col2:
                        st.metric(
                            "Intent Alignment",
                            f"{result['intent_alignment_score']:.2%}",
                        )
                        st.metric("Predicted CTR", f"{result['predicted_ctr']:.2%}")

                    with col3:
                        st.metric(
                            "Predicted Conversion",
                            f"{result['predicted_conversion']:.2%}",
                        )
                        st.metric("Confidence", f"{result['confidence_score']:.2%}")

                    st.write(
                        f"**Processing Time:** {result['processing_time_ms']:.1f}ms"
                    )

                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Error optimizing bid: {str(e)}")

    def _render_analytics(self, tenant_id: str):
        st.subheader("Tenant Analytics")

        if st.button("📊 Get Analytics"):
            try:
                response = requests.get(f"{self.api_base_url}/analytics/{tenant_id}")

                if response.status_code == 200:
                    analytics = response.json()

                    st.write("**Interaction Analytics:**")
                    for interaction_type, count in analytics.get(
                        "analytics", {}
                    ).items():
                        st.metric(interaction_type.replace("_", " ").title(), count)

                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Error getting analytics: {str(e)}")

    def _render_configuration(self):
        st.subheader("Platform Configuration")

        # CDP Configuration
        st.write("**Customer Data Platform (CDP)**")
        cdp_provider = st.selectbox("CDP Provider", ["RudderStack", "Segment"])
        cdp_api_key = st.text_input("CDP API Key", type="password")

        # DSP Configuration
        st.write("**Demand Side Platform (DSP)**")
        dsp_provider = st.selectbox(
            "DSP Provider", ["Google DV360", "The Trade Desk", "Amazon DSP"]
        )
        dsp_endpoint = st.text_input(
            "DSP Endpoint", value="https://api.dsp-provider.com/bid"
        )

        # ML Models Configuration
        st.write("**ML Models**")
        ctr_model = st.selectbox(
            "CTR Model", ["XGBoost", "Neural Network", "Random Forest"]
        )
        conversion_model = st.selectbox(
            "Conversion Model", ["Logistic Regression", "Deep Learning", "Ensemble"]
        )

        if st.button("💾 Save Configuration"):
            config = {
                "cdp": {"provider": cdp_provider, "api_key": cdp_api_key},
                "dsp": {"provider": dsp_provider, "endpoint": dsp_endpoint},
                "ml_models": {"ctr": ctr_model, "conversion": conversion_model},
            }
            st.success("✅ Configuration saved!")
            st.json(config)


# Main function for Streamlit
def main():
    ecommerce_ui = EcommercePlatformUI()
    ecommerce_ui.render()


if __name__ == "__main__":
    main()
