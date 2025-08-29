import requests
from bs4 import BeautifulSoup
from core.utils import retry_session, fetch_html


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