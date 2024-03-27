import requests
import configparser
from pymongo import MongoClient
import os
from datetime import datetime

def load_api_token():
    config = configparser.ConfigParser()
    # os. is cursed, but somehow only this works
    config.read(os.getcwd() + '\\github\\config.ini')
    return config.get('DEFAULT', 'GITHUB_API_TOKEN')

# Use the loaded API token
api_token = load_api_token()
headers = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {api_token}",
}

def load_mongodb_config():
    config = configparser.ConfigParser()
    config.read(os.getcwd() + '\\github\\config.ini')
    return {
        'host': config.get('mongodb', 'DB_HOST'),
        'port': config.getint('mongodb', 'DB_PORT'),
        'user': config.get('mongodb', 'DB_USER'),
        'password': config.get('mongodb', 'DB_PASS'),
        'dbname': config.get('mongodb', 'DB_NAME')
    }


def get_working_projects():
    mdb_config = load_mongodb_config()
    # MongoDB URI string
    mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client[mdb_config['dbname']]
    collection = db.projects
    cursor = collection.find()
    return cursor


def get_owner_and_repo(repo_link):
    # first clean up repo link
    if repo_link[0:4] == "git+":
        repo_link = repo_link[4:]
    if repo_link[-4:] == ".git":
        repo_link = repo_link[:-4]
    # now link is in format of 'https://github.com/<owner>/<repo>'
    owner_repo = repo_link[19:]
    owner, repo = owner_repo.split('/')
    return owner, repo


def get_delta_time(pull_request):
    time_created = datetime.strptime(pull_request["created_at"][:-1], "%Y-%m-%dT%H:%M:%S")
    time_merged = datetime.strptime(pull_request["merged_at"][:-1], "%Y-%m-%dT%H:%M:%S")
    return time_merged-time_created


def update_project_with_time(project, avg_time):
    mdb_config = load_mongodb_config()
    # MongoDB URI string
    mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client[mdb_config['dbname']]
    collection = db.projects
    collection.update_many({"github": project["github"]}, {"$set": {"average_pull_request_merge_time": avg_time}})



def get_pull_requests(owner, repo):
    mdb_config = load_mongodb_config()
    # MongoDB URI string
    mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client[mdb_config['dbname']]
    collection = db.pull_requests
    cursor = collection.find({"project": f"{owner}/{repo}"})
    return cursor



def main():
    # get the projects we want to work with
    projects = get_working_projects()
    # for each project, get the owner and repo
    # then get pull requests
    for project in projects:
        print(project)
        owner, repo = get_owner_and_repo(project["github"])
        print(owner, repo)
        pull_requests = get_pull_requests(owner, repo)
        avg_time = 0
        for pull_request in pull_requests:
            delta = get_delta_time(pull_request)
            avg_time += delta.seconds
        print(avg_time//50)
        update_project_with_time(project, avg_time//50)
    

def add_documentation_levels():
    mdb_config = load_mongodb_config()
    # MongoDB URI string
    mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client[mdb_config['dbname']]
    collection = db.projects
    collection.update_many({}, {"$set": {"comments_in_code": False,
                                         "wiki_present": False,
                                         "website_linked": False,
                                         "README_documentation": False}})

    

if __name__ == "__main__":
    main()