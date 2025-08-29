import os
import requests
from urllib.parse import urlparse, unquote

def download_file(file_url: str, token: str) -> tuple[str, bytes]:
    path = urlparse(file_url).path
    filename = unquote(os.path.basename(path)) or "downloaded_file"
    session = requests.Session()
    session.cookies.set("MoodleSession", token)

    resp = session.get(file_url, stream=True, timeout=30)
    resp.raise_for_status()

    return filename, resp.content