import requests
import configparser
from pymongo import MongoClient
import re

# ------------------- Global Variables & Config -------------------

url_pattern = re.compile(r'<(https?://[^>]+)>; rel="next"')

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

mdb_config = load_mongodb_config()
# MongoDB URI string
mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
client = MongoClient(mongo_uri)
db = client[mdb_config['dbname']]

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

# ------------------- Functions -------------------

def insert_pull_requests_to_mongodb(pull_requests):
    collection = db.pull_requests
    collection.insert_many(pull_requests)

def fetch_github_urls():
    collection = db.npm
    
    # Query with specified conditions
    query = {
        "downloads.downloads": {
            "$gt": 2000000,
            "$lt": 10000000
        }
    }
    
    # Sorting, limiting and projecting the query
    github_urls = collection.find(query).sort("pkg.time.modified", -1).distinct("github")
    
    # return the number 51 till nmber 100 distinct github URLs
    return github_urls[:100]


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
        print(f"Requesting URL: {url}")  # Debug: Print the URL before the request
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"GitHub API returned {response.status_code}: {response.json()}")
        data = response.json()
        for pr in data:
            if pr['merged_at'] is None or pr['user']['type'] != 'User': # only consider merged PRs
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

def filter_repos_with_many_merged_prs(repo_list):
    qualified_repos = []

    for repo_url in repo_list:
        owner, repo = get_owner_and_repo(repo_url)
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=closed&per_page=100"
        merged_human_prs_count = 0
        while url:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to fetch data for {repo}: {response.status_code}")
                break
            data = response.json()
            for pr in data:
                if pr.get('merged_at') is not None and pr['user']['type'] == 'User':  # Check if PR is merged and made by a human
                    merged_human_prs_count += 1
            
            if merged_human_prs_count > 100:
                qualified_repos.append(repo_url)
                break

            # Check for the next page
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                break

    return qualified_repos

def push_pull_requests_to_mongodb():
    urls = ["git+https://github.com/AppsFlyerSDK/react-native-appsflyer.git",
      "git+https://github.com/ArweaveTeam/arweave-js.git",
      "git+https://github.com/DavidWells/analytics.git",
      "git+https://github.com/Decathlon/vitamin-web.git",
      "git+https://github.com/FullHuman/purgecss.git",
      "git+https://github.com/GoogleChrome/lighthouse-ci.git",
      "git+https://github.com/GoogleCloudPlatform/opentelemetry-operations-js.git",
      "git+https://github.com/IBM/openapi-validator.git",
      "git+https://github.com/Kong/httpsnippet.git",
      "git+https://github.com/MichalLytek/type-graphql.git",
      "git+https://github.com/Microsoft/PowerBI-JavaScript.git",
      "git+https://github.com/Microsoft/appcenter-sdk-react-native.git",
      "git+https://github.com/Microsoft/code-push.git",
      "git+https://github.com/Microsoft/fast.git",
      "git+https://github.com/Modernizr/Modernizr.git",
      "git+https://github.com/Quramy/ts-graphql-plugin.git",
      "git+https://github.com/Shopify/quilt.git",
      "git+https://github.com/Shopify/web-configs.git",
      "git+https://github.com/Typescript-TDD/ts-auto-mock.git",
      "git+https://github.com/actions/toolkit.git",
      "git+https://github.com/adamgibbons/ics.git"]

    # Fetch pull requests for each URL and insert them into MongoDB
    for url in urls:
        pull_requests = get_pull_requests(url)
        insert_pull_requests_to_mongodb(pull_requests)
        print(f"Inserted {len(pull_requests)} pull requests for {url}")

def find_good_repos():
    good_repos = filter_repos_with_many_merged_prs(fetch_github_urls())
    collection = db.projects
    # insert list into mongo db
    collection.insert_one({"good_repos": good_repos})
