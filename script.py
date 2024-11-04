# script will get the list of all the contributors for GNOME server and make a json file
# and commits it

import requests  
import json
import os

# Replace with your GitHub token
ORG_NAME = "GNOME-Nepal"
BASE_URL = "https://api.github.com" # Base URL for Github's API. All Api requests will start with this 

# Contains HTTP Headers that are sent with every request
headers = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Authorization": f"Bearer {os.getenv('MAINTAINERS_POLLING_TOKEN')}",
}

# Get repositories of the organization
repos_url = f"{BASE_URL}/orgs/{ORG_NAME}/repos"             # Constructs the API Endpoint URL to get all repositories within the Specified Organization
repos_response = requests.get(repos_url, headers=headers)   # Sends an HTTP GET request to fetch the repositories. And stored in repos_response

contributor_contribution_dict = {}                          # Initilizes an empty dictionary to store usernames as keys and their contribution count as values 


if repos_response.status_code == 200:
    repos = repos_response.json()           

    for repo in repos:              
        repo_name = repo["name"]            # Extracts the repository's name from each repositry object

        # Get contributors for the current repository
        contributors_url = f"{BASE_URL}/repos/{ORG_NAME}/{repo_name}/contributors"         # Constructs the API Endpoint Url for the list of contributor for each repository
        contributors_response = requests.get(contributors_url, headers=headers)            # Sends and HTTP Get request to fetch the contributors for the current repository 

        if contributors_response.status_code == 200:
            repo_contributors = contributors_response.json()

            if repo_contributors:                         
                for repo_contributor in repo_contributors:  
                    username = repo_contributor["login"]    # Extracts the Githun username of each contributors
                    if username == "actions-user":
                        continue
                    if repo_contributor["type"] != "User":
                        continue
                    if username not in contributor_contribution_dict:
                        contributor_contribution_dict[username] = 0

                    contributor_contribution_dict[username] += repo_contributor[
                        "contributions"
                    ]


# now we will get all the user's information
full_information = []

for username in contributor_contribution_dict.keys():       # Loops Through each username 
    user_information_url = f"{BASE_URL}/users/{username}"   # # Construct API Endpoint URL to get user profile information

    response = requests.get(
        user_information_url,
        headers=headers,
    )                                               
    score = contributor_contribution_dict[username] # retrives the total number of contributions the user has made across all repositories
    if response.status_code == 200:
        user = response.json()                     
        user["contributions"] = score               # Adds the user's total contributions to their profile information
        full_information.append(user)              

# sort by highest contributors first
full_information = sorted(
    full_information,
    key=lambda x: x["contributions"],
    reverse=True,
)

# Opens (or creates) a file named contributors.json in write mode.
with open("contributors.json", "w") as c:
    json.dump(
        full_information,
        c,
        indent=2,
        ensure_ascii=False,
    )
