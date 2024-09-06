import requests
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup
import threading
import os
import re
import csv

# Global variable to store the authorization code
auth_code = None

class RedirectHandler(BaseHTTPRequestHandler):
    """Handler to process the redirect and extract the authorization code."""
    def do_GET(self):
        global auth_code
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        auth_code = query_params.get('code', [None])[0]
        
        # Respond to the browser
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Authorization complete. You can close this window.</h1></body></html>")
        
        # Stop the server after receiving the authorization code
        self.server.shutdown()

def start_server():
    """Start a local server to capture the redirect."""
    server_address = ('', 80)  # Port 80
    httpd = HTTPServer(server_address, RedirectHandler)
    print("Starting server on port 80...")
    httpd.serve_forever()

def open_authorization_url():
    """Open the DeviantArt authorization URL in the default web browser."""
    client_id = '40800'
    redirect_uri = 'http://localhost'
    scopes = 'browse'
    auth_url = f"https://www.deviantart.com/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scopes}"
    webbrowser.open(auth_url)

def get_access_token(auth_code):
    """Exchange the authorization code for an access token."""
    client_id = '40800'
    client_secret = '52b8251cf2eae7085fe64ef7670b3ef1'
    redirect_uri = 'http://localhost'
    
    token_url = 'https://www.deviantart.com/oauth2/token'
    payload = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    response = requests.post(token_url, data=payload)
    
    if response.status_code == 200:
        token_info = response.json()
        return token_info.get('access_token')
    else:
        print(f"Failed to retrieve access token: {response.text}")
        return None

def get_folders(username, access_token, offset = 0):
    """Retrieve the folders of a user."""
    url = f"https://www.deviantart.com/api/v1/oauth2/gallery/folders"
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'username': username,
        'limit': 50,
        'offset': offset,
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        folders = data.get('results', [])
        has_more = data.get('has_more', False)
        next_offset = data.get('next_offset', None)
        return folders, has_more, next_offset
    else:
        print(f"Failed to retrieve user folders: {response.text}")
        return [], False, None

def get_deviations(username, folder, access_token, offset = 0):
    """Retrieve the deviations of a user."""
    if folder == None:
        url = f"https://www.deviantart.com/api/v1/oauth2/gallery/all"
    else:
        url = f"https://www.deviantart.com/api/v1/oauth2/gallery/{folder}"
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'username': username,
        'limit': 24,  # Number of deviations to retrieve
        'offset': offset   # Pagination offset
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        deviations = data.get('results', [])
        has_more = data.get('has_more', False)
        next_offset = data.get('next_offset', None)
        return deviations, has_more, next_offset
    else:
        print(f"Failed to retrieve user deviations: {response.text}")
        return [], False, None

def get_deviation_metadata(deviation_ids, access_token):
    """Retrieve the metadata of a set of deviations."""
    url = f"https://www.deviantart.com/api/v1/oauth2/deviation/metadata"
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'deviationids[]': deviation_ids
    }

    response = requests.get(url, headers=headers, params=params)
    if (response.status_code == 200):
        data = response.json()
        metadata = data.get('metadata', [])
        return metadata
    else:
        print(f"Failed to retrieve metadata: {response.status_code}")
        return False

def prompt_folder_inclusion(folder):
    folder_ids = []
    folder_id = folder.get('folderid')
    folder_name = folder.get('name')

    print(f"Folder ID: {folder_id}, Folder Name: {folder_name}")
    include = input(f"Include '{folder_name}' in the data copy? (y/n) ").strip().lower()

    if include in ['yes','y']:
        folder_ids.append(folder_id)
        has_subfolders = folder.get('has_subfolders')

        if has_subfolders:
            subfolders = folder.get('subfolders')

            for subfolder in subfolders:
                subfolder_ids = prompt_folder_inclusion(subfolder)

                if subfolder_ids:
                    folder_ids.extend(subfolder_ids)
    
    return folder_ids

def process_deviations(deviations, access_token, batch_size = 50):
    """Process deviations in batches."""
    metadata = {}

    for i in range(0, len(deviations), batch_size):
        batch = deviations[i:i + batch_size]
        batch_ids = list(map(extract_deviation_id, deviations))
        data = get_deviation_metadata(batch_ids, access_token)

        for item in data:
            deviation_id = item.get('deviationid')

            if deviation_id:
                description_html = item.get('description', 'No Description')
                description_text = parse_html(description_html)
                metadata[deviation_id] = {
                    'html': description_html,
                    'text': description_text
                }
    
    return metadata
        
def extract_deviation_id(deviation):
    """Extracts the ID from a deviation object."""
    return deviation.get('deviationid')

def parse_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    return text

def write_to_tsv(deviations, metadata, file_name):
    """Write deviation details to a TSV file."""
    processed_ids = set()
    file_path = f"{file_name}.tsv"
    file_exists = os.path.isfile(file_path)

    if file_exists:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='\t')
            header = next(reader)
            for row in reader:
                processed_ids.add(row[0])
    
    with open(file_path, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter='\t')

        if not processed_ids:
            writer.writerow(['Deviation ID', 'Title', 'Image URL', 'HTML', 'Text'])
        
        for deviation in deviations:
            deviation_id = deviation.get('deviationid', 'Unknown')
            if deviation_id in processed_ids:
                continue

            title = deviation.get('title', 'Untitled')
            src_url = deviation.get('content', {}).get('src', 'No Image')
            description = metadata.get(deviation_id, {})
            html = description.get('html', '').replace('\t', ' ').replace('\n', ' ')
            text = description.get('text', '').replace('\t', ' ').replace('\n', ' ')

            writer.writerow([deviation_id, title, src_url, html, text])
            processed_ids.add(deviation_id)


def main():
    # Start the local server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.start()
    
    # Open the authorization URL
    open_authorization_url()
    
    # Wait for the server to get the authorization code
    while auth_code is None:
        pass

    # Get the access token using the authorization code
    access_token = get_access_token(auth_code)
    if access_token:
        file_name = input("Enter the output file name (exclude extension): ").strip()
        if not file_name:
            print("File name cannot be empty.")
            return

        username = input("Enter the DeviantArt username: ").strip()
        if not username:
            print("Username cannot be empty.")
            return

        include_all = input("Do you want to include all folders? (y/n) ").strip().lower()

        if include_all in ['yes', 'y']:
            print("Including all folders.")
            all_deviations = []
            has_more = True
            offset = 0

            while has_more:
                deviations, has_more, offset = get_deviations(username, None, access_token, offset)
                all_deviations.extend(deviations)
                print(f"Retrieved {len(deviations)} deviations, total: {len(all_deviations)}")
            
            print("Retrieved all deviations.")

            metadata = process_deviations(all_deviations, access_token, 50)
            print("Retrieved all deviation metadata.")

            write_to_tsv(all_deviations, metadata, file_name)
            print(f"Wrote deviation data to {file_name}.tsv")
        else:
            all_folders = []
            has_more = True
            offset = 0

            while has_more:
                folders, has_more, offset = get_folders(username, access_token, offset)
                all_folders.extend(folders)

            selected_folders = []
            print("\nAvailable folders:")
            for folder in all_folders:
                folder_ids = prompt_folder_inclusion(folder)

                if folder_ids:
                    selected_folders.extend(folder_ids)

            all_deviations = []
            for folder in selected_folders:
                print(f"Retrieving deviations from folder: {folder}")
                has_more = True
                offset = 0

                while has_more:
                    deviations, has_more, offset = get_deviations(username, folder, access_token, offset)
                    all_deviations.extend(deviations)
                    print(f"Retrieved {len(deviations)} deviations, total: {len(all_deviations)}")

                print(f"Retrieved all deviations from folder: {folder}")

            print("Retrieved all deviations.")

            metadata = process_deviations(all_deviations, access_token, 50)
            print("Retrieved all deviation metadata.")

            write_to_tsv(all_deviations, metadata, file_name)
            print(f"Wrote deviation data to {file_name}.tsv")

if __name__ == "__main__":
    main()