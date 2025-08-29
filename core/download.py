import os
import requests
from urllib.parse import urlparse, unquote
from core.auth import get_token
from core.utils import load_json, dump_json

def download_file(file_url: str, token: str) -> tuple[str, bytes]:
    path = urlparse(file_url).path
    filename = unquote(os.path.basename(path)) or "downloaded_file"
    session = requests.Session()
    session.cookies.set("MoodleSession", token)

    resp = session.get(file_url, stream=True, timeout=30)
    resp.raise_for_status()

    return filename, resp.content

def help_download_file(file_url: str):
    token = get_token()
    return download_file(file_url, token)