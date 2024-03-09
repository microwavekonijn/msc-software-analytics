import requests
import configparser
from pymongo import MongoClient

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


def get_pull_requests(owner, repo):
    """
    Fetches pull request data for a given GitHub repository.

    Parameters:
    - owner: The owner of the repository.
    - repo: The name of the repository.

    Returns:
    A list of dictionaries, each containing data about a pull request.
    """
    pull_requests = []
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=closed"

    # GitHub API paginates responses, so we need to handle pagination.
    while url:
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
            }

            pull_requests.append(pr_data)

        # GitHub provides the next page URL in the Link header
        link = response.headers.get('Link')
        if link:
            # Find the URL for the next page if it exists.
            next_link = None
            for part in link.split(','):
                if 'rel="next"' in part:
                    next_link = part.split(';')[0].strip('<>')
                    break
            url = next_link
        else:
            url = None

    return pull_requests

# Example usage
owner = "danbernier"
repo = "WordCram"
pull_requests = get_pull_requests(owner, repo)
for pr in pull_requests:
    print(pr)
insert_pull_requests_to_mongodb(pull_requests)