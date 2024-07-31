import requests

# Public URL provided by ngrok
url = 'UPLOAD_LINK'

# Path to the image file you want to upload (make sure the path is correct)
files = {'file': open('/Users/arsenchuzhykov/Desktop/new_sat/mask.png', 'rb')}

# Make the POST request to upload the image
response = requests.post(url, files=files)

# Print the response from the server
print(response.json())
