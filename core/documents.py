import re
from core.utils import fetch_html, SUBJECTS_DIR, ENDLINK_PATH, load_json, dump_json
from core.auth import get_token
from bs4 import BeautifulSoup

def doc(mod_type, doc_id, token):
	url = f"https://mydy.dypatil.edu/rait/mod/{mod_type}/view.php?id={doc_id}"
	html = fetch_html(url, token)

	if mod_type == "flexpaper":
		m = re.search(r"PDFFile\s*:\s*'(https://mydy\.dypatil\.edu/rait/pluginfile\.php[^']+)'", html)
		return m.group(1) if m else None

	soup = BeautifulSoup(html, "html.parser")
	if mod_type == "dyquestion":
		c = soup.find("div", class_="dyquestioncontent")
		if c:
			for a in c.find_all("a", href=True):
				if "pluginfile.php" in a["href"]:
					return a["href"]
			obj = c.find("object", attrs={"data": True})
			if obj and "pluginfile.php" in obj["data"]:
				return obj["data"]
		return None

	if mod_type in ["presentation", "resource", "casestudy"]:
		divs = soup.find_all("div", class_=["presentationcontent"])
		for div in divs:
			obj = div.find("object", attrs={"data": True})
			if obj and "pluginfile.php" in obj["data"]:
				return obj["data"]
			for a in div.find_all("a", href=True):
				if "pluginfile.php" in a["href"]:
					return a["href"]
		
		obj = soup.find("object", attrs={"data": True})
		if obj and "pluginfile.php" in obj["data"]:
			return obj["data"]
		for a in soup.find_all("a", href=True):
			if "pluginfile.php" in a["href"]:
				return a["href"]
		return None

	if mod_type == "url":
		c = soup.find("div", class_="urlworkaround")
		if c:
			for a in c.find_all("a", href=True):
				if a["href"].startswith("https://"):
					return a["href"]
		return None

	return None

def help_doc(modtype: str, doc_id: int) -> str | None:
    token = get_token()  
    if not ENDLINK_PATH.exists():
        dump_json([], ENDLINK_PATH)

    endlink_data = load_json(ENDLINK_PATH)  

    for item in endlink_data:
        if str(item.get("id")) == str(doc_id):
            print("doc_url Found")
            return item.get("doc_url")

    doc_url = doc(modtype, doc_id, token)
    if doc_url:
        endlink_data.append({"id": doc_id, "doc_url": doc_url})
        dump_json(endlink_data, ENDLINK_PATH)
        return doc_url

    return None
