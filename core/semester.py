import re
from urllib.parse import urlparse, parse_qs
from core.utils import load_json
from pathlib import Path
from core.utils import fetch_html
from bs4 import BeautifulSoup

def sem(url: str, token: str):
    html = fetch_html(url, token)
    soup = BeautifulSoup(html, "html.parser")
    semesters = []
    for li in soup.find_all("li", class_="type_course"):
        span = li.find("span", class_="usdimmed_text")
        if not span:
            continue
        semester_name = span.get_text(strip=True)

        
        if not re.fullmatch(r"Semester\s+[IVX0-9]+", semester_name, flags=re.IGNORECASE):
            continue

        
        p_tag = span.find_parent("p")
        ul_tag = p_tag.find_next_sibling("ul") if p_tag else None
        if not ul_tag:
            ul_tag = li.find("ul")  
        if not ul_tag:
            continue

        subjects = []
        for subject_li in ul_tag.find_all("li", recursive=False):
            a_tag = subject_li.find("a", href=True)
            if not a_tag:
                continue

            
            parsed_url = urlparse(a_tag["href"])
            query = parse_qs(parsed_url.query)
            if "/course/view.php" in parsed_url.path and "id" in query:
                subjects.append({
                    "name": a_tag.get_text(strip=True),
                    "id": query["id"][0]
                })

        if subjects:
            semesters.append({
                "semester": semester_name,
                "subjects": subjects
            })

    return semesters

def sem_sub(json_path: Path, sem_num: int):
    INT_TO_ROMAN = {
    1: "I", 2: "II", 3: "III", 4: "IV",
    5: "V", 6: "VI", 7: "VII", 8: "VIII"
    }
    sem_data = load_json(json_path)
    if not sem_data:
        raise ValueError(f"No data found in {json_path}")

    if sem_num == -1:
        semester_entry = sem_data[-1]

    else:
        roman = INT_TO_ROMAN.get(sem_num)
        if not roman:
            raise ValueError(f"Semester {sem_num} out of range (1–8)")

        
        semester_entry = next(
            (s for s in sem_data
             if str(s.get("semester")).lower() in {str(sem_num), f"semester {roman.lower()}"}),
            None
        )

    if not semester_entry:
        raise ValueError(f"Semester {sem_num} not found in {json_path}")

    return [
        {"id": subj.get("id"), "name": subj.get("name")}
        for subj in semester_entry.get("subjects", [])
    ]
