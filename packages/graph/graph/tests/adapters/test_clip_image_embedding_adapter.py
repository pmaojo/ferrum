import pytest
pytest.importorskip("PIL")
pytest.importorskip("torch")
from io import BytesIO
from PIL import Image
import torch

from adapters.llm.clip_image_embedding_adapter import CLIPImageEmbeddingAdapter


class DummyModel:
    def encode_image(self, tensor: torch.Tensor) -> torch.Tensor:
        batch, *_ = tensor.shape
        return torch.arange(batch * 3, dtype=torch.float32).reshape(batch, 3)


def dummy_preprocess(img: Image.Image) -> torch.Tensor:
    return torch.zeros(3, 224, 224)


@pytest.fixture
def adapter():
    model = DummyModel()
    return CLIPImageEmbeddingAdapter(model=model, preprocess=dummy_preprocess)


def test_embed_single_image_file(tmp_path, adapter):
    img_path = tmp_path / "img.png"
    Image.new("RGB", (10, 10), color="red").save(img_path)

    embedding = adapter.embed(images=img_path, tenant_id="t")

    assert embedding == [0.0, 1.0, 2.0]


def test_embed_single_image_bytes(adapter):
    img = Image.new("RGB", (8, 8))
    buf = BytesIO()
    img.save(buf, format="PNG")

    embedding = adapter.embed(images=buf.getvalue(), tenant_id="t")

    assert embedding == [0.0, 1.0, 2.0]


def test_embed_multiple_images(adapter):
    imgs = [Image.new("RGB", (5, 5)), Image.new("RGB", (5, 5))]

    embeddings = adapter.embed(images=imgs, tenant_id="t")

    assert embeddings == [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]
