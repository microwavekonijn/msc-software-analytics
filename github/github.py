import requests
import configparser
from pymongo import MongoClient
import re

url_pattern = re.compile(r'<(https?://[^>]+)>; rel="next"')

def load_api_token():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config.get('DEFAULT', 'GITHUB_API_TOKEN')

# Use the loaded API token
api_token = load_api_token()
headers = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {api_token}",
}

def load_mongodb_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return {
        'host': config.get('mongodb', 'DB_HOST'),
        'port': config.getint('mongodb', 'DB_PORT'),
        'user': config.get('mongodb', 'DB_USER'),
        'password': config.get('mongodb', 'DB_PASS'),
        'dbname': config.get('mongodb', 'DB_NAME')
    }


def insert_pull_requests_to_mongodb(pull_requests):
    mdb_config = load_mongodb_config()
    # MongoDB URI string
    mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client[mdb_config['dbname']]
    collection = db.pull_requests
    collection.insert_many(pull_requests)


def get_owner_and_repo(url):
    """
    Extracts the owner and repository name from a GitHub URL.
    Example input url: git+https://github.com/element-plus/element-plus.git

    Parameters:
    - url: The URL of the GitHub repository.

    Returns:
    A tuple containing the owner and repository name.
    """
    parts = url.split('/')
    owner = parts[-2]
    repo = parts[-1].split('.')[0]
    print(owner, repo)
    return owner, repo


def get_pull_requests(repo_url):
    """
    Fetches pull request data for a given GitHub repository.

    Parameters:
    - owner: The owner of the repository.
    - repo: The name of the repository.

    Returns:
    A list of dictionaries, each containing data about a pull request.
    """
    pull_requests = []
    owner, repo = get_owner_and_repo(repo_url)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=closed&per_page=100"

    # GitHub API paginates responses, so we need to handle pagination.
    while url:
        #print(f"Requesting URL: {url}")  # Debug: Print the URL before the request
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"GitHub API returned {response.status_code}: {response.json()}")
        data = response.json()
        for pr in data:
            if pr['merged_at'] is None: # only consider merged PRs
                continue

            pr_data = {
                'project': f"{owner}/{repo}",
                'title': pr['title'],
                'created_at': pr['created_at'],
                'merged_at': pr['merged_at'],
                'submitter': pr['user']['login'],
                'reviewers': [reviewer['login'] for reviewer in pr.get('requested_reviewers', [])],
                'assignees': [assignee['login'] for assignee in pr.get('assignees', [])],
            }

            pull_requests.append(pr_data)

        # GitHub provides the next page URL in the Link header
        link = response.headers.get('Link')
        if link:
            match = url_pattern.search(link)
        else:
            match = None
        
        if match:
            url = match.group(1)  # Extract the URL directly without angle brackets
        else:
            url = None

    return pull_requests


urls = ["git+https://github.com/GoodwayGroup/lib-hapi-rollbar.git"]

# Fetch pull requests for each URL and insert them into MongoDB
for url in urls:
    pull_requests = get_pull_requests(url)
    insert_pull_requests_to_mongodb(pull_requests)
    print(f"Inserted {len(pull_requests)} pull requests for {url}")
