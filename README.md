# TournamentPlayers

Analyze USTA junior tennis tournaments automatically.

TournamentPlayers collects player information from tournament pages, processes rankings and player metrics, and generates organized tournament outputs for analysis and reporting.

Built with Python, Playwright, Streamlit, and ReportLab.

---

## Overview

TournamentPlayers was created to reduce the manual work involved in reviewing tennis tournament entries.

Instead of opening dozens or hundreds of player pages individually, this tool gathers information automatically and organizes it into usable tournament data.

Current capabilities include:

- Scraping tournament and player information
- Collecting player metadata
- Extracting rankings and points
- Supporting tournament analysis workflows
- Exporting report outputs
- Interactive Streamlit interface

---

## Features

### Tournament Scraping

Extract player information directly from tournament links.

### Player Analysis

Collect:

- Player name
- Location
- District
- Section
- WTN
- Ranking
- Tournament points

### Streamlit Interface

Simple browser-based interface.

### PDF Export

Generate structured reports.

### Large Dataset Support

Designed for high-volume tournament analysis.

---

# Screenshots

Add screenshots here.

## Dashboard

![Dashboard](README_assets/dashboard.png)

---

## Results

![Results](README_assets/results.png)

---

## Generated Report

![Report](README_assets/report.png)

---

# Installation

## Clone repository

```bash
git clone https://github.com/therealshaurya2009/TournamentPlayers.git

cd TournamentPlayers
```

## Create virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Mac/Linux:

```bash
python3 -m venv venv

source venv/bin/activate
```

## Install dependencies

```bash
pip install -r requirements.txt
```

Install Playwright browser:

```bash
playwright install chromium
```

---

# Running the Project

Launch:

```bash
streamlit run main.py
```

Open:

```plaintext
http://localhost:8501
```

---

# Example Workflow

### 1. Start the application

```bash
streamlit run main.py
```

### 2. Enter tournament information

Paste a tournament URL.

### 3. Start analysis

The application will:

- Load tournament information
- Visit player pages
- Collect rankings
- Process statistics

### 4. Review output

View generated tables and reports.

---

# Project Structure

```plaintext
TournamentPlayers/

├── main.py
├── archive/
│   ├── TournamentPlayersV1.py
│   ├── TournamentPlayersV2.py
│   ├── ...
│
├── README.md
├── requirements.txt
├── README_assets/
│
└── output/
```

---

# Technology Stack

| Category | Technology |
|---|---|
| Language | Python |
| UI | Streamlit |
| Browser Automation | Playwright |
| Async Runtime | asyncio |
| Reporting | ReportLab |
| Parsing | Python |

---

# Architecture

```plaintext
User
 ↓
Streamlit Interface
 ↓
Playwright Browser
 ↓
Tournament Scraper
 ↓
Data Extraction
 ↓
Analysis
 ↓
PDF Output
```

---

# Performance Notes

Large tournaments may require:

- Stable internet
- Additional runtime
- Browser resources

Performance depends on:

- Tournament size
- Website response speed
- Local machine resources

---

# Limitations

Current limitations:

- Requires active internet connection
- External website structure changes may break selectors
- Large tournaments can increase runtime
- Browser automation may occasionally require retries

---

# Future Improvements

Planned improvements:

- Better browser reuse
- Faster scraping
- Improved export formats
- Persistent caching
- Database integration
- Additional player metrics
- Cloud deployment

---

# Contributing

Suggestions and pull requests are welcome.

If contributing:

1. Fork repository
2. Create branch

```bash
git checkout -b feature/new-feature
```

3. Commit changes

```bash
git commit -m "feat: add improvement"
```

4. Push branch

```bash
git push origin feature/new-feature
```

5. Open Pull Request

---

# License

MIT License

---

# Author

Created by Shaurya Kandhari

Project developed to automate and scale junior tennis tournament analysis.
