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
    # again cursed, but my computer hates me, and this is the only way it works for me
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
    # get all projects from db
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
    # all that is left is now '<owner>/<repo>'
    owner, repo = owner_repo.split('/')
    return owner, repo


def get_delta_time(pull_request):
    # very simple to get all time stamps
    time_created = datetime.strptime(pull_request["created_at"][:-1], "%Y-%m-%dT%H:%M:%S")
    time_merged = datetime.strptime(pull_request["merged_at"][:-1], "%Y-%m-%dT%H:%M:%S")
    return time_merged-time_created


def update_project(project, avg_time, amount):
    mdb_config = load_mongodb_config()
    # MongoDB URI string
    mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client[mdb_config['dbname']]
    collection = db.projects
    # set the time and amount of pull requests correctly for a given project
    collection.update_many({"github": project["github"]}, {"$set": {"average_pull_request_merge_time": avg_time}})
    collection.update_many({"github": project["github"]}, {"$set": {"amount_of_pull_requests": amount}})



def get_pull_requests(owner, repo):
    mdb_config = load_mongodb_config()
    # MongoDB URI string
    mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client[mdb_config['dbname']]
    collection = db.pull_requests
    # getting all pull requests where the project is from the same owner and from the right repo
    cursor = collection.find({"project": f"{owner}/{repo}"})
    return cursor


def add_fields_to_document(project):
    mdb_config = load_mongodb_config()
    # MongoDB URI string
    mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client[mdb_config['dbname']]
    collection = db.projects
    # adding using seperate update_many funcs so they appear in the right order
    # in python order does not matter, but in mongodb compass it does
    collection.update_many({"github": project["github"]}, {"$set": {"average_pull_request_merge_time": 0}})
    collection.update_many({"github": project["github"]}, {"$set": {"README_documentation": False,
                                                                    "comments_in_code": False,
                                                                    "website_linked": False,
                                                                    "wiki_present": False}})
    collection.update_many({"github": project["github"]}, {"$set": {"amount_of_pull_requests": 0}})


def main():
    # get the projects we want to work with
    projects = get_working_projects()

    # for each project
    for project in projects:
        # if the project already is processed, skip it
        if "README_documentation" in project.keys():
            print("Skipping project ", project["github"])
            continue

        print("Working on ", project["github"])

        # add the needed fields to the document
        add_fields_to_document(project)

        # get all pull requests
        owner, repo = get_owner_and_repo(project["github"])
        pull_requests = get_pull_requests(owner, repo)
        total = 0
        time = 0

        # calculate how many pull requests in total, and what the average time is
        for request in pull_requests:
            total += 1
            time += get_delta_time(request).seconds
        
        # update the project with average time and total amount of pull requests
        update_project(project, time//total, total)


if __name__ == "__main__":
    main()