"""
Tests for Velodictum 3-Tier Validated Model Catalog and Detail Inspector
"""
import pytest
from core.formatting_providers import (
    get_model_tiers,
    get_tier_for_model,
    get_curated_models_catalog,
    get_model_details,
    CURATED_MODELS_SPECS,
)


def test_model_tiers_structure():
    tiers = get_model_tiers()
    assert "speed" in tiers
    assert "balanced" in tiers
    assert "quality" in tiers

    # Check Tier 1: Speed
    speed = tiers["speed"]
    assert speed["model"] == "google/gemini-2.5-flash"
    assert "google/gemini-2.5-flash-lite" in speed["models"]
    assert "openai/gpt-4o-mini" in speed["models"]
    assert "meta-llama/llama-3.3-70b-instruct" in speed["models"]
    assert len(speed["models"]) >= 4

    # Check Tier 2: Balanced
    balanced = tiers["balanced"]
    assert balanced["model"] == "deepseek/deepseek-chat"
    assert "mistralai/mistral-small-24b-instruct-2501" in balanced["models"]
    assert "anthropic/claude-3-haiku" in balanced["models"]
    assert len(balanced["models"]) >= 3

    # Check Tier 3: Quality
    quality = tiers["quality"]
    assert quality["model"] == "qwen/qwen-2.5-72b-instruct"
    assert "openai/gpt-4o" in quality["models"]
    assert "anthropic/claude-sonnet-4" in quality["models"]
    assert len(quality["models"]) >= 3


def test_get_tier_for_model():
    # Direct IDs
    assert get_tier_for_model("google/gemini-2.5-flash") == "speed"
    assert get_tier_for_model("google/gemini-2.5-flash-lite") == "speed"
    assert get_tier_for_model("openai/gpt-4o-mini") == "speed"
    assert get_tier_for_model("meta-llama/llama-3.3-70b-instruct") == "speed"

    assert get_tier_for_model("deepseek/deepseek-chat") == "balanced"
    assert get_tier_for_model("mistralai/mistral-small-24b-instruct-2501") == "balanced"
    assert get_tier_for_model("anthropic/claude-3-haiku") == "balanced"

    assert get_tier_for_model("qwen/qwen-2.5-72b-instruct") == "quality"
    assert get_tier_for_model("openai/gpt-4o") == "quality"
    assert get_tier_for_model("anthropic/claude-sonnet-4") == "quality"

    # Aliases and partials
    assert get_tier_for_model("gemini-2.5-flash") == "speed"
    assert get_tier_for_model("gpt-4o-mini") == "speed"
    assert get_tier_for_model("deepseek-chat") == "balanced"
    assert get_tier_for_model("qwen-2.5-72b-instruct") == "quality"
    assert get_tier_for_model("claude-sonnet-4") == "quality"

    # Unknown
    assert get_tier_for_model("some-random-unknown-model-xyz") is None
    assert get_tier_for_model("") is None


def test_curated_models_catalog():
    catalog = get_curated_models_catalog()
    assert len(catalog) == 10
    ids = [m["id"] for m in catalog]
    assert "google/gemini-2.5-flash" in ids
    assert "openai/gpt-4o-mini" in ids
    assert "qwen/qwen-2.5-72b-instruct" in ids


def test_get_model_details_curated():
    # Test details for Gemini 2.5 Flash
    det_gem = get_model_details("google/gemini-2.5-flash")
    assert det_gem["key"] == "speed"
    assert "1.048.576" in det_gem["context"] or "1M" in det_gem["context"]
    assert "0.30" in det_gem["cost_input"]

    # Test details for Qwen 2.5 72B
    det_qwen = get_model_details("qwen/qwen-2.5-72b-instruct")
    assert det_qwen["key"] == "quality"
    assert "0.36" in det_qwen["cost_input"]

    # Test details for Claude Sonnet 4
    det_sonnet = get_model_details("anthropic/claude-sonnet-4")
    assert det_sonnet["key"] == "quality"
    assert "3.00" in det_sonnet["cost_input"]


def test_get_model_details_fallback_heuristics():
    # Test custom compact model
    det_custom_fast = get_model_details("my-custom-mini-model")
    assert det_custom_fast["key"] == "custom"

    # Test custom large model
    det_custom_large = get_model_details("my-custom-70b-model")
    assert det_custom_large["key"] == "custom"

    # Test generic custom model
    det_generic = get_model_details("custom-unknown-endpoint-model")
    assert det_generic["key"] == "custom"
