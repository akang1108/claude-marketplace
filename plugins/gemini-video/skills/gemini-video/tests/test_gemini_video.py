import base64
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


def test_slugify_basic():
    from gemini_video import slugify
    assert slugify("a timelapse of clouds") == "a-timelapse-of-clouds"


def test_slugify_truncates():
    from gemini_video import slugify
    long = "word " * 20
    assert len(slugify(long)) <= 60


def test_unique_path_no_conflict(tmp_path):
    from gemini_video import unique_path
    p = unique_path(str(tmp_path / "clouds"), ".mp4")
    assert p == tmp_path / "clouds.mp4"


def test_unique_path_conflict(tmp_path):
    from gemini_video import unique_path
    (tmp_path / "clouds.mp4").touch()
    p = unique_path(str(tmp_path / "clouds"), ".mp4")
    assert p == tmp_path / "clouds-2.mp4"


def _patched_client(mock_genai, video_bytes=b"mp4"):
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    interaction = MagicMock()
    interaction.output_video.data = base64.b64encode(video_bytes).decode()
    mock_client.interactions.create.return_value = interaction
    return mock_client


def test_generate_video_text_saves_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    with patch("gemini_video.genai") as mock_genai:
        _patched_client(mock_genai, b"fake mp4 bytes")

        from gemini_video import generate_video
        result = generate_video(prompt="a timelapse of clouds", image_paths=[], output=None)

    assert result == tmp_path / "a-timelapse-of-clouds.mp4"
    assert result.read_bytes() == b"fake mp4 bytes"


def test_generate_video_uses_output_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    with patch("gemini_video.genai") as mock_genai:
        _patched_client(mock_genai)

        from gemini_video import generate_video
        result = generate_video(prompt="clouds", image_paths=[], output=str(tmp_path / "custom.mp4"))

    assert result == tmp_path / "custom.mp4"


def test_generate_video_sends_format_options(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    with patch("gemini_video.genai") as mock_genai:
        client = _patched_client(mock_genai)

        from gemini_video import generate_video, MODELS
        generate_video(prompt="clouds", image_paths=[], output=None, duration=5, resolution="1080p", aspect_ratio="9:16")

    kwargs = client.interactions.create.call_args.kwargs
    assert kwargs["model"] == MODELS[0]
    assert kwargs["input"] == "clouds"
    assert kwargs["response_format"] == {
        "type": "video", "duration": "5s", "resolution": "1080p", "aspect_ratio": "9:16",
    }


def test_generate_video_sends_images_as_parts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    img = tmp_path / "a.png"
    img.write_bytes(b"png")

    with patch("gemini_video.genai") as mock_genai:
        client = _patched_client(mock_genai)

        from gemini_video import generate_video
        generate_video(prompt="a river", image_paths=[str(img)], output=None)

    parts = client.interactions.create.call_args.kwargs["input"]
    assert parts[0] == {"type": "image", "data": base64.b64encode(b"png").decode(), "mime_type": "image/png"}
    assert parts[-1] == {"type": "text", "text": "a river"}


def test_generate_video_errors_when_no_video(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    with patch("gemini_video.genai") as mock_genai:
        client = _patched_client(mock_genai)
        client.interactions.create.return_value.output_video = None

        from gemini_video import generate_video
        with pytest.raises(SystemExit):
            generate_video(prompt="clouds", image_paths=[], output=None)


def test_generate_video_falls_back_when_model_not_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    class NotFound(Exception):
        status_code = 404

    with patch("gemini_video.genai") as mock_genai:
        client = _patched_client(mock_genai, b"ok")
        good = client.interactions.create.return_value
        client.interactions.create.side_effect = [NotFound(), good]

        from gemini_video import generate_video, MODELS
        result = generate_video(prompt="clouds", image_paths=[], output=None)

    models_tried = [c.kwargs["model"] for c in client.interactions.create.call_args_list]
    assert models_tried == list(MODELS[:2])
    assert result.read_bytes() == b"ok"


def test_generate_video_does_not_swallow_other_errors(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    class Boom(Exception):
        status_code = 402

    with patch("gemini_video.genai") as mock_genai:
        client = _patched_client(mock_genai)
        client.interactions.create.side_effect = Boom()

        from gemini_video import generate_video
        with pytest.raises(Boom):
            generate_video(prompt="clouds", image_paths=[], output=None)
    assert client.interactions.create.call_count == 1


def test_validate_duration_rejects_out_of_range():
    from gemini_video import validate_duration
    assert validate_duration(3) == "3s"
    assert validate_duration(15) == "15s"
    with pytest.raises(SystemExit):
        validate_duration(2)
    with pytest.raises(SystemExit):
        validate_duration(16)
