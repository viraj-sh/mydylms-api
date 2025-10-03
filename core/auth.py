import requests
from bs4 import BeautifulSoup
from core.utils import retry_session, fetch_html, load_json_token, CREDENTIALS_PATH, load_json, dump_json

def get_payload(email, password):
    payload = {
        "uname_static": email,
        "username": email,
        "uname": email,
        "password": password,
        "rememberusername": "1",
        "logintoken": "None"
    }
    return payload

def login(email, password):
    login_url = "https://mydy.dypatil.edu/rait/login/index.php"
    session = retry_session()
    payload = get_payload(email, password)
    token = session.post(login_url, data=payload, timeout=10)
    token.raise_for_status()
    soup = BeautifulSoup(token.text, "html.parser")
    if soup.select_one("div.loginerrors span.error"):
        raise ValueError("Login failed: Invalid credentials.")
    if "Dashboard" not in token.text and "dashboard" not in token.url.lower():
        raise RuntimeError("Login failed for an unknown reason.")
    for cookie in session.cookies:
        if cookie.name.lower() == "moodlesession":
            token = cookie.value  
            return token

def verify_token(token: str) -> bool:
    url = "https://mydy.dypatil.edu/rait/my/"

    html = fetch_html(url, token)
    if not html:
        return False
    soup = BeautifulSoup(html, "html.parser")
    if soup.body and "notloggedin" in soup.body.get("class", []):
        return False
    if soup.select_one("form#login"):
        return False
    return True

def get_token(regenerate: bool = False) -> str:
    creds = load_json(CREDENTIALS_PATH)
    if not creds or "email" not in creds or "password" not in creds:
        raise ValueError("Email or password not found in credentials.json")
    email = creds["email"]
    password = creds["password"]
    token = creds.get("token")
    if regenerate:
        token = login(email, password)
        if not token:
            raise ValueError("Failed to generate token")
        creds["token"] = token
        dump_json(creds, CREDENTIALS_PATH)
        return token
    if token and verify_token(token):
        return token
    return None