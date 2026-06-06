from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
import nest_asyncio
import streamlit as st
import sqlite3
import psutil, signal
import shutil
import sys

# Other Imports
from collections import defaultdict
from datetime import datetime
import os
import platform
import random
import re
import requests
import subprocess
import us

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

wait = int(60000)

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

def get_income_data(location):
    API_KEY = "98262bd515249390db127f7dad4727a62b94fa54"
    # Extract state abbreviation
    city_name = location.split(",")[0].strip()
    player_state = location.split(",")[1].strip()
    state = us.states.lookup(player_state)
    state_fips = state.fips  # e.g., "17"

    # Request all places (cities) in the state
    url = f"https://api.census.gov/data/2023/acs/acs5?get=NAME&for=place:*&in=state:{state_fips}"
    response = requests.get(url)
    data = response.json()

    place_fips_final = 0

    # data[0] is header, data[1:] are rows
    for entry in data[1:]:
        name, place_fips = entry[0], entry[2]
        if city_name.lower() in name.lower():
            place_fips_final = place_fips

    url = (
        f"https://api.census.gov/data/2023/acs/acs5"
        f"?get=NAME,B19013_001E,B19301_001E"
        f"&for=place:{place_fips_final}&in=state:{state_fips}"
        f"&key={API_KEY}"
    )

    response = requests.get(url)
    
    try:
        data = response.json()
        return int(data[1][1])
    except Exception as e:
        print("JSON Error:", e)
        return None


async def scrape_player(page, player_link, age_group, playwright, browser, context):
    retries = 0
    while retries <= 5:
        retries += 1
        try:
            # ABOUT TAB
            await page.goto(player_link + "&tab=about")

            try:
                name = await page.locator("span.readonly-text__text > h3").inner_text()
                name = name.strip()
            except:
                name = "Unknown Player"

            try:
                raw = await page.locator(".readonly-text__content").nth(1).inner_text()
                location = raw.split('|')[1].split('Section:')[0].strip("\n")
                if "District" in location:
                    location = "Unknown"
            except:
                location = "Unknown"

            try:
                raw = await page.locator(".readonly-text__content").nth(1).inner_text()
                district = raw.split("|")[2].split(": ")[1]
            except:
                district = "Unknown"

            try:
                raw = await page.locator(".readonly-text__content").nth(1).inner_text()
                section = raw.split("|")[1].split(": ")[1]
            except:
                section = "Unknown"

            try:
                wtn_xpath = "/html/body/div[5]/div/div[2]/div/div/div[3]/div/div/div[2]/div/div/div[2]/div/div[3]/div/div/div/div[2]/div/form/div[3]/div/div/div/div[1]/div/div[2]/div[1]/div/p"
                wtn = await page.locator(f"xpath={wtn_xpath}").inner_text()
            except:
                wtn = "40.00"

            # RANKINGS TAB
            await page.goto(player_link + "&tab=rankings")
            try:
                await page.wait_for_selector(".v-grid-cell__content", timeout=8000)
                cells = await page.locator(".v-grid-cell__content").all_inner_texts()

                points = "0"
                ranking = "25,000"

                rows = [cells[i:i+5] for i in range(0, len(cells), 5)]

                target = age_group.split(" ")[1] + " National Standings List"

                for row in rows:
                    if target in row[0]:
                        points = row[1]
                        ranking = row[2]
            except:
                points = "0"
                ranking = "25,000"

            # Income
            salary = get_income_data(location)

            return {
                "Name": name,
                "Location": location,
                "District": district,
                "Section": section,
                "WTN": wtn,
                "Points": points,
                "Ranking": ranking,
                "Salary": salary,
                "Profile": player_link
            }

        except:
            return {
                "Name": "Unknown",
                "Location": "Unknown",
                "District": "Unknown",
                "Section": "Unknown",
                "WTN": "40.00",
                "Points": "0",
                "Ranking": "25,000",
                "Salary": "Unknown",
                "Profile": player_link
            }
        
async def scrape_tournament_data(tournament_url, age_group, draw_size, sort, tournament_level):

    # ---- DB Setup (unchanged) ----
    conn = sqlite3.connect("C:/Shaurya/Tennis/TournamentPlayers/TournamentAnalysisV1.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        name TEXT,
        location TEXT,
        district TEXT,
        section TEXT,
        wtn REAL,
        points INTEGER,
        national_rank INTEGER,
        salary INTEGER,
        level INTEGER,
        age INTEGER,
        gender TEXT,
        UNIQUE(name, location, level, age)
    )
    """)
    conn.commit()

    # ---- ONE browser session for ENTIRE age group ----

    playwright, browser, context, page = await setup_browser()

    # Go to main tournament page
    tournament_url = tournament_url.lower()
    await page.goto(tournament_url.replace("overview", "players"))

    # Get list of players
    await page.wait_for_selector("._alignLeft_1nqit_268", timeout=wait)
    players_list = await page.query_selector_all("._alignLeft_1nqit_268")
    
    player_links = []
    for row in players_list:
        text = await row.inner_text()
        if age_group in text:
            link = await players_list[players_list.index(row) - 1].query_selector("a")
            href = await link.get_attribute("href")
            player_links.append(href)

    # ---- Streamlit progress ----
    progress_bar = st.progress(0)
    status_text = st.empty()

    results = []
    total = len(player_links)

    # ---- REUSE THE SAME PAGE for all players ----
    for i, link in enumerate(player_links):

        # new isolated page for this player
        player_page = await context.new_page()

        try:
            player = await scrape_player(player_page, link, age_group, playwright, browser, context)
        finally:
            await player_page.close()

        # Insert immediately
        cursor.execute("""
            INSERT OR IGNORE INTO players
            (name, location, district, section, wtn, points, national_rank,
             salary, level, age, gender)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player["Name"], player["Location"], player["District"], player["Section"],
            float(player["WTN"]), int(player["Points"].replace(",", "")),
            int(player["Ranking"].replace(",", "")),
            player["Salary"],
            tournament_level.split(" ")[1],   # Level numeric
            age_group.split(" ")[1],          # Age
            age_group.split(" ")[0]           # Gender
        ))
        conn.commit()

        results.append(player)
        progress_bar.progress(int((i+1)/total * 100))

    
    await context.close()
    await browser.close()
    # And ONLY if using async_playwright():
    #   async with async_playwright():
    #       ...
    # (Playwright auto-closes)

    conn.close()
    return results
    
        
nest_asyncio.apply()  # allow nested event loops in Streamlit

async def main():
    st.title("USTA Tennis Tournament Analyzer")
    playwright, browser, context, page = await setup_browser()

    # Input for multiple tournaments
    tournament_links_raw = st.text_input("Enter tournament links (use | to separate)")

    # Split tournaments into a list
    tournament_links = [t.strip() for t in tournament_links_raw.split("|") if t.strip()]
    
    # Initialize session state
    if "age_groups_final" not in st.session_state:
        st.session_state.age_groups_final = []
    if "age_options" not in st.session_state:
        st.session_state.age_options = None
    if "pdf_ready" not in st.session_state:
        st.session_state.pdf_ready = {}

    # Button to fetch age groups + run everything
    if st.button("Find age groups:"):

        # Loop through each tournament
        for tlink in tournament_links:
            st.write(f"🔍 Processing Tournament: {tlink}")

            # Get age groups + level
            age_options = await age_groups_level(tlink, playwright, browser, context, page)

            if not age_options:
                st.write(f"⚠️ Could not extract age groups for: {tlink}")
                continue

            st.session_state.age_groups_final = age_options[-1]
            st.session_state.age_options = age_options

            tournament_level = age_options[0]

            # Loop through every age group in this tournament
            for age_group in st.session_state.age_groups_final:
                st.write(f"Analyzing age group: {age_group} ...")
                
                await scrape_tournament_data(
                    tlink.lower(),
                    age_group,
                    "",
                    "",
                    tournament_level
                )

        st.write("🎉 All tournaments processed!")

# ✅ Run without asyncio.run()
asyncio.get_event_loop().run_until_complete(main())
