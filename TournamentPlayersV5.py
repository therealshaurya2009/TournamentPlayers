from tkinter import filedialog
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import os
import platform
import subprocess
import tempfile
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import plotly.graph_objects as go
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk
import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from bs4 import BeautifulSoup
from selenium.webdriver import Edge
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import plotly.graph_objects as go
import requests
from datetime import date
from reportlab.platypus import HRFlowable
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import json
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    options = Options()
    
    # Enable headless mode (modern)
    options.add_argument("--headless=new")  # Use "--headless" if Chrome <109

    # Create driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    return driver

def age_groups(link):
    driver = setup_driver()
    driver.get(link.lower())
    groups = [h6.text for h6 in BeautifulSoup(driver.page_source, 'lxml').find("tbody", class_="MuiTableBody-root css-y6j1my").find_all("h6")]
    return groups

def scrape_usta(player_link):
    player_id = player_link.strip("https://www.usta.com/en/home/play/player-search/profile.html#uaid=")
    driver = setup_driver()
    driver.get(player_link + "&tab=about")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "readonly-text__text")))

    # Fetch player name
    player_name = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[5]/div/div[2]/div/div/div[3]/div/div/div[1]/div/div/div[2]/div/form/div[2]/div/div/div/div/div/div/div[2]/div/div/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div/div/span/h3"))
    )
    player_name = player_name.text.strip("\n") if player_name else "Unknown Player"

    # Get player location
    try: location = BeautifulSoup(driver.page_source, 'lxml').find_all("div", class_="readonly-text__content")[1].text.split('|')[1].split('Section:')[0]
    except (AttributeError, IndexError): location = "Unknown"

    try: district = BeautifulSoup(driver.page_source, 'lxml').find_all("div", class_="readonly-text__content")[1].text.split("|")[2].split(": ")[1]
    except (AttributeError, IndexError): location = "Unknown"

    # Get WTN (World Tennis Number)
    try: wtn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[5]/div/div[2]/div/div/div[3]/div/div/div[2]/div/div/div[2]/div/div[3]/div/div/div/div[2]/div/form/div[3]/div/div/div/div[1]/div/div[2]/div[1]/div/p"))
    ).text
    except AttributeError: wtn = "40.00"  # Default WTN if not available

    # Get ranking and points
    driver.get(player_link + "&tab=rankings")
    ranking_info = BeautifulSoup(driver.page_source, 'lxml').find_all("div", class_="v-grid-cell__content")

    points = "0"  # Default points if not available
    rank = "20000"  # Default rank if not available

    try:
        for j in range(0, len(ranking_info), 5):
            if "National Standings List (combined)" in ranking_info[j].text:
                if age_group.split()[1] in ranking_info[j].text:
                    points = ranking_info[j + 1].text.strip("\n") if j + 1 < len(ranking_info) else "0"
                    rank = ranking_info[j + 2].text.strip("\n") if j + 2 < len(ranking_info) else "20,000"
                    break
    except:
        points = "0"
        rank = "20,000"

    return(player_name, location, district, wtn, points, rank)

def scrape_recruiting(name, location):
    driver = setup_driver()
    driver.get("https://www.tennisrecruiting.net/player.asp")
    player_name = driver.find_element(By.NAME, "f_playername")
    player_name.send_keys(name)
    player_name.send_keys(Keys.RETURN)
    grades = ["Graduate","Senior","Junior","Sophomore","Freshman","8th Grader","7th Grader","6th Grader"]
    try:
        # Wait until the rating image is loaded
        rating = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[4]/td/img"))
        )
        try:
            utr = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'app.utrsports.net')]"))
        )
        except:
            utr = "?"
        try:
            year = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[3]/td[2]/div[3]"))
        )
            year = year.text
            if "Provisional" in year:
                for i in grades:
                    if i in year:
                        year = i
                        break
                year = year + "?"
            else:
                for i in grades:
                    if i in year:
                        year = i
                        break
        except:
            year = "?"
    except:
        players = BeautifulSoup(driver.page_source, 'lxml').find("table", class_="list").find_all("tr")
        links = []
        homes = []
        for i in players[1:]:
            links.append(i.find_all("td")[0].find("b").find("a").get("href"))
            homes.append(i.find_all("td")[1].text + ", " + i.find_all("td")[2].text)
        for i in homes:
            if i == location:
                driver.get("https://www.tennisrecruiting.net" + links[homes.index(i)])
                # Wait until the rating image is loaded in the second driver
                rating = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[4]/td/img"))
                )
                try:
                    utr = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'app.utrsports.net')]"))
                )
                except:
                    utr = "?"
                try:
                    year = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[3]/td[2]/div[3]"))
                )
                    year = year.text
                    if "Provisional" in year:
                        for i in grades:
                            if i in year:
                                year = i
                                break
                        year = year + "?"
                    else:
                        for i in grades:
                            if i in year:
                                year = i
                                break
                except:
                    year = "?"
    return([rating.get_attribute("src"),utr.text,year])

def scrape_draw_size(link, age_group):
    driver = setup_driver()
    driver.get(link)
    age_groups = BeautifulSoup(driver.page_source, 'lxml').find_all("h6", class_="_H6_1iwqn_128")
    links = BeautifulSoup(driver.page_source, 'lxml').find_all("a", class_="_link_19t7t_285")
    groups_final = []
    for i in age_groups:
        groups_final.append(i.text)
    link_final = links[groups_final.index(age_group) - 1]
    link_final = "https://playtennis.usta.com" + link_final.get("href")
    driver.get(link_final)
    time.sleep(5)
    draw_size = BeautifulSoup(driver.page_source, 'lxml').find_all("span", class_="_bodyXSmall_1iwqn_137")
    driver.quit()
    return(draw_size[1].text)
    
def scrape_player(player_link):
    """
    Scrape individual player data.
    """
    try:
        info = scrape_usta(player_link)
        try:
            recruiting_rating = scrape_recruiting(info[0], info[1])
        except:
            recruiting_rating = ["https://www.tennisrecruiting.net/img/record.gif","?","?"]
        if "0star" in recruiting_rating[0]:
            recruiting_rating[0] = "0 Star"
        elif "1star" in recruiting_rating[0]:
            recruiting_rating[0] = "1 Star"
        elif "2star" in recruiting_rating[0]:
            recruiting_rating[0] = "2 Star"
        elif "3star" in recruiting_rating[0]:
            recruiting_rating[0] = "3 Star"
        elif "4star" in recruiting_rating[0]:
            recruiting_rating[0] = "4 Star"
        elif "5star" in recruiting_rating[0]:
            recruiting_rating[0] = "5 Star"
        elif "6star" in recruiting_rating[0]:
            recruiting_rating[0] = "Blue Chip"
        else:
            recruiting_rating[0] = "????????"
        return {
            "Name": info[0],
            "Location": info[1],
            "District": info[2],
            "WTN": info[3],
            "Points": info[4],
            "Ranking": info[5],
            "Recruiting": recruiting_rating[0],
            "Class": recruiting_rating[2],
            "UTR": recruiting_rating[1],
        }
    except Exception as e:
        return None

def scrape_tournament_data(tournament_url, age_group, sort):
    start = datetime.now()
    driver = setup_driver()
    tournament_url = tournament_url.lower()
    driver.get(tournament_url)
    name = driver.find_element(By.XPATH, "//*[@id='tournaments']/div/div/div/div[1]/div/div[1]/h1").text
    driver.quit()  # Close the driver
    draw_size_str = scrape_draw_size(tournament_url.replace("overview", "events"), age_group)
    draw_size = 10000 if draw_size_str == "N/A" else int(draw_size_str)
    driver = setup_driver()
    driver.get(tournament_url.replace("overview", "players"))
    
    # Initialize player_links as an empty list
    player_links = []

    # Find all players in the tournament
    players = BeautifulSoup(driver.page_source, 'lxml').find_all("td", class_="_alignLeft_1nqit_268")
    time = datetime.now()

    # Extract player links based on age group and gender
    for i in range(0, len(players), 2):  # Iterate every 2nd element for name and age group
        if age_group in players[i + 1].text and "Boys" in players[i + 1].text and "Singles" in players[i + 1].text:
            link = players[i].find("a")
            if link and link.get('href'): player_links.append(link.get('href'))
    
    driver.quit()  # Close the driver

    # Check if any player links were found
    if not player_links:
        print("No player links found. Exiting.")
        return  # Exit the function if no players are found

    print("Found",len(player_links) - 1,"players. Starting information search...")

    # Use ThreadPoolExecutor for parallel scraping
    with ThreadPoolExecutor(max_workers=15) as executor: player_data = list(executor.map(scrape_player, player_links))

    # Filter out None results (in case of scraping errors)
    player_data = [data for data in player_data if data is not None]

    # Initialize player_data_sorted with a default value
    player_data_sorted = player_data

    sort_type = "sigma"
    
    # Fix sorting logic for player data
    if sort == 1:  # Sort by Points
        sort_type = "points"
        player_data_sorted = sorted(
            player_data,
            key=lambda x: float(x["Points"].replace(",", "")) if x["Points"].replace(",", "").isdigit() else 0,
            reverse=True,
        )
    elif sort == 2:  # Sort by WTN
        sort_type = "wtn"
        def parse_wtn(wtn_str):
            try: return float(wtn_str)  # Convert WTN to a float directly
            except ValueError: return 40.0  # Default WTN if conversion fails
        player_data_sorted = sorted(player_data, key=lambda x: parse_wtn(x["WTN"]))

    print("Completed. Analyzing data...")
        
    # Initialize data for Plotly table
    names, locations, districts, seeds, wtns, points, rankings, recruiting, year, utr = [], [], [], [], [], [], [], [], [], []
    row_colors = []  # List to hold row colors

    counts = 0

    for player in player_data_sorted:
        if player and isinstance(player, dict):  # Ensure player is not None and is a dictionary

            # Format points if they are numeric
            try: player["Points"] = f'{int(player["Points"]):,}'  # Format as integer with commas
            except (ValueError, TypeError, KeyError):  player["Points"] = "0"

            # Format ranking if it is numeric
            try: player["Ranking"] = f'{int(player["Ranking"]):,}'  # Format as integer with commas
            except (ValueError, TypeError, KeyError): player["Ranking"] = "20,000"

            # Append data to lists
            names.append(player.get("Name", "Unknown"))
            locations.append(player.get("Location", "Unknown"))
            districts.append(player.get("District", "Unknown"))
            wtns.append(player.get("WTN", "N/A"))
            points.append(player["Points"])
            rankings.append(player["Ranking"])
            recruiting.append(player["Recruiting"])
            year.append(player["Class"])
            utr.append(player["UTR"])

            # Set row color based on draw size
            if int(counts) > int(draw_size) - 1: row_colors.append('lightcoral')
            else: row_colors.append('white')

            counts += 1

    seeds2 = []
    seeds = []
    n = 0
    x = min(int(draw_size),len(player_links))
    while pow(2,n) <= x: n += 1
    n = pow(2,n - 2)
    for i in wtns[:x]: seeds2.append(i)
    seeds2.sort()
    seeds2 = seeds2[0:n]
    for i in wtns[:x]:
        if i in seeds2: seeds.append(seeds2.index(i) + 1)
        else: seeds.append("-")
    # Pad seeds to match total players
    while len(seeds) < len(names): seeds.append("-")


    today_str = datetime.today().strftime("%Y-%m-%d")
    safe_name = "".join(c if c.isalnum() or c in " -" else "-" for c in name)  # Sanitize filename

    
    filename = f"{safe_name}_{today_str}_{sort_type}.pdf"
    pdf_dir = "C:/Users/mohit/Downloads"
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, filename)

    # Build PDF report
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()

    # Add tournament name as title
    elements.append(Paragraph(f"<b>{name}</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    # Construct table data
    table_data = [
        ["No", "Name", "Location", "District", "Seed", "WTN", "Points", "Ranking", "Recruiting", "Grade", "UTR"]
    ]
    for i in range(len(names)):
        row = [
            str(i + 1),
            names[i],
            locations[i],
            districts[i],
            str(seeds[i]),
            wtns[i],
            points[i],
            rankings[i],
            recruiting[i],
            year[i],
            utr[i]
        ]
        table_data.append(row)

    # Create the table
    table = Table(table_data, repeatRows=1)
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ])

    # Apply red background to rows outside draw size
    for idx in range(1, len(table_data)):
        if idx > int(draw_size):
            table_style.add('BACKGROUND', (0, idx), (-1, idx), colors.lightcoral)
    table.setStyle(table_style)
    
    # Step 1: Count UTRs using a dictionary
    from collections import defaultdict
    import re

    utr_counter = defaultdict(int)
    utr_placeholders = set()

    for u in utr:
        u = u.strip()
        if u == "?":
            key = "? UTR"
        elif re.match(r"^\d+\.xx$", u):
            key = u.split('.')[0] + ".0"
            utr_placeholders.add(key)  # Remember this was a ".xx"
        else:
            key = u
        utr_counter[key] += 1

    # Sorting numerically
    def sort_key(k):
        try: return float(k)
        except ValueError: return float('inf')

    utrs_sorted = sorted(utr_counter.items(), key=lambda x: sort_key(x[0]))

    # Build the summary
    utr_summary_lines = []
    total = len(utr)
    for utr_val, count in utrs_sorted:
        display_val = f"{utr_val.split('.')[0]}.xx" if utr_val in utr_placeholders else utr_val
        pct = round(100 * count / total, 2)
        if count == 1:
            utr_summary_lines.append(
                f" - There is <b>{count}</b> UTR rated <b>{display_val}</b> in this tournament (<b>{pct}%</b>)."
            )
        else:
            utr_summary_lines.append(
                f" - There are <b>{count}</b> UTRs rated <b>{display_val}</b> in this tournament (<b>{pct}%</b>)."
            )

    utr_summary_text = "<br/>".join(utr_summary_lines)

    # Create and add UTR summary BEFORE table
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(utr_summary_text, styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey, spaceBefore=12, spaceAfter=12, dash=3))

    # THEN append the table
    elements.append(table)

    # Build the PDF
    doc.build(elements)
    print(f"PDF saved to: {pdf_path}")

    # Open the PDF in the system's default viewer
    try:
        if platform.system() == 'Windows': os.startfile(pdf_path)
        elif platform.system() == 'Darwin': subprocess.call(['open', pdf_path])
        else: subprocess.call(['xdg-open', pdf_path])
    except Exception as e: print("Could not open PDF automatically:", e)
    
tournament_link = input("Enter the tournament link: ")
age_options = age_groups(tournament_link)
for i in age_options:
    print(str(age_options.index(i) + 1) + ". " + i)
age_group = age_options[int(input("Enter the number for your selected age group: ")) - 1]
for i in ["1. Points", "2. WTN"]:
    print(i)
sort = int(input("Choose a sort: "))
scrape_tournament_data(tournament_link.lower(), age_group, sort)
