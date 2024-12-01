import csv
import requests

class Data_reader:

    configurations = {}
    playlists = []
    file_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSQMOg2yZp2tJaOK20D9RetwFd92GDbuIKQNrnZfl8KgQmrbA9TAa1Npr3rPI8tYIbqw_E9NC6RE7uR/pub?gid=452631794&single=true&output=csv"

    def __init__(self):

        self.configurations , self.playlists = self.read_csv_from_google_drive()



    
    def read_csv_from_google_drive(self):
        try:
            # Send a GET request to the file URL
            response = requests.get(self.file_url)
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"Failed to download file. HTTP Response Code: {response.status_code}")
                return
            
            # Check content type to verify it's a CSV file
            content_type = response.headers.get('Content-Type', '')
            print(f"Content Type: {content_type}")
            if 'text/csv' not in content_type:
                print("The file does not appear to be a CSV file.")
                return

            # Read the CSV content line by line
            csv_data = response.text
            csv_reader = csv.reader(csv_data.splitlines())
            
            configurations = {}
            playlists = []

            # Process and print each row
            for row_index, row in enumerate(csv_reader):
              row_data = " | ".join(cell.strip() for cell in row)
              print(f"Row {row_index}: {row_data}")
              if(row_index>0):
                  playlist = row[0]
                  name = row[1]
                  modes={}
                  modes["Segment h00"] = row[2]
                  modes["Segment v1"] = row[3]
                  modes["Segment h10"] = row[4]
                  modes["Segment h11"] = row[5]
                  modes["Segment v2"] = row[6]
                  modes["Segment h20"] = row[7]
                  modes["Segment v3"] = row[8]
                  modes["Segment h30"] = row[9]
                  modes["Segment h31"] = row[10]
                  modes["Segment h32"] = row[11]
                  modes["Segment v4"] = row[12]
                  if(playlist in configurations):
                      configurations[playlist].append({"name":name, "modes":modes})
                  else:
                      playlists.append(playlist)
                      configurations[playlist]=[{"name":name, "modes":modes}]
                  
            return configurations , playlists
        
        except Exception as e:
            print(f"Error reading CSV file from Google Drive: {e}")