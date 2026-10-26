import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from core import setup
from core.setup import (
    MANUAL_MODEL_OPTION,
    VENDORS,
    infer_provider,
    list_models,
    run_setup_guide,
    write_settings_atomically,
)


class FakeModel:
    """模拟单个模型对象。"""

    def __init__(self, model_id: str) -> None:
        self.id = model_id


class FakeListResponse:
    """模拟 /models 接口的响应。"""

    def __init__(self, model_ids: list[str]) -> None:
        self.data = [FakeModel(model_id) for model_id in model_ids]


class FakeOpenAIClient:
    """模拟 OpenAI 客户端，可配置抛错。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float,
        model_ids: list[str] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.model_ids = model_ids

    @property
    def models(self) -> "FakeOpenAIClient":
        return self

    def list(self) -> FakeListResponse:
        if self.model_ids is None:
            raise RuntimeError("模型列表拉取失败")
        return FakeListResponse(self.model_ids)


def test_vendors_include_manual_config() -> None:
    """测试预设厂商中包含手动配置入口。"""

    names = [vendor.name for vendor in VENDORS]

    assert "Gemini" in names
    assert (
        next(vendor for vendor in VENDORS if vendor.name == "Gemini").base_url
        == "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    assert "Manual" in names
    assert next(vendor for vendor in VENDORS if vendor.name == "Manual").base_url == ""


def test_infer_provider_matches_base_url() -> None:
    """测试根据 base_url 推断厂商名。"""

    assert infer_provider("https://api.deepseek.com/") == "deepseek"
    assert (
        infer_provider("https://generativelanguage.googleapis.com/v1beta/openai/")
        == "gemini"
    )
    assert (
        infer_provider("https://dashscope.aliyuncs.com/compatible-mode/v1")
        == "alibaba"
    )
    assert infer_provider("https://api.siliconflow.cn/v1") == "siliconflow"
    assert infer_provider("https://example.com/v1") == ""


def test_list_models_returns_model_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试 /models 接口成功时返回模型 ID 列表。"""

    monkeypatch.setattr(
        setup,
        "OpenAI",
        lambda api_key, base_url, timeout: FakeOpenAIClient(
            api_key, base_url, timeout, ["model-a", "model-b"]
        ),
    )

    assert list_models("https://example.com", "key") == ["model-a", "model-b"]


def test_list_models_returns_none_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试 /models 接口失败时返回 None 而不是抛错。"""

    monkeypatch.setattr(
        setup,
        "OpenAI",
        lambda api_key, base_url, timeout: FakeOpenAIClient(api_key, base_url, timeout),
    )

    assert list_models("https://example.com", "key") is None


def test_list_gemini_models_uses_native_api_with_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gemini 型号从原生 API 动态分页获取，并过滤不支持生成的模型。"""

    pages = [
        {
            "models": [
                {
                    "name": "models/gemini-current-flash",
                    "supportedGenerationMethods": ["generateContent"],
                },
                {
                    "name": "models/text-embedding-latest",
                    "supportedGenerationMethods": ["embedContent"],
                },
            ],
            "nextPageToken": "page-2",
        },
        {
            "models": [
                {
                    "name": "models/gemini-current-pro",
                    "supportedGenerationMethods": ["generateContent"],
                }
            ]
        },
    ]
    requests = []

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self.payload = payload

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode()

    def fake_urlopen(request, timeout: float):
        requests.append((request, timeout))
        return FakeResponse(pages[len(requests) - 1])

    monkeypatch.setattr(setup, "urlopen", fake_urlopen)

    models = list_models(
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-key",
        timeout=7,
    )

    assert models == [
        "gemini-current-flash",
        "gemini-current-pro",
    ]
    assert "gemini-3.8-flash" not in models
    assert len(requests) == 2
    assert requests[0][0].get_header("X-goog-api-key") == "gemini-key"
    assert requests[0][1] == 7
    assert parse_qs(urlparse(requests[1][0].full_url).query)["pageToken"] == [
        "page-2"
    ]


@pytest.mark.asyncio
async def test_pick_model_allows_manual_id_when_list_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API 返回目录时仍能手动选择尚未出现在目录中的模型 ID。"""

    async def fake_pick_single(title: str, items: list[str]) -> str:
        assert items == ["gemini-2.5-flash", MANUAL_MODEL_OPTION]
        return MANUAL_MODEL_OPTION

    async def fake_prompt_text(prompt_text: str) -> str:
        assert prompt_text == "Model name: "
        return "gemini-3.8-flash"

    monkeypatch.setattr(setup, "_pick_single", fake_pick_single)
    monkeypatch.setattr(setup, "_prompt_text", fake_prompt_text)

    assert await setup._pick_model(["gemini-2.5-flash"]) == "gemini-3.8-flash"


def test_write_settings_atomically_writes_complete_config(tmp_path: Path) -> None:
    """测试配置以原子方式写入，且不残留临时文件。"""

    target = tmp_path / "settings.json"
    data = {"model": {"base_url": "https://example.com", "api_key": "key", "model_name": "m"}}

    asyncio.run(write_settings_atomically(target, data))

    assert json.loads(target.read_text(encoding="utf-8")) == data
    assert not (tmp_path / "settings.json.tmp").exists()


@pytest.mark.asyncio
async def test_run_setup_guide_writes_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试完整引导流程会把配置写入目标文件。"""

    target = tmp_path / "settings.json"

    async def fake_vendor() -> str:
        return "https://api.deepseek.com/"

    async def fake_api_key() -> str:
        return "secret-key"

    async def fake_model(models) -> str:
        assert models == ["deepseek-v4-pro", "deepseek-v4-flash"]
        return "deepseek-v4-pro"

    monkeypatch.setattr(setup, "_pick_vendor", fake_vendor)
    monkeypatch.setattr(setup, "_prompt_api_key", fake_api_key)
    monkeypatch.setattr(setup, "_pick_model", fake_model)
    monkeypatch.setattr(
        setup,
        "list_models",
        lambda base_url, api_key: ["deepseek-v4-pro", "deepseek-v4-flash"],
    )
    monkeypatch.setattr(
        setup,
        "discover_context_window",
        lambda base_url, api_key, model_name: 128_000,
    )

    completed = await run_setup_guide(target)

    assert completed is True
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "model": {
            "base_url": "https://api.deepseek.com/",
            "api_key": "secret-key",
            "model_name": "deepseek-v4-pro",
            "context_window": 128000,
        }
    }


@pytest.mark.asyncio
async def test_run_setup_guide_manual_model_when_list_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试模型列表拉取失败时仍可手动输入模型名完成引导。"""

    target = tmp_path / "settings.json"

    async def fake_vendor() -> str:
        return "https://example.com"

    async def fake_api_key() -> str:
        return "secret-key"

    async def fake_model(models) -> str:
        assert models is None
        return "manual-model"

    monkeypatch.setattr(setup, "_pick_vendor", fake_vendor)
    monkeypatch.setattr(setup, "_prompt_api_key", fake_api_key)
    monkeypatch.setattr(setup, "_pick_model", fake_model)
    monkeypatch.setattr(setup, "list_models", lambda base_url, api_key: None)
    monkeypatch.setattr(
        setup,
        "discover_context_window",
        lambda base_url, api_key, model_name: 128_000,
    )

    completed = await run_setup_guide(target)

    assert completed is True
    assert json.loads(target.read_text(encoding="utf-8"))["model"]["model_name"] == "manual-model"


@pytest.mark.asyncio
async def test_run_setup_guide_cancel_at_vendor_skips_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试在厂商选择阶段取消时不写任何文件。"""

    target = tmp_path / "settings.json"

    async def fake_cancel():
        """模拟在厂商选择阶段取消。"""

        return None

    monkeypatch.setattr(setup, "_pick_vendor", fake_cancel)

    completed = await run_setup_guide(target)

    assert completed is False
    assert not target.exists()


@pytest.mark.asyncio
async def test_run_setup_guide_cancel_at_api_key_skips_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试在输入 API key 阶段取消时不写任何文件。"""

    target = tmp_path / "settings.json"

    async def fake_vendor() -> str:
        """模拟选择厂商。"""

        return "https://example.com"

    async def fake_cancel():
        """模拟在输入 API key 阶段取消。"""

        return None

    monkeypatch.setattr(setup, "_pick_vendor", fake_vendor)
    monkeypatch.setattr(setup, "_prompt_api_key", fake_cancel)

    completed = await run_setup_guide(target)

    assert completed is False
    assert not target.exists()


@pytest.mark.asyncio
async def test_run_setup_guide_cancel_at_model_skips_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试在选择模型阶段取消时不写任何文件。"""

    target = tmp_path / "settings.json"

    async def fake_vendor() -> str:
        """模拟选择厂商。"""

        return "https://example.com"

    monkeypatch.setattr(setup, "_pick_vendor", fake_vendor)

    async def fake_api_key() -> str:
        """模拟输入 API key。"""

        return "key"

    monkeypatch.setattr(setup, "_prompt_api_key", fake_api_key)

    async def fake_cancel(models):
        """模拟在选择模型阶段取消。"""

        return None

    monkeypatch.setattr(setup, "_pick_model", fake_cancel)

    completed = await run_setup_guide(target)

    assert completed is False
    assert not target.exists()
