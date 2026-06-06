from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
import nest_asyncio
import streamlit as st
import psutil, signal
import shutil
import sys

# ReportLab Imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Other Imports
from collections import defaultdict
from datetime import datetime
import os
import platform
import random
import re
import requests
import subprocess

# Apply nested asyncio
nest_asyncio.apply()

# --- Session state for browser ---
if "playwright_browser" not in st.session_state:
    st.session_state.playwright_browser = None
if "playwright_page" not in st.session_state:
    st.session_state.playwright_page = None


# Fix for Windows + Playwright async subprocesses
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# Force install if missing
if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright")):
    os.system("playwright install chromium")

wait = int(10000)

async def setup_browser():
    playwright = await async_playwright().start()

    # Try to find system Chrome (adjust path if needed)
    chrome_path = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chrome.exe")
    if not chrome_path:
        chrome_path = playwright.chromium.executable_path

    browser = await playwright.chromium.launch(
        headless=True,  # 👈 headless=False looks more human (set True if you must)
        executable_path=chrome_path,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--start-maximized",
            "--disable-extensions",
            "--disable-default-apps",
            "--no-first-run",
            "--no-service-autorun",
            "--password-store=basic",
            "--use-mock-keychain",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
        ]
    )

    # 🎭 Randomize viewport + user agent for realism
    context = await browser.new_context(
        user_agent=random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_1) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/16.4 Safari/605.1.15",
        ]),
        viewport={
            "width": random.randint(1280, 1920),
            "height": random.randint(720, 1080)
        },
        locale="en-US",
        color_scheme="light",
        timezone_id=random.choice(["America/Chicago", "America/New_York"]),
        permissions=["geolocation"],
        geolocation={"latitude": 41.8781, "longitude": -87.6298},
    )

    page = await context.new_page()

    # 🧩 Hide automation traces
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'permissions', {
            get: () => ({ query: () => Promise.resolve({ state: 'granted' }) })
        });
        window.chrome = { runtime: {} };
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
        );
    """)

    # 🖱️ Optional: random mouse movements to mimic humans
    for _ in range(random.randint(3, 6)):
        await page.mouse.move(random.randint(100, 900), random.randint(100, 600))
        await asyncio.sleep(random.uniform(0.1, 0.3))

    # --- Helper: goto with timeout, wait for selector, then scroll fully ---
    async def goto_full(url: str, wait_for: str = None, timeout: int = wait):
        if not url or not isinstance(url, str):
            raise ValueError(f"Invalid URL passed to goto_full: {url}")

        # Ensure proper scheme
        if url.startswith("/"):
            url = "https://playtennis.usta.com" + url
        elif not url.startswith("http"):
            url = "https://" + url.lstrip("/")

        try:
            await asyncio.wait_for(page.goto(url), timeout=timeout)
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout)

            # 🧭 Smooth scrolling (human-like)
            last_height = 0
            while True:
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight / 2)")
                await asyncio.sleep(random.uniform(0.8, 1.4))
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

        except (asyncio.TimeoutError, PlaywrightTimeoutError) as e:
            print(f"[goto_full] Timeout or navigation error for {url}: {e}")
            try:
                await page.close()
            except:
                pass
            await context.close()
            await browser.close()
            await playwright.stop()
            raise

    page.goto_full = goto_full
    return playwright, browser, context, page

async def age_groups_level(tournament_link, playwright, browser, context, page):
    await page.goto(tournament_link.lower())

    try:
        await page.wait_for_selector("._H6_1iwqn_128", timeout=wait)
        age_groups = await page.locator("._H6_1iwqn_128").all_inner_texts()

        continue_age = age_groups[0] in ["Level 7", "Level 6"]
        age_groups_final = age_groups[1:]

        return [age_groups[0], continue_age, age_groups_final]
    except:
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

async def scrape_usta(player_link, age_group, max_retries: int = 5):
    retries = 0
    playwright, browser, context, page = await setup_browser()
    while retries < max_retries:
        retries += 1
        try:
            await page.goto(player_link + "&tab=about")
            
            try:
                player_name_selector = "span.readonly-text__text > h3"
                await page.wait_for_selector(player_name_selector, timeout=wait)
                locator = page.locator(player_name_selector)
                player_name = await locator.text_content()
                player_name = player_name.strip()
            except:
                player_name = "Unknown Player"

            try:
                await page.wait_for_selector(".readonly-text__content", timeout=wait)
                player_location = await page.locator(".readonly-text__content").nth(1).inner_text()
                player_location = player_location.split('|')[1].split('Section:')[0].strip("\n")
                if "District" in player_location:
                    player_location = "Unknown"
            except:
                player_location = "Unknown"

            try:
                await page.wait_for_selector(".readonly-text__content", timeout=wait)
                player_district = await page.locator(".readonly-text__content").nth(1).inner_text()
                player_district = player_district.split("|")[2].split(": ")[1]
            except:
                player_district = "Unknown"

            try:
                await page.wait_for_selector(".readonly-text__content", timeout=wait)
                player_section = await page.locator(".readonly-text__content").nth(1).inner_text()
                player_section = player_section.split("|")[1].split(": ")[1]
            except:
                player_section = "Unknown"

            try:
                player_wtn_xpath = "/html/body/div[5]/div/div[2]/div/div/div[3]/div/div/div[2]/div/div/div[2]/div/div[3]/div/div/div/div[2]/div/form/div[3]/div/div/div/div[1]/div/div[2]/div[1]/div/p"
                await page.wait_for_selector(f"xpath={player_wtn_xpath}", timeout=wait)
                player_wtn = await page.locator(f"xpath={player_wtn_xpath}").inner_text()
            except:
                player_wtn = "40.00"

            player_points = "0"
            player_rank = "25,000"

            try:
                await page.goto(player_link + "&tab=rankings")
                await page.wait_for_selector(".v-grid-cell__content", timeout=wait)
                player_ranking_info = await page.locator(".v-grid-cell__content").all_inner_texts()  
                player_data = []
                i = 0
                while i < len(player_ranking_info):
                    player_data.append([
                        player_ranking_info[i],
                        player_ranking_info[i + 1],
                        player_ranking_info[i + 2],
                        player_ranking_info[i + 3],
                        player_ranking_info[i + 4]
                    ])
                    i += 5
                for player in player_data:
                    if (age_group.split(" ")[1] + " National Standings List") in player[0]:
                        player_points = player[1]
                        player_rank = player[2]
            except:
                player_points = "0"
                player_rank = "25,000"

            return [
                player_name, player_location, player_district,
                player_wtn, player_points, player_rank, player_section
            ]

        except Exception as e:
            try:
                print("")
            except:
                pass
            if retries >= max_retries:
                return [
                    "Unknown", "Unknown", "Unknown", "40.00", "0", "25,000",
                    "Unknown"
                ]

async def scrape_draw_size(link, selected_age_group):
    playwright, browser, context, page = await setup_browser()
    await page.goto(link)

    tournament_groups_final = []
    await page.wait_for_selector("._H6_1iwqn_128", timeout=wait)
    tournament_age_groups = await page.locator("._H6_1iwqn_128").all_inner_texts()

    await page.wait_for_selector("._link_19t7t_285", timeout=wait)
    links = await page.query_selector_all("._link_19t7t_285")

    for age_group in tournament_age_groups:
        tournament_groups_final.append(age_group)

    tournament_link_final = await links[tournament_groups_final.index(selected_age_group) - 1].get_attribute("href")
    if tournament_link_final and not tournament_link_final.startswith("http"):
        tournament_link_final = "https://playtennis.usta.com" + tournament_link_final
    await page.goto(tournament_link_final)

    await page.wait_for_selector("._bodyXSmall_1iwqn_137", timeout=wait)
    tournament_draw_temp = await page.locator("._bodyXSmall_1iwqn_137").all_inner_texts()

    try:
        tournament_draw_size = int(tournament_draw_temp[1])
    except:
        tournament_draw_size = 100000

    sort_type = tournament_draw_temp[5]
    if "ranking" in sort_type.lower():
        sort_type = 1
    elif "wtn" in sort_type.lower():
        sort_type = 2
    elif "manual" in sort_type.lower():
        sort_type = 1
    elif ("n/a" == sort_type.lower()) or ("first" in sort_type.lower()):
        print("1.Points\n2.WTN")
        sort_type = str(input("Choose a selection type: "))
        if sort_type == "1":
            sort_type = 1
        elif sort_type == "2":
            sort_type = 2

    return [tournament_draw_size, sort_type]


async def scrape_player(player_link, age_group):
    try:
        player_info = await scrape_usta(player_link, age_group)
        return {
            "Name": player_info[0],
            "Profile": player_link,
            "Location": player_info[1],
            "WTN": player_info[3],
            "Points": player_info[4],
            "District": player_info[2],
            "Section": player_info[6],
            "Ranking": player_info[5],
        }
    except:
        return {
            "Name": "Unknown",
            "Profile": "",
            "Location": "Unknown",
            "WTN": "40.00",
            "Points": "0",
            "District": "Unknown",
            "Section": "",
            "Ranking": "25,000",
        }


def sort_players(player_data, tournament_level, sort):
    sort_type = ""
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


async def scrape_tournament_data(tournament_url, age_group, draw_size, sort, tournament_level):
    tournament_url = tournament_url.lower()
    playwright, browser, context, page = await setup_browser()
    await page.goto(tournament_url)
    tournament_name = await page.locator("//*[@id='tournaments']/div/div/div/div[1]/div/div[1]/h1").inner_text()

    await page.goto(tournament_url.replace("overview", "players"))
    await page.wait_for_selector("._alignLeft_1nqit_268", timeout=wait)
    players_list = await page.query_selector_all("._alignLeft_1nqit_268")

    player_links = []
    for player_row in players_list:
        text = await player_row.inner_text()
        if age_group in text:
            link = await players_list[players_list.index(player_row) - 1].query_selector("a")
            href = await link.get_attribute('href')
            player_links.append(href)
    
    if not player_links:
        print("No player links found. Exiting.")
        return

    print("Found", len(player_links), "players. Starting information search...")

    # Create a progress bar in Streamlit
    progress_bar = st.progress(0)
    status_text = st.empty()

    total_players = len(player_links)
    results = []

    # Helper to run tasks in batches
    async def gather_in_batches(tasks, batch_size=10):
        nonlocal results
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)

            # Update progress bar
            progress = min(int((len(results) / total_players) * 100), 100)
            progress_bar.progress(progress)
            status_text.text(f"Completed {len(results)} of {total_players} players...")

        return results

    # Create tasks
    tasks = [scrape_player(link, age_group) for link in player_links]

    # Run tasks in batches
    player_data = await gather_in_batches(tasks, batch_size=10)

    # Finalize progress bar
    progress_bar.progress(100)
    status_text.text("✅ All player data collected!")

    # Filter out failed scrapes
    player_data = [data for data in player_data if data is not None]

    # Sort players
    player_data = sort_players(player_data, tournament_level, sort)
    sort_type = player_data[1]
    player_data = player_data[0]

    print("Completed. Analyzing data...")

    # Close browser + playwright
    await context.close()
    await browser.close()
    await playwright.stop()

    player_names = []
    player_profiles = []
    player_locations = []
    player_seeds = []
    player_wtns = []
    player_points = []
    player_district_name = []
    player_section_name = []
    player_national_rank = []
    row_colors = []
    counts = 0

    for player in player_data:
        if player and isinstance(player, dict):
            try:
                player["Points"] = f'{int(player["Points"]):,}'
            except:
                player["Points"] = "0"

            try:
                player["Ranking"] = f'{int(player["Ranking"]):,}'
            except:
                player["Ranking"] = "20,000"

            player_names.append(player.get("Name", "Unknown"))
            player_profiles.append(player.get("Profile", "Unknown"))
            player_locations.append(player.get("Location", "Unknown"))
            player_wtns.append(player.get("WTN", "N/A"))
            player_points.append(player["Points"])
            player_district_name.append(player.get("District", "Unknown"))
            player_section_name.append(player.get("Section", "Unknown"))
            player_national_rank.append(player["Ranking"])
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
    num_seeds = pow(2,num_seeds - 3) + 1
    
    for i in player_wtns[:total_players]:
        seeds_temp.append(i)

    # ensure num_seeds is an integer, default to full list if missing/invalid
    try:
        num_seeds = int(num_seeds)
    except (ValueError, TypeError):
        num_seeds = len(seeds_temp)

        
    num_seeds = num_seeds - 1
    seeds_temp.sort()
    seeds_temp = seeds_temp[0:num_seeds]

    for i in player_wtns[:total_players]:
        if i in seeds_temp:
            seeds_final.append(seeds_temp.index(i) + 1)
        else:
            seeds_final.append("-")

    today_str = datetime.today().strftime("%Y-%m-%d")
    safe_name = "".join(c if c.isalnum() or c in " -" else "-" for c in tournament_name)
    filename = f"{safe_name}_{today_str}_{sort_type}.pdf"
    pdf_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, filename)
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter))

    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"<b>{tournament_name}</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    table_data = [["No", "Name", "Location", "Seed", "WTN", "Points", "District", "Section", "National Rank"]]

    link_style = ParagraphStyle(
        'Link',
        parent=styles['Normal'],
        textColor=colors.blue,
        wordWrap='LTR',   # disables breaking for CJK and forces LTR text
    )

    for i in range(len(player_names)):
        # Make player name clickable if link exists
        if i < len(player_profiles) and player_profiles[i]:
            name_with_link = Paragraph(
                f'<a href="{player_profiles[i]}"><u>{player_names[i]}</u></a>',
                link_style
            )
        else:
            name_with_link = Paragraph(player_names[i], styles['Normal'])

        row = [
            str(i + 1),
            name_with_link,
            player_locations[i] if i < len(player_locations) else "",
            str(seeds_final[i]) if i < len(seeds_final) else "",
            player_wtns[i] if i < len(player_wtns) else "",
            player_points[i] if i < len(player_points) else "",
            player_district_name[i] if i < len(player_district_name) else "",
            player_section_name[i] if i < len(player_section_name) else "",
            player_national_rank[i] if i < len(player_national_rank) else "",
            ]
        table_data.append(row)

    # Example column widths (adjust as needed)
    col_widths = [35, 100, 100, 50, 50, 50, 100,  75, 100,  75, 75]  # first value = "No" column width
    table = Table(table_data, repeatRows=1, colWidths=col_widths)
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
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey, spaceBefore=12, spaceAfter=12, dash=3))
    elements.append(table)
    doc.build(elements)
    # ✅ Close resources
    await context.close()
    await browser.close()
    await playwright.stop()
            
    return pdf_path
        
nest_asyncio.apply()  # allow nested event loops in Streamlit

async def main():
    st.title("USTA Tennis Tournament Analyzer")
    playwright, browser, context, page = await setup_browser()

    # Input from user
    tournament_link = st.text_input("Enter the tournament link:")

    # Initialize session state
    if "age_groups_final" not in st.session_state:
        st.session_state.age_groups_final = []
    if "age_options" not in st.session_state:
        st.session_state.age_options = None

    # Button to fetch age groups
    if st.button("Find age groups:"):
        age_options = await age_groups_level(tournament_link, playwright, browser, context, page)
        st.session_state.age_groups_final = age_options[-1]  # store age groups
        st.session_state.age_options = age_options  # store full options

        # ✅ If there’s only one age group, immediately analyze
        if len(st.session_state.age_groups_final) == 1:
            selected_age_group = st.session_state.age_groups_final[0]
            st.session_state["selected_age_group"] = selected_age_group

            sort = await scrape_draw_size(
                tournament_link.replace("overview", "events"),
                selected_age_group
            )

            pdf_path = await scrape_tournament_data(
                tournament_link.lower(),
                selected_age_group,
                sort[0],
                sort[1],
                st.session_state.age_options[0]
            )

            if pdf_path and os.path.exists(pdf_path):
                st.session_state["pdf_ready"] = pdf_path

    # Normal flow (dropdown + manual analyze)
    if st.session_state.age_groups_final:
        # Use stored selection if already set
        selected_age_group = st.session_state.get(
            "selected_age_group",
            st.selectbox("Select an age group:", st.session_state.age_groups_final)
        )
        st.write("You selected:", selected_age_group)

        if st.button("Analyze tournament"):
            sort = await scrape_draw_size(
                tournament_link.replace("overview", "events"),
                selected_age_group
            )

            pdf_path = await scrape_tournament_data(
                tournament_link.lower(),
                selected_age_group,
                sort[0],
                sort[1],
                st.session_state.age_options[0]
            )

            if pdf_path and os.path.exists(pdf_path):
                st.session_state["pdf_ready"] = pdf_path

    # ✅ Always show download button if PDF already exists
    if "pdf_ready" in st.session_state and os.path.exists(st.session_state["pdf_ready"]):
        with open(st.session_state["pdf_ready"], "rb") as f:
            st.download_button(
                label="Download Tournament PDF",
                data=f,
                file_name=os.path.basename(st.session_state["pdf_ready"]),
                mime="application/pdf",
                key="download_pdf_button"
            )


# ✅ Run without asyncio.run()
asyncio.get_event_loop().run_until_complete(main())
