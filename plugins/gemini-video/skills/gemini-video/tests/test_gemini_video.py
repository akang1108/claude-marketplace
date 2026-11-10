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


def test_generate_video_text_saves_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    fake_video = MagicMock()
    fake_video.video.video_bytes = b"fake mp4 bytes"

    fake_op = MagicMock()
    fake_op.done = True
    fake_op.response.generated_videos = [fake_video]

    with patch("gemini_video.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_videos.return_value = fake_op

        from gemini_video import generate_video
        result = generate_video(prompt="a timelapse of clouds", image_path=None, output=None)

    assert result == tmp_path / "a-timelapse-of-clouds.mp4"
    assert result.read_bytes() == b"fake mp4 bytes"


def test_generate_video_uses_output_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    fake_video = MagicMock()
    fake_video.video.video_bytes = b"mp4"
    fake_op = MagicMock()
    fake_op.done = True
    fake_op.response.generated_videos = [fake_video]

    with patch("gemini_video.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_videos.return_value = fake_op

        from gemini_video import generate_video
        result = generate_video(
            prompt="clouds", image_path=None, output=str(tmp_path / "custom.mp4")
        )

    assert result == tmp_path / "custom.mp4"


def test_generate_video_polls_until_done(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    fake_video = MagicMock()
    fake_video.video.video_bytes = b"mp4"

    not_done = MagicMock()
    not_done.done = False

    done = MagicMock()
    done.done = True
    done.response.generated_videos = [fake_video]

    with patch("gemini_video.genai") as mock_genai, patch("gemini_video.time") as mock_time:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_videos.return_value = not_done
        mock_client.operations.get.return_value = done
        mock_time.time.side_effect = [0, 5, 10]  # start, poll 1, poll 2

        from gemini_video import generate_video
        result = generate_video(prompt="clouds", image_path=None, output=None)

    captured = capsys.readouterr()
    assert "Generating" in captured.out
    mock_time.sleep.assert_called()
