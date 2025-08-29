import requests
import re
from bs4 import BeautifulSoup
from core.utils import fetch_html


def d_attendance(token):
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
        total_classes = cells[1].text.strip()
        present_cell = cells[2].find("p")
        absent_cell = cells[3].find("p")

        # Extract attenid if present in either present/absent cell
        attenid = None
        if present_cell and present_cell.has_attr("attenid"):
            attenid = present_cell["attenid"]
        elif absent_cell and absent_cell.has_attr("attenid"):
            attenid = absent_cell["attenid"]

        present = cells[2].text.strip()
        absent = cells[3].text.strip()
        percentage = cells[4].text.strip()

        data.append({
            "Subject": subject,
            "Total Classes": total_classes,
            "Present": present,
            "Absent": absent,
            "Percentage": percentage,
            "altid": attenid  
        })

    return data


def o_attendance(token):
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


def s_attendance(altid, token):
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
