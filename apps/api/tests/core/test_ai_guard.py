"""
Verifies the AI safety guard infrastructure introduced for FOMO-131.

These tests prove that:
- The blocker is installed for every normal test run.
- No GOOGLE_API_KEY is required by default.
- integration_ai tests are skipped unless RUN_EXTERNAL_AI_TESTS=true.
"""

import os

import pytest


def test_ai_guard_blocks_real_calls() -> None:
    """Calling _client.chat.completions.create() without a test-level mock raises.

    The autouse _block_real_ai_client fixture replaces the module-level
    _client with a sentinel.  This test confirms the sentinel is active.
    """
    import app.services.harvester.cleansing.ai_extractor as ai_mod

    with pytest.raises(RuntimeError, match="External AI call attempted"):
        ai_mod._client.chat.completions.create()


def test_no_google_api_key_required() -> None:
    """GOOGLE_API_KEY must not be required for normal tests to pass."""
    from app.core.config import Settings

    assert Settings.model_fields["GOOGLE_API_KEY"].default is None


def test_guard_does_not_interfere_with_explicit_patch() -> None:
    """Tests that supply their own patch override the guard cleanly."""
    from unittest.mock import MagicMock, patch

    import app.services.harvester.cleansing.ai_extractor as ai_mod

    custom_mock = MagicMock()
    custom_mock.chat.completions.create.return_value = MagicMock(tasks=[])

    with patch.object(ai_mod, "_client", custom_mock):
        # Inside the patch the custom mock is visible, not the guard blocker.
        assert ai_mod._client is custom_mock
        result = ai_mod._client.chat.completions.create()
        assert result.tasks == []

    # After the patch block, the guard blocker is restored.
    with pytest.raises(RuntimeError, match="External AI call attempted"):
        ai_mod._client.chat.completions.create()


@pytest.mark.integration_ai
def test_integration_ai_opt_in_works() -> None:
    """Marker smoke-test: this test only runs when RUN_EXTERNAL_AI_TESTS=true.

    If you see this output it means the opt-in mechanism is functioning.
    The test itself is intentionally a no-op.
    """
    assert os.getenv("RUN_EXTERNAL_AI_TESTS", "").lower() == "true", (
        "integration_ai test reached without RUN_EXTERNAL_AI_TESTS=true — "
        "the skip guard in pytest_collection_modifyitems is not working."
    )
