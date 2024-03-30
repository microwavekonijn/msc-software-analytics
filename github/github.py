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
    
    # return the url 100 till 200
    return github_urls[201:300]


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

            # Check for the next page
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                break
        
        # make sure the project is big enough, but not too big
        if merged_human_prs_count > 100 and merged_human_prs_count < 1000:
            qualified_repos.append(repo_url)

    return qualified_repos

def push_pull_requests_to_mongodb(urls):

    # Fetch pull requests for each URL and insert them into MongoDB
    for url in urls:
        pull_requests = get_pull_requests(url)
        insert_pull_requests_to_mongodb(pull_requests)
        print(f"Inserted {len(pull_requests)} pull requests for {url}")

def find_good_repos():
    good_repos = filter_repos_with_many_merged_prs(fetch_github_urls())
    collection = db.projects

    print(good_repos)

    # Prepare the list of documents to insert into MongoDB
    documents_to_insert = []
    for github_url in good_repos:
        document = {
            "github": github_url,
            "average_pull_request_merge_time": 0,  # Default value, since not calculated
            "README_documentation": False,  # Default value, assuming not checked
            "comments_in_code": False,  # Default value, assuming not checked
            "website_linked": False,  # Default value, assuming not checked
            "wiki_present": False,  # Default value, assuming not checked
            "amount_of_pull_requests": 0  # Default value, since not calculated
        }
        documents_to_insert.append(document)
    
    # Insert documents into the MongoDB collection
    if documents_to_insert:
        collection.insert_many(documents_to_insert)
    else:
        print("No good repos found to insert.")

def delete_records_for_projects(projects_to_delete):
    for project in projects_to_delete:
        regex_pattern = ".*github\.com/" + re.escape(project) + "\.git"
        db.projects.delete_one({"github": {"$regex": regex_pattern}})
        db.pull_requests.delete_many({"project": project})
        print(f"Deleted records for project: {project}")
    