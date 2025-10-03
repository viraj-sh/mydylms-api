import re
from urllib.parse import urlparse, parse_qs
from core.utils import load_json
from pathlib import Path
from core.utils import fetch_html, SEM_PATH, dump_json, load_json
from core.auth import get_token
from bs4 import BeautifulSoup


def sem(token: str):
    url = "https://mydy.dypatil.edu/rait/my"
    html = fetch_html(url, token)
    soup = BeautifulSoup(html, "html.parser")
    semesters = []
    for li in soup.find_all("li", class_="type_course"):
        span = li.find("span", class_="usdimmed_text")
        if not span:
            continue
        semester_name = span.get_text(strip=True)

        if not re.fullmatch(
            r"Semester\s+[IVX0-9]+", semester_name, flags=re.IGNORECASE
        ):
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
                subjects.append(
                    {"name": a_tag.get_text(strip=True), "id": int(query["id"][0])}
                )

        if subjects:
            semesters.append({"semester": semester_name, "subjects": subjects})

    return semesters


def sem_sub(json_path: Path, sem_num: int):
    INT_TO_ROMAN = {
        1: "I",
        2: "II",
        3: "III",
        4: "IV",
        5: "V",
        6: "VI",
        7: "VII",
        8: "VIII",
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
            (
                s
                for s in sem_data
                if str(s.get("semester")).lower()
                in {str(sem_num), f"semester {roman.lower()}"}
            ),
            None,
        )

    if not semester_entry:
        raise ValueError(f"Semester {sem_num} not found in {json_path}")

    return [
        {"id": int(subj.get("id")), "name": subj.get("name")}
        for subj in semester_entry.get("subjects", [])
    ]


def load_sem() -> list[dict]:
    if SEM_PATH.exists():
        return load_json(SEM_PATH)
    token = get_token()
    data = sem(token)
    dump_json(data, SEM_PATH)
    return data


def load_semsub(sem_num: int) -> list[dict]:
    sem_file = Path(f"./data/sem_{sem_num}.json")
    if sem_file.exists():
        return load_json(sem_file)
    data = load_sem()
    subjects = sem_sub(SEM_PATH, sem_num)
    dump_json(subjects, sem_file)
    return subjects


def get_valid_sem_no(sem_no: int):
    semesters = load_sem()
    if sem_no == -1:
        sem_no = len(semesters)
    if sem_no < 1 or sem_no > len(semesters):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Semester Number. Allowed: -1 or 1 to {len(semesters)}",
        )
    return sem_no, semesters


def validate_sem(sem_no: int):
    semesters = load_sem()
    if sem_no != -1 and not (1 <= sem_no <= len(semesters)):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Semester Number. Allowed: -1 or 1 to {len(semesters)}",
        )
    return semesters


def validate_sub(sem_no: int, sub_id: int):
    semesters = load_semsub(sem_no)
    if not any(item["id"] == sub_id for item in semesters):
        raise HTTPException(
            status_code=404,
            detail=f"Subject ID {sub_id} not found in Semester {sem_no}",
        )
    return semesters
