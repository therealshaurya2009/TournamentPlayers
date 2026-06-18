import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import plotly.graph_objects as go
import requests
from datetime import date
from datetime import datetime
import json

# Function to setup Edge WebDriver
def setup_driver(minimize):
    # Automatically downloads and links the correct ChromeDriver for your system
    service = ChromeService(ChromeDriverManager().install())
    
    # Optional: If you want to configure Chrome options (like headless mode)
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new") # Uncomment if you want it to run invisibly
    
    # Initialize the Chrome Browser instance
    driver = webdriver.Chrome(service=service, options=options)
    
    if minimize: 
        driver.minimize_window()
        
    return driver

def scrape_usta(player_link):
    player_id = player_link.strip("https://www.usta.com/en/home/play/player-search/profile.html#uaid=")
    driver = setup_driver(True)
    driver.get(player_link + "&tab=about")
    time.sleep(5)  # Adjust the sleep time as necessary

    # Fetch player name
    player_name = BeautifulSoup(driver.page_source, 'lxml').find("span", class_="readonly-text__text")
    player_name = player_name.text.strip("\n") if player_name else "Unknown Player"

    # Get player location
    location = "Unknown"
    try:
        location = BeautifulSoup(driver.page_source, 'lxml').find_all("div", class_="readonly-text__content")
        location = location[1].text.split('|')[1].split('Section:')[0]
    except (AttributeError, IndexError):
        location = "Unknown"

    # Get WTN (World Tennis Number)
    try:
        wtn = BeautifulSoup(driver.page_source, 'lxml').find("p", class_="v-form-wtn-widget__section-value").text
    except AttributeError:
        wtn = "40.00"  # Default WTN if not available

    # Get ranking and points
    driver.get(player_link + "&tab=rankings")
    ranking_info = BeautifulSoup(driver.page_source, 'lxml').find_all("div", class_="v-grid-cell__content")

    points = "0"  # Default points if not available
    rank = "20000"  # Default rank if not available

    for j in range(0, len(ranking_info), 5):
        if "National Standings List (combined)" in ranking_info[j].text:
            if age_group in ranking_info[j].text:
                points = ranking_info[j + 1].text.strip("\n") if j + 1 < len(ranking_info) else "0"
                rank = ranking_info[j + 2].text.strip("\n") if j + 2 < len(ranking_info) else "20,000"
                break

    driver.quit()  # Close the driver after retrieving each player's data
    return(player_name, location, wtn, points, rank)

def scrape_utr(name, location, counts, player):
    url = "https://app.universaltennis.com/api/v2/search/players?query=" + name.replace(" ","%20")
    utr2 = ""
    response = requests.get(url)
    data = response.json()
    players = data['hits']
    count = 0
    record = []
    homes = []
    utrs = []
    try:
        for i in players:
            record.append(i['source']['id'])
            homes.append(i['source']['location']['display'])
            utrs.append(i['source']['threeMonthRatingChangeDetails']['ratingDisplay'])
        for i in homes:
            if i.strip() == location.strip():
                utr2 = str(utrs[homes.index(i)])
                homes.clear()
    except:
        utr2 = str(input(str(counts) + "/" + str(player) + ". Enter " + name + "'s UTR: ")) + ".xx"
        count += 1
    if ".xx" not in str(utr2):
            utr2 = str(input(str(counts) + "/" + str(player) + ". Enter " + name + "'s UTR: ")) + ".xx"
            count += 1
    try:
        last = requests.get("https://app.universaltennis.com/api/v1/player/" + str(record[utrs.index(utr2)]) + "/results")
        last = last.json()['events'][0]['startDate'].split("T")[0]
    except:
        last = "N/A"
    return [utr2, last, count]

# Main function to scrape tournament player data
def scrape_tournament_data(tournament_url, age_group, draw_size, sort):
    driver = setup_driver(True)
    driver.get(tournament_url.replace("overview", "players"))

    # Find all players in the tournament
    players = BeautifulSoup(driver.page_source, 'lxml').find_all("td", class_="_alignLeft_1nqit_268")
    player_links = ["https://www.usta.com/en/home/play/player-search/profile.html#uaid=2019026844"] # List to store player profile links
    driver.quit()  # Close the driver after retrieving player links
    time = datetime.now()

    # Extract player links based on age group and gender
    for i in range(0, len(players), 2):  # Iterate every 2nd element for name and age group
        if age_group in players[i + 1].text and "Boys" in players[i + 1].text and "Singles" in players[i + 1].text:
            link = players[i].find("a")
            if link and link.get('href'):  # Ensure the link is valid
                player_links.append(link.get('href'))
    
    # Initialize a list to store player data
    player_data = []

    print(f"Found {len(player_links)} player(s). Starting information search:")

    # Initialize player counter
    average_utr = 0
    average_draw_utr = 0
    in_05_range_count = 0
    in_10_range_count = 0
    in_15_range_count = 0
    in_20_range_count = 0
    out_of_range_count = 0
    main_utr = None  # Variable to store the UTR for reference (e.g., for Shaurya Kandhari)

    for player_link in player_links:
        info = scrape_usta(player_link)
        # Add the player's data to the list
        player_data.append({
            "Name": info[0],
            "Location": info[1],
            "WTN": info[2],
            "Points": info[3],
            "Ranking": info[4],
        })


    # Fix sorting logic for player data
    if sort == 1:  # Sort by Points
        player_data_sorted = sorted(player_data, key=lambda x: (float(x["Points"].replace(",", "")) if x["Points"].replace(",", "").isdigit() else 0), reverse=True)
    elif sort == 2:  # Sort by WTN
        def parse_wtn(wtn_str):
            try:
                return float(wtn_str)  # Convert WTN to a float directly
            except ValueError:
                return 40.0  # Default WTN if conversion fails
        player_data_sorted = sorted(player_data, key=lambda x: parse_wtn(x["WTN"]))


    # Initialize data for Plotly table
    names, locations, wtns, points, rankings, utrs, lasts = [], [], [], [], [], [], []
    row_colors = []  # List to hold row colors

    counts = 1
    counte = 0
    for player in player_data_sorted:
        # Scrape UTR for the player (manual input for now)
        x = scrape_utr(player['Name'], player['Location'], counts, len(player_links))
        utr = x[0]
        last = x[1]
        counte += x[2]
        
        # Set reference UTR for comparison (Shaurya Kandhari)
        if player['Name'] == "Shaurya Kandhari":
            main_utr = float(str(utr).replace("xx","50"))
        
        # Add player data to lists for Plotly table

        # Format points if they are numeric
        try:
            player["Points"] = f'{int(player["Points"]):,}'  # Format as integer with commas
        except ValueError:
            player["Points"] = "0"  # Default value if invalid

        # Format ranking if it is numeric
        try:
            player["Ranking"] = f'{int(player["Ranking"]):,}'  # Format as integer with commas
        except ValueError:
            player["Ranking"] = "20,000"  # Default value if invalid
        names.append(player["Name"])
        locations.append(player["Location"])
        wtns.append(player["WTN"])
        points.append(player["Points"])
        rankings.append(player["Ranking"])
        utrs.append(utr)
        lasts.append(last)    

        # Check if the count is greater than the draw size, and set the row color
        if counts > draw_size:
            row_colors.append('lightcoral')  # Red color if count exceeds draw size
        else:
            average_draw_utr += float(str(utr).replace("xx","50"))
            row_colors.append('white')  # White color otherwise

        counts += 1

    print("Completed with " + str(100-(100*round(counte/len(player_data),4))) + "% accuracy.")
    # Create the Plotly table with conditional row coloring
    fig = go.Figure(data=[go.Table(
        header=dict(values=["No", "Name", "Location", "WTN", "Points", "Ranking", "UTR", "Last Tournament"],
                    fill_color='green',
                    align='left'),
        cells=dict(values=[list(range(1, counts)), names, locations, wtns, points, rankings, utrs, lasts],
                   fill_color=[row_colors],  # Set the row colors conditionally
                   align='left'),
                   columnwidth=[3/4, 1, 1, 3/4, 3/4, 3/4, 3/4, 1]  # Adjust these proportions as needed
                   )
    ])

    
    
    # Calculate UTR ranges and print summary
    total_players = len(player_data)
    summary_text = ""
    for utr in utrs:
        if int(utrs.index(utr)) < int(draw_size):
            utr = float(utr.replace("xx","50"))
            # Check if UTR is within the specified range
            if main_utr and main_utr - 0.5 <= float(utr) <= main_utr + 0.5:
                in_05_range_count += 1
            elif main_utr and main_utr - 1 <= float(utr) <= main_utr + 1:
                in_10_range_count += 1
            elif main_utr and main_utr - 1.5 <= float(utr) <= main_utr + 1.5:
                in_15_range_count += 1
            elif main_utr and main_utr - 2 <= float(utr) <= main_utr + 2:
                in_20_range_count += 1
            else:
                out_of_range_count += 1
            average_utr += float(str(utr).replace("xx","50"))

    # Prepare the summary text
    total_players -= 1
    summary_text += f"Tournament Information As Of {time}<br>"
    summary_text += f"Total Average UTR: {round(average_utr / total_players, 2)}<br>"
    if draw_size <= total_players:
        summary_text += f"Average UTR of Draw: {round(average_draw_utr / draw_size, 2)}<br>"
    else:
        summary_text += f"Average UTR of Draw: {round(average_draw_utr / total_players, 2)}<br>"
    summary_text += f"Total players within +/- 0.5 UTR range: {in_05_range_count} ({round((in_05_range_count * 100) / total_players, 2)}%)<br>"
    summary_text += f"Total players within +/- 1.0 UTR range: {in_10_range_count} ({round((in_10_range_count * 100) / total_players, 2)}%)<br>"
    summary_text += f"Total players within +/- 1.5 UTR range: {in_15_range_count} ({round((in_15_range_count * 100) / total_players, 2)}%)<br>"
    summary_text += f"Total players within +/- 2.0 UTR range: {in_20_range_count} ({round((in_20_range_count * 100) / total_players, 2)}%)<br>"
    summary_text += f"Total players in UTR range: {(total_players - out_of_range_count - 1)} ({round(((total_players - out_of_range_count) * 100) / total_players, 2)}%)<br>"
    summary_text += f"Total players out of UTR range: {out_of_range_count} ({round((out_of_range_count * 100) / total_players, 2)}%)<br>"

    # Add summary text to the figure as annotation (positioned above the table)
    fig.add_annotation(
        text=summary_text,
        xref="paper", yref="paper",
        x=0, y=1.2,  # Adjust y-coordinate to position the summary above the table
        showarrow=False,
        font=dict(size=12),
        align="left"
    )

    # Move the table down to avoid overlap
    fig.update_traces(
        cells=dict(values=[list(range(1, counts)), names, locations, wtns, points, rankings, utrs, lasts],
                   fill_color=[row_colors],
                   align='left',
                   ),
        domain=dict(x=[0, 1], y=[0, 0.8])  # Adjust the y domain to move the table down
    )

    # Show the table and summary in a browser
    fig.update_layout(margin=dict(l=0, r=0, t=100, b=100))  # Adjust the layout to fit the summary text above
    fig.show()


# User input
tournament_link = input("Tournament Link: ").lower()
age_group = input("Age group: ")
draw_size = int(input("Enter the draw size: "))
sort = int(input("Selection by 1.Points or 2.WTN? "))
scrape_tournament_data(tournament_link, age_group, draw_size, sort)
