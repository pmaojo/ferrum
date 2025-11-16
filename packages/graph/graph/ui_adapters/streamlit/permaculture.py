from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from adapters.ontology.owl_ontology_loader import OwlOntologyLoader
from application.use_cases.ontology.load_official_ontology_use_case import (
    LoadOfficialOntologyRequestDTO,
)


def permaculture_interface():
    """Streamlit interface for permaculture garden planning."""

    st.header("🌱 Permaculture Garden Assistant")
    st.write("Plan your sustainable garden with plant compatibility analysis")

    # Initialize services
    owl_loader = OwlOntologyLoader()

    # Tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(
        ["🔄 Load Ontologies", "🌿 Plant Compatibility", "📋 Garden Plan"]
    )

    with tab1:
        st.subheader("Load Official Plant Ontologies")

        # Show available ontologies
        available_ontologies = owl_loader.list_available_ontologies()

        col1, col2 = st.columns([1, 1])

        with col1:
            st.write("**Available Official Ontologies:**")
            for name, info in available_ontologies.items():
                with st.expander(f"📚 {name.replace('_', ' ').title()}"):
                    st.write(f"**Description:** {info['description']}")
                    st.write(f"**Domain:** {info['domain']}")
                    st.code(f"URL: {info['url']}", language="text")

        with col2:
            st.write("**Load Ontology:**")
            selected_ontology = st.selectbox(
                "Choose an ontology to load:",
                list(available_ontologies.keys()),
                format_func=lambda x: x.replace("_", " ").title(),
            )

            merge_custom = st.checkbox(
                "Add custom permaculture compatibility rules",
                value=True,
                help="Enhance the official ontology with practical gardening rules",
            )

            force_refresh = st.checkbox(
                "Force refresh (bypass cache)",
                help="Download fresh copy even if cached version exists",
            )

            if st.button("🚀 Load Ontology", type="primary"):
                with st.spinner(f"Loading {selected_ontology}..."):
                    try:
                        _ = LoadOfficialOntologyRequestDTO(
                            tenant_id="demo-tenant",
                            ontology_name=selected_ontology,
                            merge_with_custom_rules=merge_custom,
                            force_refresh=force_refresh,
                        )

                        # This would use your actual use case in production
                        st.success(f"✅ Successfully loaded {selected_ontology}!")

                        # Show mock results
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Official Axioms", "1,247")
                        with col_b:
                            st.metric(
                                "Custom Rules Added", "156" if merge_custom else "0"
                            )
                        with col_c:
                            st.metric("Relationships", "23")

                        if merge_custom:
                            st.info(
                                "💡 Added permaculture-specific compatibility rules for "
                                "nitrogen cycling, allelopathy, and companion planting!"
                            )

                    except Exception as e:
                        st.error(f"❌ Failed to load ontology: {str(e)}")

    with tab2:
        st.subheader("🌿 Plant Compatibility Analysis")

        # Plant selection
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Primary Plant:**")
            plant1 = st.selectbox(
                "Select first plant:",
                [
                    "Tomato",
                    "Bean",
                    "Corn",
                    "Lettuce",
                    "Marigold",
                    "Basil",
                    "Clover",
                    "Walnut",
                ],
                key="plant1",
            )

            st.write("**Characteristics:**")
            plant1_traits = get_plant_traits(plant1)
            for trait, value in plant1_traits.items():
                st.write(f"• **{trait}:** {value}")

        with col2:
            st.write("**Companion Plant:**")
            plant2 = st.selectbox(
                "Select second plant:",
                [
                    "Tomato",
                    "Bean",
                    "Corn",
                    "Lettuce",
                    "Marigold",
                    "Basil",
                    "Clover",
                    "Walnut",
                ],
                key="plant2",
            )

            st.write("**Characteristics:**")
            plant2_traits = get_plant_traits(plant2)
            for trait, value in plant2_traits.items():
                st.write(f"• **{trait}:** {value}")

        # Compatibility analysis
        if plant1 != plant2:
            compatibility = analyze_compatibility(plant1, plant2)

            st.write("---")
            st.subheader("🔍 Compatibility Analysis")

            # Compatibility score
            score = compatibility["score"]
            color = "green" if score > 0.7 else "orange" if score > 0.4 else "red"
            st.markdown(f"**Compatibility Score:** :{color}[{score:.1%}]")

            # Detailed analysis
            col_a, col_b = st.columns(2)

            with col_a:
                st.write("**✅ Beneficial Interactions:**")
                for benefit in compatibility["benefits"]:
                    st.write(f"• {benefit}")

            with col_b:
                st.write("**⚠️ Potential Issues:**")
                for issue in compatibility["issues"]:
                    st.write(f"• {issue}")

            # Recommendations
            st.write("**💡 Recommendations:**")
            for rec in compatibility["recommendations"]:
                st.info(rec)

    with tab3:
        st.subheader("📋 Garden Layout Planner")

        st.write("Design your garden bed with optimal plant placement:")

        # Garden bed configuration
        col1, col2 = st.columns([1, 2])

        with col1:
            st.write("**Garden Bed Settings:**")
            bed_length = st.slider("Bed Length (feet)", 4, 20, 8)
            bed_width = st.slider("Bed Width (feet)", 3, 10, 4)

            st.write("**Selected Plants:**")
            available_plants = [
                "Tomato",
                "Bean",
                "Corn",
                "Lettuce",
                "Marigold",
                "Basil",
                "Clover",
            ]
            selected_plants = st.multiselect(
                "Choose plants for your garden:",
                available_plants,
                default=["Tomato", "Bean", "Marigold"],
            )

        with col2:
            st.write("**Optimized Layout:**")
            if selected_plants:
                layout_grid = generate_garden_layout(
                    selected_plants, bed_length, bed_width
                )

                # Create a simple grid visualization
                layout_df = pd.DataFrame(layout_grid)
                st.dataframe(
                    layout_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        str(i): st.column_config.TextColumn(width="small")
                        for i in range(len(layout_df.columns))
                    },
                )

                # Layout analysis
                st.write("**Layout Analysis:**")
                analysis = analyze_garden_layout(selected_plants)
                for point in analysis:
                    st.write(f"• {point}")
            else:
                st.info("Select plants to generate an optimized layout")


def get_plant_traits(plant: str) -> Dict[str, str]:
    """Get characteristics of a plant."""
    traits_db = {
        "Tomato": {
            "Nitrogen needs": "High consumer",
            "Growth pattern": "Vining, needs support",
            "Pest issues": "Hornworms, aphids",
            "Soil pH": "6.0-6.8",
        },
        "Bean": {
            "Nitrogen needs": "Nitrogen fixer",
            "Growth pattern": "Climbing or bush",
            "Pest issues": "Bean beetles",
            "Soil pH": "6.0-7.0",
        },
        "Corn": {
            "Nitrogen needs": "Heavy consumer",
            "Growth pattern": "Tall, provides structure",
            "Pest issues": "Corn borers",
            "Soil pH": "6.0-6.8",
        },
        "Lettuce": {
            "Nitrogen needs": "Moderate consumer",
            "Growth pattern": "Low growing, quick harvest",
            "Pest issues": "Aphids, slugs",
            "Soil pH": "6.0-7.0",
        },
        "Marigold": {
            "Nitrogen needs": "Low",
            "Growth pattern": "Compact flowering",
            "Pest issues": "Few (pest deterrent)",
            "Soil pH": "6.0-7.5",
        },
        "Basil": {
            "Nitrogen needs": "Moderate",
            "Growth pattern": "Bushy herb",
            "Pest issues": "Few (aromatic deterrent)",
            "Soil pH": "6.0-7.0",
        },
        "Clover": {
            "Nitrogen needs": "Nitrogen fixer",
            "Growth pattern": "Ground cover",
            "Pest issues": "Few",
            "Soil pH": "6.0-7.0",
        },
        "Walnut": {
            "Nitrogen needs": "Moderate",
            "Growth pattern": "Large tree",
            "Pest issues": "Allelopathic (inhibits others)",
            "Soil pH": "6.0-7.5",
        },
    }

    return traits_db.get(plant, {"Info": "No data available"})


def analyze_compatibility(plant1: str, plant2: str) -> Dict[str, Any]:
    """Analyze compatibility between two plants."""

    # Compatibility rules based on permaculture principles
    compatibility_rules = {
        ("Bean", "Tomato"): {
            "score": 0.9,
            "benefits": [
                "Bean fixes nitrogen for tomato's heavy needs",
                "Tomato provides structure for climbing beans",
                "Different root depths reduce competition",
            ],
            "issues": [],
            "recommendations": [
                "Plant beans 2-3 weeks before tomatoes",
                "Space adequately for air circulation",
            ],
        },
        ("Bean", "Corn"): {
            "score": 0.95,
            "benefits": [
                "Classic Three Sisters combination",
                "Bean fixes nitrogen for corn",
                "Corn provides natural trellis for beans",
            ],
            "issues": [],
            "recommendations": [
                "Add squash as ground cover for complete Three Sisters",
                "Plant corn first, then beans when corn is 6 inches tall",
            ],
        },
        ("Marigold", "Tomato"): {
            "score": 0.85,
            "benefits": [
                "Marigold deters tomato hornworms",
                "Attracts beneficial insects",
                "Different nutrient needs reduce competition",
            ],
            "issues": [],
            "recommendations": [
                "Plant marigolds around tomato bed perimeter",
                "Choose compact marigold varieties",
            ],
        },
        ("Walnut", "Tomato"): {
            "score": 0.1,
            "benefits": [],
            "issues": [
                "Walnut produces juglone, toxic to tomatoes",
                "Severe allelopathic inhibition",
                "Can kill or severely stunt tomato growth",
            ],
            "recommendations": [
                "Keep tomatoes at least 50 feet from walnut trees",
                "Consider raised beds with barriers",
                "Choose juglone-tolerant plants instead",
            ],
        },
    }

    # Check both directions
    pair = (plant1, plant2)
    reverse_pair = (plant2, plant1)

    if pair in compatibility_rules:
        return compatibility_rules[pair]
    elif reverse_pair in compatibility_rules:
        return compatibility_rules[reverse_pair]
    else:
        # Default neutral compatibility
        return {
            "score": 0.6,
            "benefits": ["No known negative interactions"],
            "issues": ["Limited research on this combination"],
            "recommendations": [
                "Monitor plants for competition",
                "Ensure adequate spacing",
                "Consider staggered planting times",
            ],
        }


def generate_garden_layout(
    plants: List[str], length: int, width: int
) -> List[List[str]]:
    """Generate an optimized garden layout."""

    # Simple layout algorithm (in production, this would use your ontology)
    grid_rows = max(2, width)
    grid_cols = max(2, length // 2)

    layout = [["" for _ in range(grid_cols)] for _ in range(grid_rows)]

    # Priority placement based on compatibility
    plant_priorities = {
        "Corn": 1,  # Tall, provides structure
        "Bean": 2,  # Climbs on corn
        "Clover": 3,  # Ground cover
        "Tomato": 4,  # Main crop
        "Marigold": 5,  # Pest deterrent, border
        "Basil": 6,  # Aromatic deterrent
        "Lettuce": 7,  # Quick growing, fill gaps
    }

    sorted_plants = sorted(plants, key=lambda p: plant_priorities.get(p, 10))

    # Place plants strategically
    plant_idx = 0
    for row in range(grid_rows):
        for col in range(grid_cols):
            if plant_idx < len(sorted_plants):
                layout[row][col] = sorted_plants[plant_idx % len(sorted_plants)]
                plant_idx += 1

    return layout


def analyze_garden_layout(plants: List[str]) -> List[str]:
    """Analyze the garden layout for potential issues and benefits."""
    analysis = []

    # Check for beneficial combinations
    if "Bean" in plants and "Tomato" in plants:
        analysis.append("✅ Bean-Tomato partnership: Nitrogen fixation benefit")

    if "Bean" in plants and "Corn" in plants:
        analysis.append("✅ Bean-Corn partnership: Natural trellis system")

    if "Marigold" in plants:
        analysis.append("✅ Marigold inclusion: Natural pest deterrent")

    if "Clover" in plants:
        analysis.append("✅ Clover ground cover: Soil protection and nitrogen fixation")

    # Check for potential issues
    if "Walnut" in plants and any(p in plants for p in ["Tomato", "Bean", "Corn"]):
        analysis.append("⚠️ Walnut proximity: Risk of allelopathic inhibition")

    # General recommendations
    analysis.append("💡 Consider succession planting for continuous harvest")
    analysis.append("💡 Add mulch pathways between plantings")
    analysis.append("💡 Include flowers to attract pollinators")

    return analysis


def show_permaculture_ontology_demo():
    """Demo for permaculture ontology features."""
    st.header("🌱 Permaculture Knowledge Assistant")

    # Official ontology selection
    st.subheader("📚 Load Official Plant Ontologies")

    ontology_options = {
        "plant_ontology": "Plant Ontology (PO) - Plant anatomy and development stages",
        "crop_ontology": "Crop Ontology (CO) - Agricultural traits and phenotypes",
        "agrovoc": "AGROVOC - FAO's multilingual agricultural vocabulary",
        "peco": "Plant Experimental Conditions Ontology",
    }

    col1, col2 = st.columns(2)

    with col1:
        selected_ontologies = st.multiselect(
            "Select ontologies to load:",
            options=list(ontology_options.keys()),
            default=["plant_ontology", "agrovoc"],
            format_func=lambda x: ontology_options[x],
        )

        merge_custom = st.checkbox(
            "Merge with permaculture compatibility rules",
            value=True,
            help="Add practical gardening knowledge to official ontologies",
        )

    with col2:
        st.info(
            "**Official Ontology Sources:**\n\n"
            "• **Plant Ontology**: http://purl.obolibrary.org/obo/po.owl\n"
            "• **Crop Ontology**: http://www.cropontology.org/\n"
            "• **AGROVOC**: https://agrovoc.fao.org/\n"
            "• **PECO**: Plant experimental conditions"
        )

    if st.button("🚀 Load Selected Ontologies", type="primary"):
        if not selected_ontologies:
            st.error("Please select at least one ontology to load")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()

        results = {}
        for i, ontology_name in enumerate(selected_ontologies):
            status_text.text(f"Loading {ontology_name}...")
            progress_bar.progress((i + 1) / len(selected_ontologies))

            try:
                # Simulate loading with the actual use case
                import time

                time.sleep(1)  # Simulate network delay

                # Mock results - in production this would use LoadOfficialOntologyUseCase
                results[ontology_name] = {
                    "official_axioms": 1247 + i * 100,
                    "custom_rules": 156 if merge_custom else 0,
                    "total_axioms": (1247 + i * 100) + (156 if merge_custom else 0),
                    "relationships": 89 + i * 20,
                    "status": "success",
                }

            except Exception as e:
                results[ontology_name] = {"status": "error", "error": str(e)}

        status_text.text("✅ Loading complete!")

        # Display results
        st.subheader("📊 Loading Results")

        for ontology_name, result in results.items():
            with st.expander(f"🌿 {ontology_options[ontology_name]}", expanded=True):
                if result["status"] == "success":
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("Official Axioms", f"{result['official_axioms']:,}")
                    with col_b:
                        st.metric("Custom Rules", f"{result['custom_rules']:,}")
                    with col_c:
                        st.metric("Total Axioms", f"{result['total_axioms']:,}")
                    with col_d:
                        st.metric("Relationships", f"{result['relationships']:,}")

                    st.success(f"✅ Successfully loaded {ontology_name}")
                else:
                    st.error(f"❌ Failed to load {ontology_name}: {result['error']}")

    # Demonstrate compatibility logic
    st.subheader("🤝 Plant Compatibility Analysis")

    col1, col2 = st.columns(2)

    with col1:
        plant1 = st.selectbox(
            "First plant:",
            ["Tomato", "Basil", "Beans", "Corn", "Marigold", "Nasturtium"],
        )

    with col2:
        plant2 = st.selectbox(
            "Second plant:",
            ["Tomato", "Basil", "Beans", "Corn", "Marigold", "Nasturtium"],
        )

    if st.button("🔍 Analyze Compatibility"):
        if plant1 == plant2:
            st.warning("Please select two different plants")
        else:
            # Demo compatibility analysis using ontology rules
            compatibility_demo(plant1, plant2)


def compatibility_demo(plant1: str, plant2: str):
    """Demo plant compatibility analysis."""

    # Mock compatibility rules based on permaculture knowledge
    compatibility_rules = {
        ("Tomato", "Basil"): {
            "compatible": True,
            "reason": "Basil repels tomato hornworms and improves tomato flavor",
            "ontology_rule": "repels_pest(basil, tomato_hornworm) AND improves_flavor(basil, tomato)",
        },
        ("Beans", "Corn"): {
            "compatible": True,
            "reason": "Beans fix nitrogen that corn needs, corn provides support for beans",
            "ontology_rule": "fixes_nitrogen(beans) AND requires_nitrogen(corn) AND provides_support(corn, beans)",
        },
        ("Tomato", "Beans"): {
            "compatible": False,
            "reason": "Beans can stunt tomato growth due to allelopathy",
            "ontology_rule": "allelopathic_inhibition(beans, tomato)",
        },
    }

    key = (plant1, plant2)
    reverse_key = (plant2, plant1)

    if key in compatibility_rules:
        rule = compatibility_rules[key]
    elif reverse_key in compatibility_rules:
        rule = compatibility_rules[reverse_key]
    else:
        rule = {
            "compatible": None,
            "reason": "Compatibility data not available in loaded ontologies",
            "ontology_rule": "unknown_relationship(?plant1, ?plant2)",
        }

    if rule["compatible"] is True:
        st.success(f"✅ **{plant1}** and **{plant2}** are compatible!")
        st.info(f"**Reason:** {rule['reason']}")
        st.code(f"Ontology Rule: {rule['ontology_rule']}", language="prolog")
    elif rule["compatible"] is False:
        st.error(f"❌ **{plant1}** and **{plant2}** are NOT compatible!")
        st.warning(f"**Reason:** {rule['reason']}")
        st.code(f"Ontology Rule: {rule['ontology_rule']}", language="prolog")
    else:
        st.info(f"🤷 Compatibility between **{plant1}** and **{plant2}** is unknown")
        st.help("Try loading more ontologies or adding custom compatibility rules")
