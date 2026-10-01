"""Network file download utilities from GitHub releases.

This module provides utilities for downloading EPANET network files from
GitHub release assets. It supports progress monitoring, progress bars, and
error handling for robust file downloads.

Examples
--------
>>> from pathlib import Path
>>> from epanetparser.download import download_networks
>>> download_networks(Path("networks/extra"), progress_bar=True, quiet=False)

Notes
-----
The module downloads network files (.inp and .json) from GitHub releases
and can display progress using the rich library.
"""
from pathlib import Path
from typing import Optional
import zipfile
import requests
from rich import print as rprint
from rich.progress import (
    Progress,
    BarColumn,
    DownloadColumn,
    TextColumn,
)


NETWORKS_URLS = (
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/anytown-exeter.inp",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/anytown-exeter.json",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/gessler1985.inp",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/gessler1985.json",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/hanoi-exeter.inp",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/hanoi-exeter.json",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/Hanoi.inp",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/Hanoi.json",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/ky10.inp",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/ky10.json",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/ky4.inp",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/ky4.json",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/L-TOWN.inp",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/L-TOWN.json",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/nytun.inp",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/nytun.json",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/Richmond_skeleton.inp",
    "https://github.com/tomjanus/epanetparser/releases/download/extra_networks_1_0/Richmond_skeleton.json"
)

def download_release_asset(
    url: str,
    output_path: Path,
    chunk_size: int = 8_192,
    progress: Optional[Progress] = None,
    task_id: Optional[int] = None,
    quiet: bool = False,
) -> Path:
    """Download a GitHub release asset with optional progress tracking.
    
    Parameters
    ----------
    url : str
        URL of the GitHub release asset to download.
    output_path : Path
        Local path where the file will be saved.
    chunk_size : int, optional
        Size of chunks to download at a time in bytes, by default 8192.
    progress : Optional[Progress], optional
        Rich Progress instance for tracking download progress, by default None.
    task_id : Optional[int], optional
        Task ID in the Progress instance for this download, by default None.
    quiet : bool, optional
        If True, suppress status messages, by default False.
    
    Returns
    -------
    Path
        Path to the downloaded file.
    
    Raises
    ------
    requests.HTTPError
        If the HTTP request returns an error status code.
    requests.ConnectionError
        If a network connection problem occurs.
    requests.Timeout
        If the request times out.
    OSError
        If file creation or writing fails.
    PermissionError
        If insufficient permissions to write to output path.
    ValueError
        If the content-length header contains an invalid value.
    
    Examples
    --------
    >>> from pathlib import Path
    >>> url = "https://github.com/user/repo/releases/download/v1.0/file.txt"
    >>> download_release_asset(url, Path("output/file.txt"))
    PosixPath('output/file.txt')
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not quiet:
        rprint(f"[cyan]Downloading:[/cyan] {output_path.name}")
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    # Get total file size if available
    total_size = int(response.headers.get('content-length', 0))
    # Update progress bar total if provided
    if progress and task_id is not None and total_size > 0:
        progress.update(task_id, total=total_size)
    downloaded_size = 0
    with output_path.open("wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded_size += len(chunk)
                # Update progress if provided
                if progress and task_id is not None:
                    progress.update(task_id, advance=len(chunk))
    if not quiet:
        size_mb = downloaded_size / (1024 * 1024)
        rprint(f"[green]✓ Downloaded:[/green] {output_path.name} ({size_mb:.2f} MB)")
    return output_path


def extract_zip(zip_path: Path, output_dir: Path) -> None:
    """Extract a ZIP archive to a specified directory.
    
    Parameters
    ----------
    zip_path : Path
        Path to the ZIP file to extract.
    output_dir : Path
        Directory where files will be extracted.
    
    Examples
    --------
    >>> extract_zip(Path("archive.zip"), Path("output_folder"))
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(output_dir)



def download_networks(
    output_dir: Path,
    progress_bar: bool = False,
    quiet: bool = False,
) -> int:
    """Download EPANET network files from GitHub releases.
    
    Downloads all network files defined in NETWORKS_URLS to the specified
    output directory. Optionally displays a progress bar and download statistics.
    
    Parameters
    ----------
    output_dir : Path
        Directory where network files will be saved.
    progress_bar : bool, optional
        If True, display a rich progress bar during downloads, by default False.
    quiet : bool, optional
        If True, suppress status messages (progress bar still shown if enabled),
        by default False.
    
    Returns
    -------
    int
        Number of files successfully downloaded.
    
    Notes
    -----
    Individual file download errors (HTTP errors, connection errors, timeouts, 
    file I/O errors) are caught and logged but do not stop the download process.
    The function continues attempting to download remaining files and returns 
    the count of successful downloads.
    
    Examples
    --------
    >>> from pathlib import Path
    >>> # Download with progress bar
    >>> count = download_networks(Path("networks/extra"), progress_bar=True)
    >>> print(f"Downloaded {count} files")
    
    >>> # Download quietly without progress bar
    >>> count = download_networks(Path("networks/extra"), quiet=True)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    total_files = len(NETWORKS_URLS)
    downloaded_count = 0
    if not quiet:
        rprint(f"\n[bold cyan]Starting download of {total_files} network files[/bold cyan]")
        rprint(f"[cyan]Output directory:[/cyan] {output_dir.resolve()}\n")
    if progress_bar:
        # Use rich progress bar
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
        ) as progress:
            for idx, network_url in enumerate(NETWORKS_URLS, 1):
                network_filename = Path(network_url).name
                archive = output_dir / network_filename
                # Create a task for this file
                task_id = progress.add_task(
                    f"[{idx}/{total_files}] {network_filename}",
                    total=0,
                )
                try:
                    download_release_asset(
                        network_url,
                        archive,
                        progress=progress,
                        task_id=task_id,
                        quiet=True,  # Suppress individual messages when using progress bar
                    )
                    downloaded_count += 1
                except requests.HTTPError as exc:
                    progress.console.print(f"[red]✗ HTTP Error:[/red] {network_filename} - {exc.response.status_code} {exc.response.reason}")
                except requests.ConnectionError as exc:
                    progress.console.print(f"[red]✗ Connection Error:[/red] {network_filename} - Failed to connect")
                except requests.Timeout as exc:
                    progress.console.print(f"[red]✗ Timeout:[/red] {network_filename} - Request timed out")
                except (OSError, PermissionError) as exc:
                    progress.console.print(f"[red]✗ File Error:[/red] {network_filename} - {exc}")
                except ValueError as exc:
                    progress.console.print(f"[red]✗ Value Error:[/red] {network_filename} - {exc}")
    else:
        # Download without progress bar
        for idx, network_url in enumerate(NETWORKS_URLS, 1):
            network_filename = Path(network_url).name
            archive = output_dir / network_filename
            if not quiet:
                rprint(f"[dim]({idx}/{total_files})[/dim]", end=" ")
            try:
                download_release_asset(
                    network_url,
                    archive,
                    quiet=quiet,
                )
                downloaded_count += 1
            except requests.HTTPError as exc:
                if not quiet:
                    rprint(f"[red]✗ HTTP Error {network_filename}:[/red] {exc.response.status_code} {exc.response.reason}")
            except requests.ConnectionError:
                if not quiet:
                    rprint(f"[red]✗ Connection Error {network_filename}:[/red] Failed to connect to server")
            except requests.Timeout:
                if not quiet:
                    rprint(f"[red]✗ Timeout {network_filename}:[/red] Request timed out after 30 seconds")
            except (OSError, PermissionError) as exc:
                if not quiet:
                    rprint(f"[red]✗ File Error {network_filename}:[/red] {exc}")
            except ValueError as exc:
                if not quiet:
                    rprint(f"[red]✗ Value Error {network_filename}:[/red] {exc}")
    if not quiet:
        rprint(f"\n[bold green]Download complete![/bold green] ")
        rprint(f"[green]Successfully downloaded {downloaded_count}/{total_files} files[/green]")
        rprint(f"[green]Files saved to:[/green] {output_dir.resolve()}\n")
    return downloaded_count


if __name__ == "__main__":
    # Example usage: Download networks with progress bar
    output_directory = Path("networks/extra")
    rprint("[bold]EPANET Networks Downloader[/bold]")
    rprint("=" * 60)
    # Download with progress bar
    count = download_networks(
        output_directory,
        progress_bar=True,
        quiet=False,
    )
    rprint(f"\n[bold cyan]Summary:[/bold cyan] {count} files downloaded to {output_directory}")