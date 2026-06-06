from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk
import time
from bs4 import BeautifulSoup
from selenium.webdriver import Edge
from selenium.webdriver.common.by import By
import plotly.graph_objects as go
import requests
from datetime import date
from datetime import datetime
import json

# Function to setup Edge WebDriver
def setup_driver(minimize):
    driver = Edge()
    if minimize: driver.minimize_window()  # Minimize the window instead of using headless mode
    return driver

def age_groups(link):
    driver = setup_driver(True)
    driver.get(link.lower())
    soup = BeautifulSoup(driver.page_source, 'lxml')  # Parse once
    groups = [h6.text for h6 in soup.find("tbody", class_="MuiTableBody-root css-y6j1my").find_all("h6")]
    return groups

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
    try: location = BeautifulSoup(driver.page_source, 'lxml').find_all("div", class_="readonly-text__content")[1].text.split('|')[1].split('Section:')[0]
    except (AttributeError, IndexError): location = "Unknown"

    # Get WTN (World Tennis Number)
    try: wtn = BeautifulSoup(driver.page_source, 'lxml').find("p", class_="v-form-wtn-widget__section-value").text
    except AttributeError: wtn = "40.00"  # Default WTN if not available

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
    try: last = requests.get("https://app.universaltennis.com/api/v1/player/" + str(record[utrs.index(utr2)]) + "/results").json()['events'][0]['startDate'].split("T")[0]
    except: last = "N/A"
    return [utr2, last, count]


def scrape_player(player_link):
    """
    Scrape individual player data.
    """
    try:
        info = scrape_usta(player_link)
        return {
            "Name": info[0],
            "Location": info[1],
            "WTN": info[2],
            "Points": info[3],
            "Ranking": info[4],
        }
    except Exception as e:
        return None

def scrape_tournament_data(tournament_url, age_group, draw_size, sort):
    driver = setup_driver(True)
    tournament_url = tournament_url.lower()
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

    print(f"Found {len(player_links)} player(s). Starting information search...")

    # Use ThreadPoolExecutor for parallel scraping
    with ThreadPoolExecutor(max_workers=8) as executor: player_data = list(executor.map(scrape_player, player_links))

    # Filter out None results (in case of scraping errors)
    player_data = [data for data in player_data if data is not None]

    # Initialize player_data_sorted with a default value
    player_data_sorted = player_data

    # Fix sorting logic for player data
    if sort == 1:  # Sort by Points
        player_data_sorted = sorted(
            player_data,
            key=lambda x: float(x["Points"].replace(",", "")) if x["Points"].replace(",", "").isdigit() else 0,
            reverse=True,
        )
    elif sort == 2:  # Sort by WTN
        def parse_wtn(wtn_str):
            try: return float(wtn_str)  # Convert WTN to a float directly
            except ValueError: return 40.0  # Default WTN if conversion fails
        player_data_sorted = sorted(player_data, key=lambda x: parse_wtn(x["WTN"]))
        
    # Initialize data for Plotly table
    names, locations, seeds, wtns, points, rankings, utrs, lasts = [], [], [], [], [], [], [], []
    row_colors = []  # List to hold row colors

    average_draw_utr = 0  # Initialize the variable before using it
    average_utr = 0  # Initialize average_utr as well
    in_05_range_count = 0
    in_10_range_count = 0
    in_15_range_count = 0
    in_20_range_count = 0
    out_of_range_count = 0
    counts = 1
    counte = 0
    for player in player_data_sorted:
        # Scrape UTR for the player (manual input for now)
        x = scrape_utr(player['Name'], player['Location'], counts, len(player_links))
        utr = x[0]
        last = x[1]
        counte += x[2]
        
        # Set reference UTR for comparison (Shaurya Kandhari)
        if player['Name'] == "Shaurya Kandhari": main_utr = float(str(utr).replace("xx","50"))
        
        # Add player data to lists for Plotly table

        # Format points if they are numeric
        try: player["Points"] = f'{int(player["Points"]):,}'  # Format as integer with commas
        except ValueError: player["Points"] = "0"  # Default value if invalid

        # Format ranking if it is numeric
        try: player["Ranking"] = f'{int(player["Ranking"]):,}'  # Format as integer with commas
        except ValueError: player["Ranking"] = "20,000"  # Default value if invalid
        names.append(player["Name"])
        locations.append(player["Location"])
        wtns.append(player["WTN"])
        points.append(player["Points"])
        rankings.append(player["Ranking"])
        utrs.append(utr)
        lasts.append(last)

        
        # Check if the count is greater than the draw size, and set the row color
        if int(counts) > int(draw_size): row_colors.append('lightcoral')  # Red color if count exceeds draw size
        else:
            average_draw_utr += float(str(utr).replace("xx","50"))
            row_colors.append('white')  # White color otherwise

        counts += 1

    seeds2 = []
    seeds = []
    n = 0
    while pow(2,n) < int(draw_size):
        n += 1
    n = pow(2,n - 2)
    for i in wtns:
        seeds2.append(i)
    seeds2.sort()
    seeds2 = seeds2[0:n]
    for i in wtns:
        if i in seeds2:
            seeds.append(seeds2.index(i) + 1)
        else:
            seeds.append("-")
    
    # Create the Plotly table with conditional row coloring
    fig = go.Figure(data=[go.Table(
        header=dict(values=["No", "Name", "Location", "Seeding", "WTN", "Points", "Ranking", "UTR", "Last Tournament"],
                    fill_color='green',
                    align='left'),
        cells=dict(values=[list(range(1, counts)), names, locations, seeds, wtns, points, rankings, utrs, lasts],
                   fill_color=[row_colors],  # Set the row colors conditionally
                   align='left'),
                   columnwidth=[1/2, 1, 1, 1/2, 3/4, 3/4, 3/4, 3/4, 1]  # Adjust these proportions as needed
                   )
    ])

    
    
    # Calculate UTR ranges and print summary
    total_players = len(player_data)
    summary_text = ""
    for utr in utrs:
        if int(utrs.index(utr)) < int(draw_size):
            utr = float(utr.replace("xx","50"))
            # Check if UTR is within the specified range
            if main_utr and main_utr - 0.5 <= float(utr) <= main_utr + 0.5: in_05_range_count += 1
            elif main_utr and main_utr - 1 <= float(utr) <= main_utr + 1: in_10_range_count += 1
            elif main_utr and main_utr - 1.5 <= float(utr) <= main_utr + 1.5: in_15_range_count += 1
            elif main_utr and main_utr - 2 <= float(utr) <= main_utr + 2: in_20_range_count += 1
            else: out_of_range_count += 1
        average_utr += float(str(utr).replace("xx","50"))

    # Prepare the summary text
    summary_text += f"Tournament Information As Of {time}<br>"
    summary_text += f"Total Average UTR: {round(average_utr / total_players, 2)}<br>"
    if int(draw_size) <= int(total_players): summary_text += f"Average UTR of Draw: {round(average_draw_utr / int(draw_size), 2)}<br>"
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
        cells=dict(values=[list(range(1, counts)), names, locations, seeds, wtns, points, rankings, utrs, lasts],
                   fill_color=[row_colors],
                   align='left',
                   ),
        domain=dict(x=[0, 1], y=[0, 0.8])  # Adjust the y domain to move the table down
    )

    # Show the table and summary in a browser
    fig.update_layout(margin=dict(l=0, r=0, t=100, b=100))  # Adjust the layout to fit the summary text above
    fig.show()

# Variable to store user input
tournament_link = ""
age_group = ""
draw_size = ""
sort = ""

def sorttype(selected_sort_type):
    global sort
    sort = selected_sort_type.get()  # Get the selected value from the second dropdown
    sort = int(sort[0])
    root.destroy()
    scrape_tournament_data(tournament_link.lower(), age_group, draw_size, sort)

def drawsize(selected_draw_size):
    global draw_size
    draw_size = selected_draw_size  # Update the global draw_size with the value from the input
    
    # Create a dropdown list (OptionMenu) dynamically
    selected_sort_type = tk.StringVar()  # Create a new StringVar for the second dropdown
    selected_sort_type.set("Select a sort type: ")  # Set the default value
    options2 = ["1. Points", "2. WTN"]

    # Create the second dropdown
    dropdown2 = tk.OptionMenu(root, selected_sort_type, *options2)
    dropdown2.grid(row=4, column=0, padx=20, pady=2, sticky="w")

    # Create a button to submit the selected value from the second dropdown
    submit_button = tk.Button(root, text="Submit", command=lambda: sorttype(selected_sort_type))
    submit_button.grid(row=4, column=1, padx=10, pady=5, sticky="w")

def agegroup():
    global age_group
    age_group = selected_option.get().split()[1]
    
    # Create a label
    label = tk.Label(root, text="Enter the draw size:")
    label.grid(row=3, column=0, padx=20, pady=5, sticky="w")  # Reduced pady

    # Create a larger text input box
    entry = tk.Text(root, height=1, width=10)  # Set height and width of the text input box
    entry.grid(row=3, column=1, padx=20, pady=5, sticky="w")  # Reduced pady

    # Create a submit button and place it next to the text box
    submit_button = tk.Button(root, text="Submit", command=lambda: drawsize(entry.get("1.0", "end-1c")))  # Get value from text input
    submit_button.grid(row=3, column=2, padx=10, pady=5, sticky="w")  # Reduced pady

def submit():
    global tournament_link  # Declare the variable as global to store input
    tournament_link = entry.get("1.0", tk.END).strip()  # Get the text from the Text widget
    options = age_groups(tournament_link)  # Example options
    selected_option.set("Select an age group: ")  # Set the default value
    dropdown = tk.OptionMenu(root, selected_option, *options)
    dropdown.grid(row=2, column=0, padx=20, pady=2, sticky="w")
    # Create a submit button and place it next to the text box
    submit_button = tk.Button(root, text="Submit", command=agegroup)
    submit_button.grid(row=2, column=1, padx=5, pady=2, sticky="w")  # Reduced pady


root = tk.Tk()
root.title("Tournament Players Info")

# Make the window occupy the entire screen
screen_width = root.winfo_screenwidth() 
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")

# Create a label
label = tk.Label(root, text="Enter the URL for the tournament below:")
label.grid(row=0, column=0, columnspan=2, padx=20, pady=5, sticky="w")  # Reduced pady

# Create a larger text input box
entry = tk.Text(root, height=1, width=140)  # Set height and width of the text input box
entry.grid(row=1, column=0, columnspan=20, padx=20, pady=5, sticky="w")  # Reduced pady

# Create a submit button and place it next to the text box
submit_button = tk.Button(root, text="Submit", command=submit)
submit_button.grid(row=1, column=20, padx=10, pady=5, sticky="w")  # Reduced pady

# Create a StringVar to store the selected option
selected_option = tk.StringVar()

# Ensure grid cells expand properly
root.grid_rowconfigure(25, weight=0, minsize=30)  # Set a small minimum size for the row
root.grid_columnconfigure(25, weight=1)
root.attributes('-topmost', 1)  # Make the window always on top

root.mainloop()
