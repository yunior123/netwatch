import pytest
import json
import time
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def mock_nim_response():
    """Return a mock NIM API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": "No suspicious activity detected. All traffic appears normal.",
                    "role": "assistant",
                }
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }


@pytest.fixture
def nim_module():
    """Import nim_analyzer with mocked API key."""
    import nim_analyzer
    return nim_analyzer


class TestAnalyzeUrls:
    def test_no_api_key(self, nim_module):
        """analyze_urls() without API key should return error."""
        with patch.object(nim_module, "NIM_API_KEY", ""):
            result = nim_module.analyze_urls([], {})
        assert "error" in result
        assert "api key" in result["error"].lower() or "NVIDIA_NIM_API_KEY" in result["error"]

    def test_with_mock_api(self, nim_module, mock_nim_response, sample_events):
        """analyze_urls() should call NIM API and return analysis."""
        with patch.object(nim_module, "NIM_API_KEY", "nvapi-fake-key"):
            with patch("nim_analyzer.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.json.return_value = mock_nim_response
                mock_resp.raise_for_status = MagicMock()
                mock_post.return_value = mock_resp

                result = nim_module.analyze_urls(sample_events, {})

                assert "analysis" in result
                assert "No suspicious" in result["analysis"]
                assert result["model"] == nim_module.NIM_MODEL
                mock_post.assert_called_once()

    def test_api_timeout(self, nim_module, sample_events):
        """analyze_urls() should handle timeout gracefully."""
        with patch.object(nim_module, "NIM_API_KEY", "nvapi-fake-key"):
            with patch("nim_analyzer.requests.post", side_effect=TimeoutError("timeout")):
                result = nim_module.analyze_urls(sample_events, {})
        assert "error" in result

    def test_api_http_error(self, nim_module, sample_events):
        """analyze_urls() should handle HTTP errors."""
        with patch.object(nim_module, "NIM_API_KEY", "nvapi-fake-key"):
            with patch("nim_analyzer.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.raise_for_status.side_effect = Exception("401 Unauthorized")
                mock_post.return_value = mock_resp
                result = nim_module.analyze_urls(sample_events, {})
        assert "error" in result

    def test_limits_events_to_100(self, nim_module, mock_nim_response):
        """analyze_urls() should only use last 100 events."""
        events = [{"t": time.time(), "dev": "1.2.3.4", "kind": "dns", "host": f"h{i}.com"} for i in range(200)]
        with patch.object(nim_module, "NIM_API_KEY", "nvapi-fake-key"):
            with patch("nim_analyzer.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.json.return_value = mock_nim_response
                mock_resp.raise_for_status = MagicMock()
                mock_post.return_value = mock_resp

                nim_module.analyze_urls(events, {})

                call_args = mock_post.call_args
                payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
                prompt = payload["messages"][1]["content"]
                # Should contain events but not all 200
                assert "h199.com" in prompt  # Last event
                assert "h0.com" not in prompt  # First event (dropped)


class TestAnalyzeDevice:
    def test_no_api_key(self, nim_module):
        """analyze_device() without API key should return error."""
        with patch.object(nim_module, "NIM_API_KEY", ""):
            result = nim_module.analyze_device({}, [])
        assert "error" in result

    def test_with_mock_api(self, nim_module, mock_nim_response, sample_device_info, sample_events):
        """analyze_device() should call NIM API with device context."""
        with patch.object(nim_module, "NIM_API_KEY", "nvapi-fake-key"):
            with patch("nim_analyzer.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.json.return_value = mock_nim_response
                mock_resp.raise_for_status = MagicMock()
                mock_post.return_value = mock_resp

                result = nim_module.analyze_device(sample_device_info, sample_events)

                assert "analysis" in result
                call_args = mock_post.call_args
                payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
                prompt = payload["messages"][1]["content"]
                assert "iPhone" in prompt
                assert "192.168.2.10" in prompt


class TestInvestigateDomain:
    def test_no_api_key(self, nim_module):
        """investigate_domain() without API key should return error."""
        with patch.object(nim_module, "NIM_API_KEY", ""):
            result = nim_module.investigate_domain("evil.com")
        assert "error" in result

    def test_with_mock_api(self, nim_module, mock_nim_response):
        """investigate_domain() should call NIM API with domain."""
        with patch.object(nim_module, "NIM_API_KEY", "nvapi-fake-key"):
            with patch("nim_analyzer.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.json.return_value = mock_nim_response
                mock_resp.raise_for_status = MagicMock()
                mock_post.return_value = mock_resp

                result = nim_module.investigate_domain("suspicious-domain.com")

                assert "analysis" in result
                call_args = mock_post.call_args
                payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
                prompt = payload["messages"][1]["content"]
                assert "suspicious-domain.com" in prompt

    def test_invalid_response(self, nim_module):
        """investigate_domain() should handle invalid API response."""
        with patch.object(nim_module, "NIM_API_KEY", "nvapi-fake-key"):
            with patch("nim_analyzer.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.json.return_value = {"invalid": "response"}
                mock_resp.raise_for_status = MagicMock()
                mock_post.return_value = mock_resp
                result = nim_module.investigate_domain("test.com")
        assert "error" in result
