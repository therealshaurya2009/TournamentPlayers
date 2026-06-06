import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk
import time
from bs4 import BeautifulSoup
from selenium.webdriver import Edge
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import plotly.graph_objects as go
import requests
from datetime import date
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import json

# Function to setup Edge WebDriver
def setup_driver(minimize):
    driver = Edge()
    if minimize: driver.minimize_window()  # Minimize the window instead of using headless mode
    return driver

def find_player(name):
    driver = setup_driver(True)
    driver.get("https://www.usta.com/en/home/play/player-search.html")
    player_name = driver.find_element(By.ID, "gridsearch-5689e82879-input")
    player_name.send_keys(name)
    player_name.send_keys(Keys.RETURN)
    time.sleep(2)
    if "uaid" in driver.current_url:
        return(driver.current_url.strip("&tab=tournaments"))
    else:
        return(" ")
    
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
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "readonly-text__text")))

    # Fetch player name
    player_name = BeautifulSoup(driver.page_source, 'lxml').find("span", class_="readonly-text__text")
    player_name = player_name.text.strip("\n") if player_name else "Unknown Player"

    # Get player location
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

    return(player_name, location, wtn, points, rank)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_recruiting(name, location):
    driver = setup_driver(True)
    driver.get("https://www.tennisrecruiting.net/player.asp")
    player_name = driver.find_element(By.NAME, "f_playername")
    player_name.send_keys(name)
    player_name.send_keys(Keys.RETURN)
    grades = ["Senior","Junior","Sophomore","Freshman","8th Grader","7th Grader","6th Grader"]
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
                driver2 = setup_driver(True)
                driver2.get("https://www.tennisrecruiting.net" + links[homes.index(i)])
                # Wait until the rating image is loaded in the second driver
                rating = WebDriverWait(driver2, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//*[@id='CenterColumn']/table[1]/tbody/tr/td[2]/table/tbody/tr[4]/td/img"))
                )
                try:
                    utr = WebDriverWait(driver2, 10).until(
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
    driver = setup_driver(True)
    driver.get(link)
    age_groups = BeautifulSoup(driver.page_source, 'lxml').find_all("h6", class_="_H6_1iwqn_128")
    links = BeautifulSoup(driver.page_source, 'lxml').find_all("a", class_="_link_19t7t_285")
    groups_final = []
    driver.quit()
    for i in age_groups:
        groups_final.append(i.text)
    link_final = links[groups_final.index(age_group) - 1]
    link_final = "https://playtennis.usta.com" + link_final.get("href")
    driver = setup_driver(True)
    driver.get(link_final)
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
            recruiting_rating[0] = "☆☆☆☆☆"
        elif "1star" in recruiting_rating[0]:
            recruiting_rating[0] = "★☆☆☆☆"
        elif "2star" in recruiting_rating[0]:
            recruiting_rating[0] = "★★☆☆☆"
        elif "3star" in recruiting_rating[0]:
            recruiting_rating[0] = "★★★☆☆"
        elif "4star" in recruiting_rating[0]:
            recruiting_rating[0] = "★★★★☆"
        elif "5star" in recruiting_rating[0]:
            recruiting_rating[0] = "★★★★★"
        elif "6star" in recruiting_rating[0]:
            recruiting_rating[0] = "🪙🪙🪙🪙🪙"
        else:
            recruiting_rating[0] = "????????"
        return {
            "Name": info[0],
            "Location": info[1],
            "WTN": info[2],
            "Points": info[3],
            "Ranking": info[4],
            "Recruiting": recruiting_rating[0],
            "Class": recruiting_rating[2],
            "UTR": recruiting_rating[1],
        }
    except Exception as e:
        return None

def scrape_tournament_data(tournament_url, age_group, sort, player_url):
    start = datetime.now()
    driver = setup_driver(True)
    tournament_url = tournament_url.lower()
    driver.get(tournament_url)
    name = driver.find_element(By.XPATH, "//*[@id='tournaments']/div/div/div/div[1]/div/div[1]/h1").text
    driver.quit()  # Close the driver

    draw_size = int(scrape_draw_size(tournament_url.replace("overview", "events"), age_group))

    driver = setup_driver(True)
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

    player_links.append(player_url)

    # Check if any player links were found
    if not player_links:
        print("No player links found. Exiting.")
        return  # Exit the function if no players are found

    print("Found",len(player_links),"players. Starting information search...")

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

    print("Completed. Analyzing data...")
        
    # Initialize data for Plotly table
    names, locations, seeds, wtns, points, rankings, recruiting, year, utr = [], [], [], [], [], [], [], [], []
    row_colors = []  # List to hold row colors

    counts = 0

    for player in player_data_sorted:
        if player and isinstance(player, dict):  # Ensure player is not None and is a dictionary

            # Format points if they are numeric
            try:
                player["Points"] = f'{int(player["Points"]):,}'  # Format as integer with commas
            except (ValueError, TypeError, KeyError):  # Handle missing keys or invalid values
                player["Points"] = "0"

            # Format ranking if it is numeric
            try:
                player["Ranking"] = f'{int(player["Ranking"]):,}'  # Format as integer with commas
            except (ValueError, TypeError, KeyError):
                player["Ranking"] = "20,000"

            # Append data to lists
            names.append(player.get("Name", "Unknown"))
            locations.append(player.get("Location", "Unknown"))
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
    x = int(draw_size)
    if x > len(player_links):
        x = len(player_links)
    while pow(2,n) < x:
        n += 1
    n = pow(2,n - 2)
    for i in wtns[:x]:
        seeds2.append(i)
    seeds2.sort()
    seeds2 = seeds2[0:n]
    for i in wtns[:x]:
        if i in seeds2:
            seeds.append(seeds2.index(i) + 1)
        else:
            seeds.append("-")
    
    # Create the Plotly table with conditional row coloring
    fig = go.Figure(data=[go.Table(
        header=dict(values=["No", "Name", "Location", "Seed", "WTN", "Points", "Ranking", "Recruiting", "Grade", "UTR"],
                    fill_color='green',
                    align='left'),
        cells=dict(values=[list(range(1, counts + 1)), names, locations, seeds, wtns, points, rankings, recruiting, year, utr],
                   fill_color=[row_colors],  # Set the row colors conditionally
                   align='left'),
                   columnwidth=[1/8, 3/4, 1/2, 1/4, 1/4, 1/4, 1/4, 1/4, 1/2, 1/4]  # Adjust these proportions as needed
                   )
    ])
    
    # Prepare the summary text
    summary_text = name
    
    # Add summary text to the figure as annotation (positioned above the table)
    fig.add_annotation(
        text=summary_text,
        xref="paper", yref="paper",
        x=0.5, y=1,  # Adjust y-coordinate to position the summary above the table
        showarrow=False,
        font=dict(size=20),
        align="center"
    )

    # Move the table down to avoid overlap
    fig.update_traces(
        cells=dict(values=[list(range(1, counts + 1)), names, locations, seeds, wtns, points, rankings, recruiting, year, utr],
                   fill_color=[row_colors],
                   align='left',
                   ),
        domain=dict(x=[0, 1], y=[0, 0.9])  # Adjust the y domain to move the table down
    )

    # Adjust layout to fit the title properly
    fig.update_layout(
        margin=dict(l=0, r=0, t=25, b=100),  # Increase top margin for title spacing
        title_x=0.5  # Center the layout title if used
    )
    
    # Show the table and summary in a browser
    fig.update_layout(margin=dict(l=0, r=0, t=35, b=100))  # Adjust the layout to fit the summary text above
    fig.show()

    print("Printing results...")
    end = datetime.now()
    difference = end - start
    print("Average Time per Player = ", difference / len(player_links))
    
# Variable to store user input
tournament_link = ""
age_group = ""
draw_size = ""
sort = ""

def submit_player_name(player_entry):
    player_name = player_entry.get().strip()
    root.destroy()
    scrape_tournament_data(tournament_link.lower(), age_group, sort, find_player(player_name))
            
def submit_checkbox(check_var):
    include_player = check_var.get()

    if include_player == 1:
        # Show entry field and button for player name
        label = tk.Label(root, text="Enter player name:")
        label.grid(row=6, column=0, padx=20, pady=5, sticky="w")

        player_entry = tk.Entry(root, width=40)
        player_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")
        player_submit_btn = tk.Button(root, text="Submit", command=lambda: submit_player_name(player_entry))
        player_submit_btn.grid(row=6, column=2, padx=10, pady=5, sticky="w")
    
    else:
        root.destroy()
        scrape_tournament_data(tournament_link.lower(), age_group, sort, "")
        
def sorttype(selected_sort_type):
    global sort
    sort = int(selected_sort_type.get()[0])

    # Checkbox to include player
    check_var = tk.IntVar()
    checkbox = tk.Checkbutton(root, text="Include player?", variable=check_var)
    checkbox.grid(row=5, column=0, padx=20, pady=5, sticky="w")

    # Submit button next to checkbox
    submit_btn = tk.Button(root, text="Submit", command=lambda: submit_checkbox(check_var))
    submit_btn.grid(row=5, column=1, padx=10, pady=5, sticky="w")

def agegroup():
    global age_group
    age_group = selected_option.get()
    
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
