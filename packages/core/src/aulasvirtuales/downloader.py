import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

BASE_URL = "https://aulasvirtuales.frba.utn.edu.ar"


def get_resource_files(http: httpx.Client, resource_id: int, module: str) -> list[str]:
    if module == "resource":
        return _get_single_resource_url(http, resource_id)
    elif module == "folder":
        return _get_folder_urls(http, resource_id)
    return []


def _get_single_resource_url(http: httpx.Client, resource_id: int) -> list[str]:
    response = http.get(f"/mod/resource/view.php?id={resource_id}", follow_redirects=True)
    final_url = str(response.url)
    if "pluginfile.php" in final_url and "mod_resource" in final_url:
        return [final_url]
    urls = re.findall(
        r'https://aulasvirtuales\.frba\.utn\.edu\.ar/pluginfile\.php/[^\"\s\?\']+',
        response.text,
    )
    resource_urls = [u for u in urls if "mod_resource" in u]
    return list(dict.fromkeys(resource_urls))


def _get_folder_urls(http: httpx.Client, resource_id: int) -> list[str]:
    response = http.get(f"/mod/folder/view.php?id={resource_id}", follow_redirects=True)
    urls = re.findall(
        r'https://aulasvirtuales\.frba\.utn\.edu\.ar/pluginfile\.php/[^\"\s\?\']+',
        response.text,
    )
    folder_urls = [u for u in urls if "mod_folder" in u]
    return list(dict.fromkeys(folder_urls))


def download_file(
    http: httpx.Client, url: str, dest_dir: Path, filename: str | None = None
) -> Path:
    if filename is None:
        filename = unquote(urlparse(url).path.split("/")[-1])
    dest_path = dest_dir / filename
    dest_dir.mkdir(parents=True, exist_ok=True)

    with http.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)

    return dest_path


def filename_from_url(url: str) -> str:
    return unquote(urlparse(url).path.split("/")[-1])
