import re
from core.utils import fetch_html, SUBJECTS_DIR, ENDLINK_PATH, load_json, dump_json
from core.auth import get_token
from bs4 import BeautifulSoup
from core.subjects import sub, load_sub
import io, mimetypes
from fastapi import FastAPI, Path, Query, Depends, HTTPException
from typing import List, Dict, Any, Optional
from fastapi.responses import StreamingResponse


def doc(mod_type, doc_id, token):
    url = f"https://mydy.dypatil.edu/rait/mod/{mod_type}/view.php?id={doc_id}"
    html = fetch_html(url, token)

    if mod_type == "flexpaper":
        m = re.search(
            r"PDFFile\s*:\s*'(https://mydy\.dypatil\.edu/rait/pluginfile\.php[^']+)'",
            html,
        )
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


def get_doc_entry(sub_id: int, doc_id: int):
    try:
        semsub = load_sub(sub_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    doc_entry = next((d for d in semsub if str(d["id"]) == str(doc_id)), None)
    if not doc_entry:
        raise HTTPException(
            status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}"
        )
    return doc_entry


def guess_media_type(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def build_streaming_response(filename: str, content: bytes, inline: bool = True):
    disposition = "inline" if inline else "attachment"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=guess_media_type(filename) if inline else "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


def get_subject_or_404(sub_id: int = Path(..., ge=1)):
    """Fetch subject or raise 404."""
    try:
        semsub = load_sub(sub_id)  # <-- your existing function
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not semsub:
        raise HTTPException(
            status_code=404, detail=f"No data found for subject {sub_id}"
        )
    return semsub


def get_doc_or_404(
    sub_id: int = Path(..., ge=1),
    doc_id: int = Path(..., ge=1),
    semsub: List[Dict[str, Any]] = Depends(get_subject_or_404),
):
    doc_entry = next((d for d in semsub if str(d["id"]) == str(doc_id)), None)
    if not doc_entry:
        raise HTTPException(
            status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}"
        )
    return doc_entry


def get_doc_url_or_500(mod_type: str, doc_id: int):
    """Fetch document URL or raise 500."""
    try:
        return help_doc(mod_type, doc_id)  # <-- your existing function
    except Exception as e:
        logger.exception(f"help_doc failed for {mod_type} #{doc_id}")
        raise HTTPException(status_code=500, detail="Internal error fetching document")
