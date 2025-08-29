import requests
from bs4 import BeautifulSoup
from core.utils import dump_json
from core.utils import fetch_html
from pathlib import Path
from urllib.parse import urlparse, parse_qs

def extract_resource_id(href):
	parsed = urlparse(href)
	if "/mod/" in parsed.path and "/view.php" in parsed.path:
		qs = parse_qs(parsed.query)
		if "id" in qs:
			return qs["id"][0]
	return None

def extract_module_type(href):
	parsed = urlparse(href)
	parts = parsed.path.split('/')
	try:
		idx = parts.index('mod')
		return parts[idx + 1]
	except (ValueError, IndexError):
		return None
        
def parse_documents(html):
	soup = BeautifulSoup(html, "html.parser")
	docs = []

	for a in soup.find_all("a", href=True):
		href = a["href"]
		docid = extract_resource_id(href)
		if not docid:
			continue
		mod_type = extract_module_type(href)
		if not mod_type:
			continue

		div = a.find("div")
		text = div.get_text(" ", strip=True) if div else a.get_text(" ", strip=True)
		text = text.replace('\xa0', ' ').replace('&nbsp;', ' ').replace('&nbsp', ' ').replace("Presentation (Secured PDF)", "").replace("File", "").replace("Presentation (Download)", "").replace("Reference URL", "").replace("Discussion Forum", "").replace("Question Bank", "").replace("Quiz", "").replace("File", "").replace("File", "").replace("File", "").replace("File", "").replace("File", "").replace("File", "").strip()

		first_word = text.split()[0] if text else ""
		if first_word.lower() == "training" or (first_word and first_word[0].isdigit()):
			continue

		docs.append({
			"id": docid,
			"name": text,
			"mod_type": mod_type
		})
	return docs

def sub(sub_id, token):
    url = f"https://mydy.dypatil.edu/rait/course/view.php?id={sub_id}"
    try:
        html = fetch_html(url, token)
    except requests.exceptions.HTTPError as e:
        raise ValueError(f"Invalid subject id: {sub_id}") from e
    docs = parse_documents(html) or []
    if not docs:
        raise ValueError(f"No documents found for subject id: {sub_id}")
    # dump_json(docs, Path(f"./data/{sub_id}.json"))
    return docs
    