import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv, set_key, dotenv_values
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def save_token(token: str, env_path: Path):
    load_dotenv(env_path)
    set_key(str(env_path), "TOKEN", token)

def load_token(env_path: Path) -> str | None:
    if not env_path.exists():
        return None
    config = dotenv_values(env_path)
    return config.get("TOKEN")

def remove_token(env_path: Path):
    if not env_path.exists():
        return
    config = dotenv_values(env_path)
    if "TOKEN" in config:
        lines = env_path.read_text().splitlines()
        new_lines = [line for line in lines if not line.startswith("TOKEN=")]
        env_path.write_text("\n".join(new_lines))
        
def dump_json(data, json_path: Path, indent: int = 4):
    json_path.parent.mkdir(parents=True, exist_ok=True)  
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)  
        
def load_json(json_path):
    json_path = Path(json_path)
    if not json_path.exists():
        return None
    
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)              

def retry_session():
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[502, 503, 504, 408],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_html(url :str, token :str):
    session = requests.Session()
    session.cookies.set("MoodleSession", token)
    resp = session.get(url, timeout=10)
    resp.raise_for_status()
    return resp.text
