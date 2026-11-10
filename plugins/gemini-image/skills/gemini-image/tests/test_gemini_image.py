import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from gemini_image import slugify, unique_path, generate_image, analyze_image, describe_image, main


def test_slugify_basic():
    assert slugify("a red fox in snow") == "a-red-fox-in-snow"


def test_slugify_lowercases():
    assert slugify("Red Fox") == "red-fox"


def test_slugify_strips_special_chars():
    assert slugify("hello! world?") == "hello-world"


def test_slugify_collapses_multiple_spaces():
    assert slugify("a  b   c") == "a-b-c"


def test_slugify_truncates_at_60_chars():
    long = "word " * 20  # 100 chars
    result = slugify(long)
    assert len(result) <= 60


def test_slugify_no_trailing_hyphen_after_truncation():
    long = "word " * 20
    result = slugify(long)
    assert not result.endswith("-")


def test_unique_path_no_conflict(tmp_path):
    p = unique_path(str(tmp_path / "fox"), ".png")
    assert p == tmp_path / "fox.png"


def test_unique_path_conflict_increments(tmp_path):
    (tmp_path / "fox.png").touch()
    p = unique_path(str(tmp_path / "fox"), ".png")
    assert p == tmp_path / "fox-2.png"


def test_unique_path_multiple_conflicts(tmp_path):
    (tmp_path / "fox.png").touch()
    (tmp_path / "fox-2.png").touch()
    p = unique_path(str(tmp_path / "fox"), ".png")
    assert p == tmp_path / "fox-3.png"


def test_generate_image_saves_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    fake_image = MagicMock()
    fake_image.image.image_bytes = b"\x89PNG fake image bytes"

    fake_response = MagicMock()
    fake_response.generated_images = [fake_image]

    with patch("gemini_image.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_images.return_value = fake_response

        result = generate_image("a red fox in snow", output=None)

    assert result == tmp_path / "a-red-fox-in-snow.png"
    assert result.read_bytes() == b"\x89PNG fake image bytes"


def test_generate_image_uses_output_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    fake_image = MagicMock()
    fake_image.image.image_bytes = b"PNG bytes"
    fake_response = MagicMock()
    fake_response.generated_images = [fake_image]

    with patch("gemini_image.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_images.return_value = fake_response

        result = generate_image("a red fox in snow", output=str(tmp_path / "custom.png"))

    assert result == tmp_path / "custom.png"


def test_analyze_image_prints_response(tmp_path, monkeypatch, capsys):
    img_file = tmp_path / "photo.jpg"
    img_file.write_bytes(b"fake jpeg bytes")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    fake_response = MagicMock()
    fake_response.text = "There is a cat sitting on a mat."

    with patch("gemini_image.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = fake_response

        analyze_image(str(img_file), question="What is in this image?")

    captured = capsys.readouterr()
    assert "There is a cat sitting on a mat." in captured.out


def test_describe_image_prints_response(tmp_path, monkeypatch, capsys):
    img_file = tmp_path / "photo.jpg"
    img_file.write_bytes(b"fake jpeg bytes")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    fake_response = MagicMock()
    fake_response.text = "A sleek product shot with warm lighting."

    with patch("gemini_image.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = fake_response

        describe_image(str(img_file), prompt="Write a marketing caption.")

    captured = capsys.readouterr()
    assert "A sleek product shot with warm lighting." in captured.out


def test_main_dispatches_generate(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    fake_image = MagicMock()
    fake_image.image.image_bytes = b"PNG"
    fake_response = MagicMock()
    fake_response.generated_images = [fake_image]

    with patch("gemini_image.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_images.return_value = fake_response

        with patch("sys.argv", ["gemini_image.py", "--mode", "generate", "--prompt", "a fox"]):
            main()

    assert (tmp_path / "a-fox.png").exists()


def test_main_missing_api_key_exits(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with patch("sys.argv", ["gemini_image.py", "--mode", "generate", "--prompt", "a fox"]):
        with pytest.raises(SystemExit):
            main()
