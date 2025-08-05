from tkinter import filedialog, ttk
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import os
import platform
import subprocess
import tempfile
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, HRFlowable
from concurrent.futures import ThreadPoolExecutor
import time
# CHANGE 1: Import async_playwright
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests
from datetime import date, datetime
import json
from collections import defaultdict
from playwright.sync_api import sync_playwright
import re
import asyncio # Import asyncio

# ---
## Playwright Setup and Teardown

# CHANGE 2: Make setup_browser an async function
def setup_browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        return browser, page

# CHANGE 3: Make setup_page an async function
def setup_page():
    """Create a new page with proper context"""
    playwright, browser, context = setup_browser()
    page = context.new_page()
    return playwright, browser, context, page

# No change needed for close_browser as it doesn't await anything
def close_browser(playwright, browser, context):
    """Properly close browser and playwright"""
    context.close()
    browser.close()
    playwright.stop()

def setup_persistent_browser(user_data_dir="userdata"):
    with sync_playwright() as p:
        # Launch persistent context (acts like a real browser profile)
        browser = p.chromium.launch_persistent_context(user_data_dir, headless=True)
        page = browser.new_page()
        page.goto("https://playtennis.usta.com")
        
        # Wait for any manual login or session setup, if needed
        input("Press Enter after logging in...")  # Optional
        # Do your scraping
        print(page.title())
        
        # Close the browser when done
        browser.close()


# ---
## Web Scraping Functions

# CHANGE 4: Make age_groups an async function
def age_groups(link):
    playwright, browser, context, page = setup_page()
    try:
        page.goto(link.lower())
        page.wait_for_selector("tbody.MuiTableBody-root.css-y6j1my", timeout=10000)

        content = page.content()
        soup = BeautifulSoup(content, 'lxml')
        tbody = soup.find("tbody", class_="MuiTableBody-root css-y6j1my")
        if tbody:
            groups = [h6.text for h6 in tbody.find_all("h6")]
        else:
            groups = []
        return groups
    finally:
        close_browser(playwright, browser, context)

# CHANGE 5: Make scrape_usta an async function
def scrape_usta(player_link, age_group_param=None):
    player_id = player_link.strip("https://www.usta.com/en/home/play/player-search/profile.html#uaid=")
    playwright, browser, context, page = setup_page()

    try:
        page.goto(player_link + "&tab=about")
        page.wait_for_selector(".readonly-text__text", timeout=10000)

        # Fetch player name
        try:
            player_name_element = page.wait_for_selector("/html/body/div[5]/div/div[2]/div/div/div[3]/div/div/div[1]/div/div/div[2]/div/form/div[2]/div/div/div/div/div/div/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div/div/span/h3", timeout=10000)
            player_name = player_name_element.inner_text() if player_name_element else "Unknown Player"
        except:
            player_name = "Unknown Player"

        # Get player location and district
        content = page.content()
        soup = BeautifulSoup(content, 'lxml')

        try:
            content_divs = soup.find_all("div", class_="readonly-text__content")
            if len(content_divs) > 1 and content_divs[1] and hasattr(content_divs[1], 'text'):
                text_parts = content_divs[1].text.split('|')
                if len(text_parts) > 1:
                    location = text_parts[1].split('Section:')[0]
                else:
                    location = "Unknown"
            else:
                location = "Unknown"
        except (AttributeError, IndexError):
            location = "Unknown"

        try:
            content_divs = soup.find_all("div", class_="readonly-text__content")
            if len(content_divs) > 1 and content_divs[1] and hasattr(content_divs[1], 'text'):
                text_parts = content_divs[1].text.split("|")
                if len(text_parts) > 2:
                    district_parts = text_parts[2].split(": ")
                    if len(district_parts) > 1:
                        district = district_parts[1]
                    else:
                        district = "Unknown"
                else:
                    district = "Unknown"
            else:
                district = "Unknown"
        except (AttributeError, IndexError):
            district = "Unknown"

        # Get WTN (World Tennis Number)
        try:
            wtn_element = page.wait_for_selector("/html/body/div[5]/div/div[2]/div/div/div[3]/div/div/div[2]/div/div[3]/div/div/div/div[2]/div/form/div[3]/div/div/div/div[1]/div/div[2]/div[1]/div/p", timeout=10000)
            wtn = wtn_element.inner_text()
        except:
            wtn = "40.00"  # Default WTN if not available

        # Get ranking and points
        page.goto(player_link + "&tab=rankings")
        content = page.content()
        soup = BeautifulSoup(content, 'lxml')
        ranking_info = soup.find_all("div", class_="v-grid-cell__content")

        points = "0"  # Default points if not available
        rank = "20000"  # Default rank if not available

        try:
            if age_group_param:
                for j in range(0, len(ranking_info), 5):
                    if "National Standings List (combined)" in ranking_info[j].text:
                        if age_group_param.split()[1] in ranking_info[j].text:
                            points = ranking_info[j + 1].text.strip("\n") if j + 1 < len(ranking_info) else "0"
                            rank = ranking_info[j + 2].text.strip("\n") if j + 2 < len(ranking_info) else "20,000"
                            break
        except:
            points = "0"
            rank = "20,000"

        return(player_name, location, district, wtn, points, rank)

    finally:
        close_browser(playwright, browser, context)

# CHANGE 6: Make scrape_recruiting an async function
def scrape_recruiting(name, location):
    playwright, browser, context, page = setup_page()

    try:
        page.goto("https://www.tennisrecruiting.net/player.asp")
        page.fill("input[name='f_playername']", name)
        page.press("input[name='f_playername']", "Enter")

        grades = ["Graduate","Senior","Junior","Sophomore","Freshman","8th Grader","7th Grader","6th Grader"]

        rating = None
        utr_text = "?"
        year_text = "?"

        try:
            # Wait until the rating image is loaded
            rating = page.wait_for_selector("//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[4]/td/img", timeout=10000)

            try:
                utr = page.wait_for_selector("//a[contains(@href, 'app.utrsports.net')]", timeout=10000)
                utr_text = utr.inner_text() if utr else "?"
            except:
                utr_text = "?"

            try:
                year = page.wait_for_selector("//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[3]/td[2]/div[3]", timeout=10000)
                year_text = year.inner_text() if year else "?"
                if "Provisional" in year_text:
                    for grade in grades:
                        if grade in year_text:
                            year_text = grade
                            break
                    year_text = year_text + "?"
                else:
                    for grade in grades:
                        if grade in year_text:
                            year_text = grade
                            break
            except:
                year_text = "?"

        except:
            content = page.content()
            soup = BeautifulSoup(content, 'lxml')
            table = soup.find("table", class_="list")
            if table:
                players = table.find_all("tr")
                links = []
                homes = []

                for i in players[1:]:
                    if hasattr(i, 'find_all'):
                        td_elements = i.find_all("td")
                        if len(td_elements) >= 3:
                            link_element = td_elements[0].find("b") if hasattr(td_elements[0], 'find') else None
                            if link_element and hasattr(link_element, 'find'):
                                a_element = link_element.find("a")
                                if a_element and hasattr(a_element, 'get'):
                                    href = a_element.get("href")
                                    if href:
                                        links.append(href)
                                        homes.append(td_elements[1].text + ", " + td_elements[2].text)

                for i, home in enumerate(homes):
                    if home == location and i < len(links):
                        page.goto("https://www.tennisrecruiting.net" + links[i])

                        # Wait until the rating image is loaded in the second page
                        try:
                            rating = page.wait_for_selector("//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[4]/td/img", timeout=10000)
                        except:
                            rating = None

                        try:
                            utr = page.wait_for_selector("//a[contains(@href, 'app.utrsports.net')]", timeout=10000)
                            utr_text = utr.inner_text() if utr else "?"
                        except:
                            utr_text = "?"

                        try:
                            year = page.wait_for_selector("//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[3]/td[2]/div[3]", timeout=10000)
                            year_text = year.inner_text() if year else "?"
                            if "Provisional" in year_text:
                                for grade in grades:
                                    if grade in year_text:
                                        year_text = grade
                                        break
                                year_text = year_text + "?"
                            else:
                                for grade in grades:
                                    if grade in year_text:
                                        year_text = grade
                                        break
                        except:
                            year_text = "?"
                        break

        return([rating.get_attribute("src") if rating else "?", utr_text, year_text])

    finally:
        close_browser(playwright, browser, context)

# CHANGE 7: Make scrape_draw_size an async function
def scrape_draw_size(link, age_group):
    playwright, browser, context, page = setup_page()

    try:
        page.goto(link)
        content = page.content()
        soup = BeautifulSoup(content, 'lxml')

        age_groups = soup.find_all("h6", class_="_H6_1iwqn_128")
        links = soup.find_all("a", class_="_link_19t7t_285")
        groups_final = []

        for i in age_groups:
            groups_final.append(i.text)

        if groups_final and age_group in groups_final and links:
            index = groups_final.index(age_group) - 1
            if 0 <= index < len(links):
                link_href = links[index].get("href")
                link_final = "https://playtennis.usta.com" + (link_href if link_href else "")
                page.goto(link_final)
                asyncio.sleep(5) # Use asyncio.sleep for async functions

                content = page.content()
                soup = BeautifulSoup(content, 'lxml')
                draw_size = soup.find_all("span", class_="_bodyXSmall_1iwqn_137")

                if len(draw_size) > 1:
                    return(draw_size[1].text)

        return "N/A"

    finally:
        close_browser(playwright, browser, context)

# CHANGE 8: Make scrape_player an async function
def scrape_player(player_link, age_group_param=None):
    """
    Scrape individual player data.
    """
    try:
        info = scrape_usta(player_link, age_group_param)
        try:
            recruiting_rating = scrape_recruiting(info[0], info[1])
        except:
            recruiting_rating = ["?","?","?"]

        if "0star" in recruiting_rating[0]: recruiting_rating[0] = "0 Star"
        elif "1star" in recruiting_rating[0]: recruiting_rating[0] = "1 Star"
        elif "2star" in recruiting_rating[0]: recruiting_rating[0] = "2 Star"
        elif "3star" in recruiting_rating[0]: recruiting_rating[0] = "3 Star"
        elif "4star" in recruiting_rating[0]: recruiting_rating[0] = "4 Star"
        elif "5star" in recruiting_rating[0]: recruiting_rating[0] = "5 Star"
        elif "6star" in recruiting_rating[0]: recruiting_rating[0] = "Blue Chip"
        else: recruiting_rating[0] = "????????"

        return {
            "Name": info[0],
            "Location": info[1],
            "District": info[2],
            "WTN": info[3],
            "Points": info[4],
            "Ranking": info[5],
            "Recruiting": recruiting_rating[0],
            "Class": recruiting_rating[2],
            "UTR": recruiting_rating[1]
        }
    except Exception as e:
        print(f"Error scraping player {player_link}: {e}")
        return None

# ---
## Tournament Data Scraping and PDF Generation

# CHANGE 9: Make scrape_tournament_data an async function
def scrape_tournament_data(tournament_url, age_group, sort):
    start = datetime.now()
    playwright, browser, context, page = setup_page()

    try:
        tournament_url = tournament_url.lower()
        page.goto(tournament_url)

        try:
            name_element = page.wait_for_selector("//*[@id='tournaments']/div/div/div/div[1]/div/div[1]/h1", timeout=10000)
            name = name_element.inner_text() if name_element else "Unknown Tournament"
        except:
            name = "Unknown Tournament"

        draw_size_str = scrape_draw_size(tournament_url.replace("overview", "events"), age_group)
        draw_size = 10000 if draw_size_str == "N/A" else int(draw_size_str)

        page.goto(tournament_url.replace("overview", "players"))

        # Initialize player_links as an empty list
        player_links = []

        # Find all players in the tournament
        content = page.content()
        soup = BeautifulSoup(content, 'lxml')
        players = soup.find_all("td", class_="_alignLeft_1nqit_268")
        time_now = datetime.now()

        # Extract player links based on age group and gender
        for i in range(0, len(players), 2):  # Iterate every 2nd element for name and age group
            if (i + 1 < len(players) and
                hasattr(players[i + 1], 'text') and
                age_group in players[i + 1].text and
                "Boys" in players[i + 1].text and
                "Singles" in players[i + 1].text):

                if hasattr(players[i], 'find'):
                    link = players[i].find("a")
                    if link and hasattr(link, 'get'):
                        href = link.get('href')
                        if href:
                            player_links.append(href)

        # Check if any player links were found
        if not player_links:
            print("No player links found. Exiting.")
            return  # Exit the function if no players are found

        print("Found",len(player_links),"players. Starting information search...")

        # Use asyncio.gather for parallel asynchronous scraping
        # You would typically use asyncio.gather for async functions, not ThreadPoolExecutor directly.
        # Since scrape_player is now async, we'll use asyncio.gather.
        player_data = asyncio.gather(*(scrape_player(link, age_group) for link in player_links))


        # Filter out None results (in case of scraping errors)
        player_data = [data for data in player_data if data is not None]

        # Initialize player_data_sorted with a default value
        player_data_sorted = player_data

        sort_type = ""

        # Fix sorting logic for player data
        if sort == 1:  # Sort by Points
            sort_type = "points"
            player_data_sorted = sorted(
                player_data,
                key=lambda x: float(x["Points"].replace(",", "")) if x["Points"].replace(",", "").replace(".", "").isdigit() else 0,
                reverse=True,
            )
        elif sort == 2:  # Sort by WTN
            sort_type = "wtn"
            def parse_wtn(wtn_str):
                try:
                    return float(wtn_str)  # Convert WTN to a float directly
                except ValueError:
                    return 40.0  # Default WTN if conversion fails
            player_data_sorted = sorted(player_data, key=lambda x: parse_wtn(x["WTN"]))

        print("Completed. Analyzing data...")

        # Initialize data for Plotly table
        names, locations, districts, seeds, wtns, points, rankings, recruiting, year, utr = [], [], [], [], [], [], [], [], [], []
        row_colors = []  # List to hold row colors

        counts = 0

        for player in player_data_sorted:
            if player and isinstance(player, dict):  # Ensure player is not None and is a dictionary

                # Format points if they are numeric
                try:
                    player["Points"] = f'{int(player["Points"]):,}'  # Format as integer with commas
                except (ValueError, TypeError, KeyError):
                    player["Points"] = "0"

                # Format ranking if it is numeric
                try:
                    player["Ranking"] = f'{int(player["Ranking"]):,}'  # Format as integer with commas
                except (ValueError, TypeError, KeyError):
                    player["Ranking"] = "20,000"

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
                if int(counts) > int(draw_size) - 1:
                    row_colors.append('lightcoral')
                else:
                    row_colors.append('white')

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
            try:
                return float(k)
            except ValueError:
                return float('inf')

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
            if platform.system() == 'Windows':
                subprocess.call(('start', pdf_path), shell=True)
            elif platform.system() == 'Darwin':
                subprocess.call(['open', pdf_path])
            else:
                subprocess.call(['xdg-open', pdf_path])
        except Exception as e:
            print("Could not open PDF automatically:", e)

    finally:
        close_browser(playwright, browser, context)

# ---
## Main Execution Block

# CHANGE 10: Run the main function using asyncio.run
def main():
    tournament_link = input("Enter the tournament link: ")
    options = age_groups(tournament_link) # Await the async function call
    for i in options:
        print(str(options.index(i) + 1) + ". " + i)
    age_group = options[int(input("Enter the number for your selected age group: ")) - 1]
    for i in ["1. Points", "2. WTN"]:
        print(i)
    sort = int(input("Choose a sort: "))
    scrape_tournament_data(tournament_link.lower(), age_group, sort) # Await the async function call

if __name__ == "__main__":
    main()
