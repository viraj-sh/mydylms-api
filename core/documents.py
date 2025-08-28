import re
from core.utils import fetch_html
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
