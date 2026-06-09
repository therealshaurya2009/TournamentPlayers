# USTA Tennis Tournament Analyzer 🎾

A comprehensive Python-based web scraping and data analytics platform designed to extract detailed player statistics and tournament rosters directly from the United States Tennis Association (USTA) platform. 

The application parses complex, dynamic player profiles to extract metrics such as **WTN (World Tennis Number)**, **UTR (Universal Tennis Rating)**, sectional locations, national points, and regional rankings. It calculates statistical distribution thresholds and builds structured, publication-ready analytical summary distributions.

---

## 🛠️ Tech Stack & Key Libraries

Depending on which historic version you run, the project leverages different tiers of Python automation, scraping layers, and graphical interfaces:

* **Web Scraping & Browser Automation:** `Playwright (Async API)`, `Selenium WebDriver`, `BeautifulSoup4`, `Requests`, `webdriver_manager`
* **User Interfaces:** `Streamlit` (Modern Reactive Web Interface), `Tkinter` (Legacy Desktop GUI)
* **Reporting & Data Visualization:** `ReportLab` (PDF Report Engineering), `Plotly Graph Objects` (Interactive Browser Tables)
* **Asynchronous & System Control:** `asyncio`, `nest_asyncio`, `psutil`, `ThreadPoolExecutor`

---

## 🚀 Getting Started

### Prerequisites
Make sure you have Python 3.9 or higher installed. To run the latest and most optimized versions of the codebase (`V9`, `V10`, or `V11`), install the dependencies via pip:

```bash
pip install streamlit playwright beautifulsoup4 reportlab requests psutil nest_asyncio\
```

If you are running the Playwright-backed versions (V7 through V11) for the first time, ensure the required browser binaries are initialized on your machine:

```bash
playwright install chromium
```

How to Run
To boot up the modern interactive web application interface, navigate to your root project directory and execute:

```Bash
streamlit run TournamentPlayersV10.py
(Replace TournamentPlayersV10.py with whichever specific version file you want to test).
```

📈 Version Evolution & Project History
This repository documents an end-to-end software engineering journey across 11 distinct iterations, showcasing structural migrations from simple sequential scripts to highly optimized, multi-threaded, and eventually completely asynchronous reactive web applications:

```V1``` — Proof of Concept: A foundational command-line script leveraging sequential ```Selenium (Edge)``` loops and ```BeautifulSoup4```. It targets player search nodes, parses profile markup, handles basic UTR/WTN strings, and pushes interactive datatables straight to the local browser using ```Plotly```.

```V2 & V3``` — Concurrency & Desktop GUI: Dropped raw terminal inputs for a formal ```Tkinter``` desktop window GUI. To bypass slow sequential profile fetching, this era integrated a ```ThreadPoolExecutor``` to handle concurrent scraper worker threads. V3 refined sync timeouts with ```WebDriverWait``` explicit conditions.

```V4``` — Extended Search Capabilities: Introduced a dynamic cross-referencing search tool (```find_player```) that leverages USTA’s global portal to parse individual player URLs cleanly by inputting raw string text names.

```V5 & V6``` — Corporate PDF Reporting: Completely replaced raw browser visuals with automated document assembly. Integrated ```ReportLab``` to structure tournament rosters into landscape-oriented tables, compute percentage distributions, and automatically open local PDFs via system subprocesses (```os.startfile/xdg-open```). ```V6``` modularized the setup with clean anti-detection User-Agents and multi-browser support.

```V7``` — High-Speed Async & Playwright Migration: Completely replaced Selenium with ```Playwright (Async API)``` to dramatically minimize script runtimes. Included automatic DOM scrolling injectors and configured ```psutil``` pipeline handlers to cleanly kill orphaned background browser processes upon termination.

```V8``` — Web UI Paradigm Shift: Phased out Tkinter to migrate the presentation layer entirely to ```Streamlit```, converting the script into an executive web application layout.

```V9 & V10``` — Async Lifecycle Architecture: Solved intricate async loop collisions inside Streamlit by wrapping runtime environments with ```nest_asyncio```. Optimized state retention (```st.session_state```) so generated data vectors and file buffers persist correctly without breaking the UI during script re-runs. ```V10``` scaled the anti-bot ```wait``` thresholds to 10,000ms to guarantee complete stability over massive draw sheets.

```V11``` — Production Finalization: Refined network resilience and exception-handling frameworks, stabilizing continuous data streams across deep draw pages without triggering USTA rate-limiting blocks.

📊 Core Features & Extracted Statistics
Automated Draw Parsing: Resolves raw tournament event pages, automatically detecting explicit age divisions, ranking classifications, and dynamic competitor draw scales.

Metric Fetching & Aggregation: Safely extracts protected values (WTN data vectors, exact UTR metrics, national points balances, and sectional tracking IDs).

Statistical Thresholding: Computes the concentration ratios of players falling within competitive bands, generating clear distribution breakdowns (e.g., percentage inside/outside target player thresholds).

Automated PDF Compiler: Outputs publication-grade, color-coded PDF books featuring clean header formatting, horizontal line separators, and calculated tournament health summaries.

📝 License
Distributed under the MIT License. See LICENSE for more information.


### Pro-Tips for Final Polish on GitHub:
1. **Add Images/Screenshots:** Since your later versions build a clean Streamlit interface and compile beautiful `ReportLab` PDFs, take screenshots of them. You can drag and drop those image files directly into the GitHub README markdown text editor. It is highly recommended to place them right under the **Core Features** section!
2. **Relative File Structuring:** If you decide later to clean up your root directory by placing these files into a subdirectory (e.g., `src/` or `versions/`), remember to update the **How to Run** snippet (`streamlit run versions/TournamentPlayersV10.py`) so users don't get a file-not-found error.
