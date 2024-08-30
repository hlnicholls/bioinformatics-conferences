import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re 
import json 
import yaml

def fetch_esc_dates(url):
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Conference start and end dates
        start_date_meta = soup.find('meta', attrs={"name": "esc-event-startdate"})
        end_date_meta = soup.find('meta', attrs={"name": "esc-event-enddate"})
        
        # Abstract submission date
        abstract_date_div = soup.find('div', class_="importantdate")
        abstract_date_span = abstract_date_div.find('span', class_="start") if abstract_date_div else None
        
        # Location information
        location_info = soup.find('script', type='application/ld+json')
        if location_info:
            location_data = json.loads(location_info.string)
            location_name = location_data.get("location", {}).get("name", "Not available")
            address = location_data.get("location", {}).get("address", {})
            city = address.get("addressLocality", "Not available")
            country = address.get("addressCountry", "Not available")
            place = f"{city}, {country}"  # Format: "City, Country"
        else:
            place = "Not available"
        
        if start_date_meta and end_date_meta and abstract_date_span:
            start_date = start_date_meta['content']
            end_date = end_date_meta['content']
            abstract_date = datetime.strptime(abstract_date_span.text.strip(), "%d/%m/%Y").strftime('%Y-%m-%d') + " 23:59:00"
            
            return {
                'title': 'ESC',
                'year': datetime.strptime(start_date, "%Y-%m-%d").year,
                'link': url,
                'deadline': abstract_date,
                'timezone': 'UTC-12',  # Assuming UTC-12; adjust as necessary
                'place': place,  # Updated to include the extracted location
                'date': f"{datetime.strptime(start_date, '%Y-%m-%d').strftime('%B %d')} - {datetime.strptime(end_date, '%Y-%m-%d').strftime('%B %d, %Y')}",
                'start': start_date,
                'end': end_date,
                'sub': 'CV',  # Assuming 'CV' for Cardiovascular; adjust if necessary
                'note': "Please check the website for more details.",
            }
        else:
            print("Necessary conference information not found.")
            return {}
    else:
        print("Failed to retrieve the webpage")
        return {}

def parse_date_range(date_range):
    parts = date_range.split('–')
    if len(parts) == 2:
        start_date, end_date = parts
    else:
        return None, None

    end_day, year = end_date.split(',')
    end_month = start_date.split(' ')[0]

    start = f"{start_date}, {year}".strip()
    end = f"{end_month} {end_day}, {year}".strip()

    start_datetime = datetime.strptime(start, "%B %d, %Y")
    end_datetime = datetime.strptime(end, "%B %d, %Y")

    start_str = start_datetime.strftime('%Y-%m-%d')
    end_str = end_datetime.strftime('%Y-%m-%d')

    return start_str, end_str

def extract_deadline(text):
    # Use regular expression to find date patterns (e.g., "February 6, 2024")
    matches = re.findall(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2},\s\d{4}', text)
    if matches:
        # Assume the first match is the deadline date
        return datetime.strptime(matches[0], "%B %d, %Y").strftime('%Y-%m-%d') + " 23:59:00"
    return ""

def fetch_eshg_dates(main_url):
    year = datetime.now().year
    response = requests.get(main_url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        conference_url = f"https://{year}.eshg.org/home"
        
        conference_response = requests.get(conference_url)
        if conference_response.status_code == 200:
            conference_soup = BeautifulSoup(conference_response.text, 'html.parser')
            conference_date_tag = conference_soup.find('h2', class_='header-date')
            location_tag = conference_soup.find('h3', class_='header-title').find_all('i')[-1]
            
            abstracts_url = f"https://{year}.eshg.org/abstracts/"
            abstracts_response = requests.get(abstracts_url)
            if abstracts_response.status_code == 200:
                abstracts_soup = BeautifulSoup(abstracts_response.text, 'html.parser')
                abstract_deadline_meta = abstracts_soup.find('meta', property='og:description')
                
                if conference_date_tag and location_tag and abstract_deadline_meta:
                    date_text = conference_date_tag.text.strip()
                    location_text = location_tag.text.strip()
                    abstract_deadline_text = abstract_deadline_meta['content']
                    
                    start, end = parse_date_range(date_text)
                    month_name = datetime.strptime(start, '%Y-%m-%d').strftime('%B')
                    start_day = start.split('-')[-1]
                    end_day = end.split('-')[-1]
                    year = start.split('-')[0]
                    
                    # Adjusted to format the date with zero-padded days
                    date_str = f"{month_name} {start_day.zfill(2)} – {end_day.zfill(2)}, {year}"
                    
                    deadline = extract_deadline(abstract_deadline_text)
                    
                    return {
                        'title': 'ESHG',
                        'year': year,
                        'link': conference_url,
                        'deadline': deadline,
                        'timezone': 'UTC-12',
                        'place': location_text,
                        'date': date_str,  # Updated 'date' field
                        'start': start,
                        'end': end,
                        'sub': 'GEN',
                        'note': abstract_deadline_text,
                    }
                else:
                    print("Necessary information not found.")
                    return {}
            else:
                print("Failed to retrieve the abstracts page.")
                return {}
        else:
            print("Failed to retrieve the conference page.")
            return {}
    else:
        print("Failed to retrieve the main ESHG page.")
        return {}

def read_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file) or []

def write_yaml(file_path, data):
    with open(file_path, 'w') as file:
        yaml.dump(data, file, sort_keys=False)

def update_conference_entry(conferences, new_data):
    for conference in conferences:
        if conference['title'] == new_data['title'] and conference['year'] == new_data['year']:
            # Update existing entry if year matches
            conference.update(new_data)
            return conferences

    # Add new entry if not found or year does not match
    conferences.append(new_data)
    return conferences

def update_conferences(file_path):
    conferences = read_yaml(file_path)
    
    # Fetch new conference data
    esc_data = fetch_esc_dates('https://www.escardio.org/Congresses-Events/ESC-Congress')
    eshg_data = fetch_eshg_dates('https://www.eshg.org/home')
    
    # Update or add conference entries
    conferences = update_conference_entry(conferences, esc_data)
    conferences = update_conference_entry(conferences, eshg_data)
    
    # Construct the new file name with today's date
    today = datetime.now().strftime('%Y%m%d')  # Format: YYYYMMDD
    new_file_path = file_path.replace('.yml', f'_updated_{today}.yml')
    
    # Write updated data back to the new YAML file
    write_yaml(new_file_path, conferences)
    print(f"Updated YAML file saved as: {new_file_path}")

yaml_file_path = '/Users/hannah/Documents/GitHub/conference-deadlines/_data/conferences.yml'
update_conferences(yaml_file_path)
