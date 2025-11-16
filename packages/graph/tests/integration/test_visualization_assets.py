import pytest
from unittest.mock import Mock

from collections import namedtuple
import sys
import types

Community = namedtuple("Community", "id centroid_embedding node_ids size tenant_id")
Triple = namedtuple("Triple", "subject predicate object tenant_id")

# Provide stub domain.entities for GraphVisualizer import
stub_entities = types.ModuleType("domain.entities")
stub_entities.Triple = Triple
stub_entities.Community = Community
stub_entities.GraphStreamEvent = namedtuple(
    "GraphStreamEvent", "event_type data timestamp kg_id tenant_id"
)
stub_entities.GraphStreamEventType = types.SimpleNamespace(
    RENDER_COMPLETED=1, PATH_HIGHLIGHTED=2
)
sys.modules.setdefault("domain.entities", stub_entities)
from domain.graph_visualizer import GraphVisualizer


@pytest.fixture
def visualizer():
    clustering = Mock()
    clustering.compute_communities.return_value = [
        Community(
            id="kg:1",
            centroid_embedding=[0.0, 0.1],
            node_ids=["n1", "n2"],
            size=2,
            tenant_id="t",
        )
    ]
    clustering.get_community_subgraph.return_value = [
        Triple(subject="n1", predicate="rel", object="n2", tenant_id="t")
    ]
    return GraphVisualizer(clustering_port=clustering)


def test_asset_hook_metadata_included(visualizer):
    def hook(node_ids, community_id, tenant_id):
        return {
            node_ids[0]: {"image_thumbnail": "img.png"},
            node_ids[1]: {"audio_marker": "audio.wav"},
        }

    visualizer.register_asset_hook(hook)

    result = visualizer.render_community_detail(community_id="kg:1", tenant_id="t")
    node_map = {n["id"]: n for n in result["nodes"]}

    assert node_map["n1"]["assets"]["image_thumbnail"] == "img.png"
    assert node_map["n2"]["assets"]["audio_marker"] == "audio.wav"
