import requests
import re
from bs4 import BeautifulSoup
from core.utils import fetch_html
from core.auth import get_token


def d_attendance():
    token = get_token()
    url = "https://mydy.dypatil.edu/rait/blocks/academic_status/ajax.php?action=attendance"
    html = fetch_html(url, token)
    soup = BeautifulSoup(html, "html.parser")
    table_rows = soup.select("tbody > tr")
    data = []

    for row in table_rows:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue  

        subject = cells[0].text.strip()
        total_classes = int(cells[1].text.strip())
        present_cell = cells[2].find("p")
        absent_cell = cells[3].find("p")

        attenid = None
        if present_cell and present_cell.has_attr("attenid"):
            attenid = int(present_cell["attenid"])
        elif absent_cell and absent_cell.has_attr("attenid"):
            attenid = int(absent_cell["attenid"])

        present_str = cells[2].text.strip().replace("--", "")
        present = int(present_str) if present_str else None

        absent_str = cells[3].text.strip().replace("--", "")
        absent = int(absent_str) if absent_str else None

        percentage_str = cells[4].text.strip().replace("--", "")
        percentage = float(percentage_str) if percentage_str else None

        data.append({
            "Subject": subject,
            "Total Classes": total_classes,
            "Present": present,
            "Absent": absent,
            "Percentage": percentage,
            "altid": attenid
        })

    return data


def o_attendance():
    token = get_token()
    url = f"https://mydy.dypatil.edu/rait/blocks/academic_status/ajax.php?action=myclasses"
    html = fetch_html(url, token)
    soup = BeautifulSoup(html, "html.parser")
    circular_value = soup.find("p", class_="circular_value")
    if circular_value:
        value = circular_value.get_text(strip=True)
        import re
        match = re.match(r"(\d+)", value)
        return match.group(1) if match else None
    return None    


def s_attendance(altid):
    token = get_token()
    url = f"https://mydy.dypatil.edu/rait/local/attendance/studentreport.php?id={altid}"
    html = fetch_html(url, token)
    soup = BeautifulSoup(html, "html.parser")
    table_rows = soup.select("tbody > tr")
    records = []

    for row in table_rows:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue
        record = {
            "Class No": cells[0].text.strip(),
            "Subject": cells[1].text.strip(),
            "Date": cells[2].text.strip(),
            "Time": cells[3].text.strip(),
            "Status": cells[4].text.strip(),
        }
        records.append(record)
    return records    
