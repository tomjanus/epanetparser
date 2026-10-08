"""Tests for download module."""

import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest
import responses
import requests

from epanetparser.core.download import (
    download_release_asset,
    extract_zip,
    download_networks,
    NETWORKS_URLS,
)


class TestDownloadReleaseAsset:
    """Tests for download_release_asset function."""

    @responses.activate
    def test_download_release_asset_success(self, tmp_path):
        """Test successful download of release asset."""
        url = "https://github.com/test/repo/releases/download/v1.0/file.txt"
        output_path = tmp_path / "file.txt"
        content = b"test content"

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        result = download_release_asset(url, output_path)

        assert result == output_path
        assert output_path.read_bytes() == content

    @responses.activate
    def test_download_release_asset_creates_parent_dirs(self, tmp_path):
        """Test download creates parent directories."""
        url = "https://github.com/test/repo/releases/download/v1.0/file.txt"
        output_path = tmp_path / "subdir" / "file.txt"
        content = b"test content"

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        result = download_release_asset(url, output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.parent.exists()

    @responses.activate
    def test_download_release_asset_http_error_404(self, tmp_path):
        """Test download raises HTTPError on 404."""
        url = "https://github.com/test/repo/releases/download/v1.0/file.txt"
        output_path = tmp_path / "file.txt"

        responses.add(
            responses.GET,
            url,
            body="Not Found",
            status=404,
        )

        with pytest.raises(requests.HTTPError):
            download_release_asset(url, output_path)

    @responses.activate
    def test_download_release_asset_http_error_500(self, tmp_path):
        """Test download raises HTTPError on 500."""
        url = "https://github.com/test/repo/releases/download/v1.0/file.txt"
        output_path = tmp_path / "file.txt"

        responses.add(
            responses.GET,
            url,
            body="Internal Server Error",
            status=500,
        )

        with pytest.raises(requests.HTTPError):
            download_release_asset(url, output_path)

    @responses.activate
    def test_download_release_asset_timeout(self, tmp_path):
        """Test download handles timeout."""
        url = "https://github.com/test/repo/releases/download/v1.0/file.txt"
        output_path = tmp_path / "file.txt"

        def request_callback(request):
            raise requests.Timeout("Request timed out")

        responses.add_callback(
            responses.GET,
            url,
            callback=request_callback,
        )

        with pytest.raises(requests.Timeout):
            download_release_asset(url, output_path)

    @responses.activate
    def test_download_release_asset_connection_error(self, tmp_path):
        """Test download handles connection error."""
        url = "https://github.com/test/repo/releases/download/v1.0/file.txt"
        output_path = tmp_path / "file.txt"

        def request_callback(request):
            raise requests.ConnectionError("Connection failed")

        responses.add_callback(
            responses.GET,
            url,
            callback=request_callback,
        )

        with pytest.raises(requests.ConnectionError):
            download_release_asset(url, output_path)

    @responses.activate
    def test_download_release_asset_progress_bar_updates(self, tmp_path):
        """Test download updates progress bar."""
        url = "https://github.com/test/repo/releases/download/v1.0/file.txt"
        output_path = tmp_path / "file.txt"
        content = b"x" * 1000

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        mock_progress = MagicMock()
        mock_task_id = 1

        result = download_release_asset(
            url, output_path, progress=mock_progress, task_id=mock_task_id
        )

        assert result == output_path
        mock_progress.update.assert_called()

    @responses.activate
    def test_download_release_asset_quiet_mode(self, tmp_path, capsys):
        """Test download suppresses output in quiet mode."""
        url = "https://github.com/test/repo/releases/download/v1.0/file.txt"
        output_path = tmp_path / "file.txt"
        content = b"test content"

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        download_release_asset(url, output_path, quiet=True)

        captured = capsys.readouterr()
        assert "Downloading:" not in captured.out
        assert "Downloaded:" not in captured.out

    @responses.activate
    def test_download_release_asset_non_quiet_mode(self, tmp_path, capsys):
        """Test download shows output in non-quiet mode."""
        url = "https://github.com/test/repo/releases/download/v1.0/file.txt"
        output_path = tmp_path / "file.txt"
        content = b"test content"

        responses.add(
            responses.GET,
            url,
            body=content,
            status=200,
            headers={"content-length": str(len(content))},
        )

        download_release_asset(url, output_path, quiet=False)

        captured = capsys.readouterr()
        assert "Downloading:" in captured.out
        assert "Downloaded:" in captured.out


class TestExtractZip:
    """Tests for extract_zip function."""

    def test_extract_zip(self, tmp_path):
        """Test extracting a zip file."""
        zip_path = tmp_path / "test.zip"
        extract_dir = tmp_path / "extracted"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("dir/file2.txt", "content2")

        extract_zip(zip_path, extract_dir)

        assert (extract_dir / "file1.txt").read_text() == "content1"
        assert (extract_dir / "dir" / "file2.txt").read_text() == "content2"


class TestDownloadNetworks:
    """Tests for download_networks function."""

    @responses.activate
    def test_download_networks_no_progress(self, tmp_path):
        """Test downloading networks without progress bar."""
        for url in NETWORKS_URLS:
            filename = Path(url).name
            content = f"content of {filename}".encode()
            responses.add(
                responses.GET,
                url,
                body=content,
                status=200,
                headers={"content-length": str(len(content))},
            )

        count = download_networks(tmp_path, progress_bar=False, quiet=True)

        assert count == len(NETWORKS_URLS)
        for url in NETWORKS_URLS:
            filename = Path(url).name
            assert (tmp_path / filename).exists()

    @responses.activate
    def test_download_networks_with_progress(self, tmp_path):
        """Test downloading networks with progress bar."""
        for url in NETWORKS_URLS:
            filename = Path(url).name
            content = f"content of {filename}".encode()
            responses.add(
                responses.GET,
                url,
                body=content,
                status=200,
                headers={"content-length": str(len(content))},
            )

        count = download_networks(tmp_path, progress_bar=True, quiet=True)

        assert count == len(NETWORKS_URLS)

    @responses.activate
    def test_download_networks_quiet_mode(self, tmp_path, capsys):
        """Test downloading networks in quiet mode."""
        for url in NETWORKS_URLS:
            filename = Path(url).name
            content = f"content of {filename}".encode()
            responses.add(
                responses.GET,
                url,
                body=content,
                status=200,
                headers={"content-length": str(len(content))},
            )

        download_networks(tmp_path, progress_bar=False, quiet=True)

        captured = capsys.readouterr()
        assert "Starting download" not in captured.out
        assert "Download complete" not in captured.out

    @responses.activate
    def test_download_networks_non_quiet_mode(self, tmp_path, capsys):
        """Test downloading networks shows progress."""
        for url in NETWORKS_URLS:
            filename = Path(url).name
            content = f"content of {filename}".encode()
            responses.add(
                responses.GET,
                url,
                body=content,
                status=200,
                headers={"content-length": str(len(content))},
            )

        download_networks(tmp_path, progress_bar=False, quiet=False)

        captured = capsys.readouterr()
        assert "Starting download" in captured.out
        assert "Download complete" in captured.out

    @responses.activate
    def test_download_networks_partial_failure(self, tmp_path):
        """Test download continues on partial failure."""
        for i, url in enumerate(NETWORKS_URLS):
            filename = Path(url).name
            if i == 0:
                def http_error_callback(request):
                    response = MagicMock()
                    response.status_code = 404
                    response.reason = "Not Found"
                    raise requests.HTTPError("404 Not Found", response=response)
                responses.add_callback(
                    responses.GET,
                    url,
                    callback=http_error_callback,
                )
            else:
                content = f"content of {filename}".encode()
                responses.add(
                    responses.GET,
                    url,
                    body=content,
                    status=200,
                    headers={"content-length": str(len(content))},
                )

        count = download_networks(tmp_path, progress_bar=False, quiet=True)

        assert count == len(NETWORKS_URLS) - 1

    @responses.activate
    def test_download_networks_connection_error(self, tmp_path):
        """Test download handles connection errors gracefully."""
        for i, url in enumerate(NETWORKS_URLS):
            if i == 0:
                def connection_error_callback(request):
                    raise requests.ConnectionError("Connection failed")
                responses.add_callback(
                    responses.GET,
                    url,
                    callback=connection_error_callback,
                )
            else:
                filename = Path(url).name
                content = f"content of {filename}".encode()
                responses.add(
                    responses.GET,
                    url,
                    body=content,
                    status=200,
                    headers={"content-length": str(len(content))},
                )

        count = download_networks(tmp_path, progress_bar=False, quiet=True)
        assert count == len(NETWORKS_URLS) - 1

    @responses.activate
    def test_download_networks_timeout(self, tmp_path):
        """Test download handles timeout gracefully."""
        for i, url in enumerate(NETWORKS_URLS):
            if i == 0:
                def timeout_callback(request):
                    raise requests.Timeout("Timeout")
                responses.add_callback(
                    responses.GET,
                    url,
                    callback=timeout_callback,
                )
            else:
                filename = Path(url).name
                content = f"content of {filename}".encode()
                responses.add(
                    responses.GET,
                    url,
                    body=content,
                    status=200,
                    headers={"content-length": str(len(content))},
                )

        count = download_networks(tmp_path, progress_bar=False, quiet=True)
        assert count == len(NETWORKS_URLS) - 1

    @responses.activate
    def test_download_networks_creates_output_dir(self, tmp_path):
        """Test download creates output directory."""
        output_dir = tmp_path / "networks" / "extra"

        for url in NETWORKS_URLS:
            filename = Path(url).name
            content = f"content of {filename}".encode()
            responses.add(
                responses.GET,
                url,
                body=content,
                status=200,
                headers={"content-length": str(len(content))},
            )

        count = download_networks(output_dir, progress_bar=False, quiet=True)

        assert count == len(NETWORKS_URLS)
        assert output_dir.exists()


class TestNetworksUrls:
    """Tests for NETWORKS_URLS constant."""

    def test_networks_urls_not_empty(self):
        """Test NETWORKS_URLS is not empty."""
        assert len(NETWORKS_URLS) > 0

    def test_networks_urls_are_github_urls(self):
        """Test all URLs are GitHub release URLs."""
        for url in NETWORKS_URLS:
            assert url.startswith("https://github.com/")
            assert "/releases/download/" in url

    def test_networks_urls_have_inp_or_json_extension(self):
        """Test all URLs end with .inp or .json."""
        for url in NETWORKS_URLS:
            assert url.endswith(".inp") or url.endswith(".json")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])