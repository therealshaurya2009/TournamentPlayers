#Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

#ReportLab Imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import HRFlowable
from reportlab.platypus import Paragraph
from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Spacer
from reportlab.platypus import Table
from reportlab.platypus import TableStyle

#Other Imports
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import platform
import re
import requests
import subprocess
import time
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver():
    driver_options = Options()
    driver_options.add_argument("--headless=new")
    driver_options.add_argument("--disable-gpu")
    driver_options.add_argument("--window-size=1920,1080")
    driver_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    driver_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver_options.add_experimental_option('useAutomationExtension', False)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=driver_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def age_groups_level(tournament_link):
    driver = setup_driver()
    driver.get(tournament_link.lower())

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "_H6_1iwqn_128")))
        age_groups = driver.find_elements(By.CLASS_NAME, "_H6_1iwqn_128")
        level_xpath = "/html/body/div[4]/div/div/div[2]/div[3]/div[1]/div[2]/div[2]/div/div/div[1]/div/div/div[1]/h6"
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, level_xpath)))
        level = driver.find_element(By.XPATH, level_xpath)
        continue_age = False
        if level.text in ["Level 7", "Level 6"]:
            continue_age = True
        age_groups_final = []
        for group in age_groups[1:]:
            age_groups_final.append(group.text)
        return [level.text, continue_age, age_groups_final]
    except Exception as e:
        return []


def parse_wtn(wtn_str):
    try:
        return float(wtn_str)
    except ValueError:
        return 40.0


def sort_key(k):
    try:
        return float(k)
    except ValueError:
        return float('inf')


def scrape_recruiting(name, location, driver):
    driver.get("https://www.tennisrecruiting.net/player.asp")

    player_grades = ["Graduate","Senior","Junior","Sophomore","Freshman","8th Grader","7th Grader","6th Grader"]
    player_rating_xpath = "//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[4]/td/img"
    player_utr_xpath = "//a[contains(@href, 'app.utrsports.net')]"
    player_year_xpath = "//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[3]/td[2]/div[3]"
            
    player_name = driver.find_element(By.NAME, "f_playername")
    player_name.send_keys(name)
    player_name.send_keys(Keys.RETURN)
    
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, player_rating_xpath)))
        player_rating = driver.find_element(By.XPATH, player_rating_xpath)

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, player_utr_xpath)))
            
            player_utr = driver.find_element(By.XPATH, player_utr_xpath)
        except:
            player_utr = "?"

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, player_year_xpath)))
            player_year = driver.find_element(By.XPATH, player_year_xpath)
            player_year = player_year.text
            for grade in player_grades:
                if grade in player_year:
                    player_year = grade
                    if "Provisional" in player_year:
                        player_year = player_year + "?"
                    break
        except:
            player_year = "?"

    except:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "_players_1nqit_161")))
        players = driver.find_element(By.CLASS_NAME, "_players_1nqit_161").find_all("tr")
        players_links = []
        players_homes = []
        for i in players[1:]:
            players_links.append(i.find_all("td")[0].find("b").find("a").get("href"))
            players_homes.append(i.find_all("td")[1].text + ", " + i.find_all("td")[2].text)
        for i in player_homes:
            if i == location:
                driver.get("https://www.tennisrecruiting.net" + links[homes.index(i)])
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, player_rating_xpath)))
                player_rating = driver.find_element(By.XPATH, player_rating_xpath)
                
                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, player_utr_xpath)))
                    player_utr = driver.find_element(By.XPATH, player_utr_xpath)
                    
                except:
                    player_utr = "?"

                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, player_year_xpath)))
                    player_year = driver.find_element(By.XPATH, player_year_xpath)
                    player_year = player_year.text
                    for grade in player_grades:
                        if grade in player_year:
                            player_year = grade
                            if "Provisional" in player_year:
                                player_year = player_year + "?"
                            break
                except:
                    player_year = "?"
    
    return([player_rating.get_attribute("src"),player_utr.text,player_year])


def scrape_usta(player_link):
    driver = setup_driver()
    driver.get(player_link + "&tab=about")

    try:
        player_name_xpath = "/html/body/div[5]/div/div[2]/div/div/div[3]/div/div/div[1]/div/div/div[2]/div/form/div[2]/div/div/div/div/div/div/div[2]/div/div/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div/div/span/h3"
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, player_name_xpath)))
        
        player_name = driver.find_element(By.XPATH, player_name_xpath)
        player_name = player_name.text.strip("\n")
    except:
         player_name = "*Unknown Player*"

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "readonly-text__content")))
        
        player_location = driver.find_elements(By.CLASS_NAME, "readonly-text__content")[1]
        player_location = player_location.text.split('|')[1].split('Section:')[0]
        player_location = player_location.strip("\n")
    except:
        player_location = "*Unknown*"

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "readonly-text__content")))
        
        player_district = driver.find_elements(By.CLASS_NAME, "readonly-text__content")[1]
        player_district = player_district.text.split("|")[2].split(": ")[1]
    except:
        player_district = "Unknown"

    try:
        player_wtn_xpath = "/html/body/div[5]/div/div[2]/div/div/div[3]/div/div/div[2]/div/div/div[2]/div/div[3]/div/div/div/div[2]/div/form/div[3]/div/div/div/div[1]/div/div[2]/div[1]/div/p"
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, player_wtn_xpath)))
        
        player_wtn = driver.find_element(By.XPATH, player_wtn_xpath).text
    except:
        player_wtn = "*40.00*"

    driver.get(player_link + "&tab=rankings")
    
    player_points = "0"  
    player_rank = "20000"

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "v-grid-cell__content")))
        
        player_ranking_info = driver.find_elements(By.CLASS_NAME, "v-grid-cell__content")    
        for player in range(0, len(player_ranking_info), 5):
            if "National Standings List (combined)" in player_ranking_info[player].text:
                if age_group.split()[1] in player_ranking_info[player].text:
                    player_points = player_ranking_info[player + 1].text.strip("\n") if player + 1 < len(player_ranking_info) else "0"
                    player_rank = player_ranking_info[player + 2].text.strip("\n") if player + 2 < len(player_ranking_info) else "20,000"
                    break
    except:
        player_points = "*0*"
        player_rank = "*20,000*"

    try:
        recruiting_rating = scrape_recruiting(player_name, player_location, driver)
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

    driver.quit()

    return([player_name, player_location, player_district, player_wtn, player_points, player_rank, recruiting_rating[0], recruiting_rating[1], recruiting_rating[2]])


def scrape_draw_size(link, selected_age_group):
    driver = setup_driver()
    driver.get(link)

    tournament_groups_final = []
    
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "_H6_1iwqn_128")))
    
    tournament_age_groups = driver.find_elements(By.CLASS_NAME, "_H6_1iwqn_128")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "_link_19t7t_285")))
    
    links = driver.find_elements(By.CLASS_NAME, "_link_19t7t_285")
    
    for age_group in tournament_age_groups:
        tournament_groups_final.append(age_group.text)

    tournament_link_final = links[tournament_groups_final.index(selected_age_group) - 1]
    tournament_link_final = tournament_link_final.get_attribute("href")
    driver.get(tournament_link_final)

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "_bodyXSmall_1iwqn_137")))
    
    tournament_draw_temp = driver.find_elements(By.CLASS_NAME, "_bodyXSmall_1iwqn_137")
    try:
        tournament_draw_size = int(tournament_draw_temp[1].text)
    except:
        tournament_draw_size = 100000
        
    sort_type = tournament_draw_temp[5].text
    if "ranking" in sort_type.lower():
        sort_type = 1
    elif "wtn" in sort_type.lower():
        sort_type = 2
    elif "manual" in sort_type.lower():
        sort_type = 0
    elif ("n/a" == sort_type.lower()) or ("first" in sort_type.lower()):
        print("1.Points\n2.WTN")
        sort_type = str(input("Choose a selection type: "))
        if sort_type == "1":
            sort_type = 1
        elif sort_type == "2":
            sort_type = 2
    
    return([tournament_draw_size, sort_type])

    
def scrape_player(player_link):
    try:
        player_info = scrape_usta(player_link)
        return {
            "Name": player_info[0],
            "Location": player_info[1],
            "District": player_info[2],
            "WTN": player_info[3],
            "Points": player_info[4],
            "Ranking": player_info[5],
            "Recruiting": player_info[6],
            "Class": player_info[8],
            "UTR": player_info[7],
        }
    except Exception as e:
        return None

def sort_players(player_data, tournament_level, sort):
    if "Level 7" in tournament_level:
        if sort == 1:
            sort_type = "points"
            player_data = sorted(player_data,key=lambda x: float(x["Points"].replace(",", "")) if x["Points"].replace(",", "").isdigit() else 0)
        elif sort == 2:
            sort_type = "wtn"
            player_data = sorted(player_data, key=lambda x: parse_wtn(x["WTN"]), reverse=True)
    elif "Level 6" in tournament_level:
        if sort == 1:
            sort_type = "points"
            player_data = sorted(player_data,key=lambda x: float(x["Points"].replace(",", "")) if x["Points"].replace(",", "").isdigit() else 0, reverse=True)
        elif sort == 2:
            sort_type = "wtn"
            player_data = sorted(player_data, key=lambda x: parse_wtn(x["WTN"]))
    else:
        sort_type = "mixed"
        player_data = sorted(player_data,key=lambda x: float(x["Points"].replace(",", "")) if x["Points"].replace(",", "").isdigit() else 0, reverse=True)    

    return [player_data, sort_type] 


def scrape_tournament_data(tournament_url, age_group, draw_size, sort, tournament_level):
    driver = setup_driver()
    tournament_url = tournament_url.lower()
    driver.get(tournament_url)
    tournament_name = driver.find_element(By.XPATH, "//*[@id='tournaments']/div/div/div/div[1]/div/div[1]/h1").text

    driver.get(tournament_url.replace("overview", "players"))
    player_links = []

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "_alignLeft_1nqit_268")))
    players_list = driver.find_elements(By.CLASS_NAME, "_alignLeft_1nqit_268")

    for player_row in players_list:
        if age_group in player_row.text:
            link = players_list[players_list.index(player_row) - 1].find_element(By.TAG_NAME, "a")
            link = link.get_attribute('href')
            player_links.append(link)


    if not player_links:
        print("No player links found. Exiting.")
        return

    print("Found",len(player_links),"players. Starting information search...")
    with ThreadPoolExecutor(max_workers=5) as executor: player_data = list(executor.map(scrape_player, player_links))

    player_data = [data for data in player_data if data is not None]
    
    player_data = sort_players(player_data, tournament_level, sort)
    sort_type = player_data[1]
    player_data = player_data[0]
      
    print("Completed. Analyzing data...")
    driver.quit()

    player_names = []
    player_locations = []
    player_districts = []
    player_seeds = []
    player_wtns = []
    player_points = []
    player_rankings = []
    player_recruiting = []
    player_year = []
    player_utr = []
    row_colors = []
    counts = 0
    
    for player in player_data:
        if player and isinstance(player, dict):

            try:
                player["Points"] = f'{int(player["Points"]):,}'
            except (ValueError, TypeError, KeyError):
                player["Points"] = "0"

            try:
                player["Ranking"] = f'{int(player["Ranking"]):,}'
            except (ValueError, TypeError, KeyError):
                player["Ranking"] = "20,000"

            player_names.append(player.get("Name", "Unknown"))
            player_locations.append(player.get("Location", "Unknown"))
            player_districts.append(player.get("District", "Unknown"))
            player_wtns.append(player.get("WTN", "N/A"))
            player_points.append(player["Points"])
            player_rankings.append(player["Ranking"])
            player_recruiting.append(player["Recruiting"])
            player_year.append(player["Class"])
            player_utr.append(player["UTR"])
            if int(counts) > int(draw_size) - 1:
                row_colors.append('lightcoral')
            else:
                row_colors.append('white')
            counts += 1
            
    seeds_temp = []
    seeds_final = []
    num_seeds = 0
    total_players = min(int(draw_size),len(player_links))

    while pow(2,num_seeds) <= total_players:
        num_seeds += 1
    num_seeds = pow(2,num_seeds - 2)

    for i in player_wtns[:total_players]:
        seeds_temp.append(i)

    seeds_temp.sort()
    seeds_temp = seeds_temp[0:num_seeds]
    
    for i in player_wtns[:total_players]:
        if i in seeds_temp:
            seeds_final.append(seeds_temp.index(i) + 1)
        else:
            seeds_final.append("-")
            
    while len(seeds_final) < len(player_names):
        seeds_final.append("-")
    
    today_str = datetime.today().strftime("%Y-%m-%d")
    safe_name = "".join(c if c.isalnum() or c in " -" else "-" for c in tournament_name)
    filename = f"{safe_name}_{today_str}_{sort_type}.pdf"
    pdf_dir = os.path.join(os.getcwd(), "static")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, filename)
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter))

    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"<b>{tournament_name}</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    table_data = [["No", "Name", "Location", "District", "Seed", "WTN", "Points", "Ranking", "Recruiting", "Grade", "UTR"]]
    
    for i in range(len(player_names)):
        row = [
            str(i + 1),
            player_names[i],
            player_locations[i],
            player_districts[i],
            str(seeds_final[i]),
            player_wtns[i],
            player_points[i],
            player_rankings[i],
            player_recruiting[i],
            player_year[i],
            player_utr[i]
        ]
        table_data.append(row)
        
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
    
    for idx in range(1, len(table_data)):
        if idx > int(draw_size):
            table_style.add('BACKGROUND', (0, idx), (-1, idx), colors.lightcoral)

    table.setStyle(table_style)
    utr_counter = defaultdict(int)
    utr_placeholders = set()
    
    for each_utr in player_utr:
        each_utr = each_utr.strip()
        
        if each_utr == "?":
            key = "? UTR"
        elif re.match(r"^\d+\.xx$", each_utr):
            key = each_utr.split('.')[0] + ".0"
            utr_placeholders.add(key)
        else:
            key = each_utr
            
        utr_counter[key] += 1
        
    utrs_sorted = sorted(utr_counter.items(), key=lambda x: sort_key(x[0]))
    utr_summary_lines = []
    total = len(player_utr)
    
    for utr_val, count in utrs_sorted:
        display_val = f"{utr_val.split('.')[0]}.xx" if utr_val in utr_placeholders else utr_val
        pct = round(100 * count / total, 2)

        if count == 1:
            utr_summary_text = f" - There is <b>{count}</b> UTR rated <b>{display_val}</b> in this tournament (<b>{pct}%</b>)."
            utr_summary_lines.append(utr_summary_text)
        else:
            utr_summary_text = f" - There are <b>{count}</b> UTRs rated <b>{display_val}</b> in this tournament (<b>{pct}%</b>)."
            utr_summary_lines.append(utr_summary_text)
            
    utr_summary_text = "<br/>".join(utr_summary_lines)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(utr_summary_text, styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey, spaceBefore=12, spaceAfter=12, dash=3))
    elements.append(table)
    doc.build(elements)
    print(f"PDF saved to: {pdf_path}")
        
def run_tournament_analysis(tournament_url, selected_age_index):
    age_options = age_groups_level(tournament_url)
    if not age_options or len(age_options[2]) < int(selected_age_index):
        raise ValueError("Invalid age group selection.")
    
    age_group = age_options[2][int(selected_age_index) - 1]
    draw_info = scrape_draw_size(tournament_url.replace("overview", "events"), age_group)
    scrape_tournament_data(
        tournament_url.lower(),
        age_group,
        draw_info[0],
        draw_info[1],
        age_options[0]
    )
    today_str = datetime.today().strftime("%Y-%m-%d")
    tournament_name = "".join(c if c.isalnum() or c in " -" else "-" for c in tournament_url.split("/")[-1])
    return f"{tournament_name}_{today_str}_{draw_info[1]}.pdf"
    
