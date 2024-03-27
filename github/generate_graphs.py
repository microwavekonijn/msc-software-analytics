import configparser
from pymongo import MongoClient
import os
import matplotlib.pyplot as plt

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


def pull_request_bool_cmp(wrt):
    projects = get_working_projects()
    yes_amount = 0
    yes_time = 0
    no_amount = 0
    no_time = 0
    for project in projects:
        if project[wrt]:
            yes_amount += project["amount_of_pull_requests"]
            yes_time += project["amount_of_pull_requests"]*project["average_pull_request_merge_time"]
        else:
            no_amount += project["amount_of_pull_requests"]
            no_time += project["amount_of_pull_requests"]*project["average_pull_request_merge_time"]
    return {"yes": yes_time//yes_amount, "no": no_time//no_amount}


def main():
    # get the projects we want to work with
    projects = get_working_projects()
    # for each project, get the owner and repo
    # then get pull requests
    pull_request_amount = []
    pull_request_merge_time = []
    for project in projects:
        pull_request_amount.append(project["amount_of_pull_requests"])
        pull_request_merge_time.append(project["average_pull_request_merge_time"])
    code_comments_cmp = pull_request_bool_cmp("comments_in_code")
    wiki_present_cmp = pull_request_bool_cmp("wiki_present")
    website_linked_cmp = pull_request_bool_cmp("website_linked")
    fig, axs = plt.subplots(2,2)
    fig.text(0, 0.5, "Average merge time for a pull request (s)", va="center", rotation="vertical")
    axs[0,0].scatter(pull_request_amount, pull_request_merge_time)
    axs[0,0].set(xlabel="Amount of pull requests for a project")
    axs[0,1].bar(list(code_comments_cmp.keys()), list(code_comments_cmp.values()))
    axs[0,1].set(xlabel="Does a project have comments?")
    axs[1,0].bar(list(wiki_present_cmp.keys()), list(wiki_present_cmp.values()))
    axs[1,0].set(xlabel="Does a project have a wiki?")
    axs[1,1].bar(list(website_linked_cmp.keys()), list(website_linked_cmp.values()))
    axs[1,1].set(xlabel="Does a project have a website?")
    fig.tight_layout()
    plt.show()
 

if __name__ == "__main__":
    main()