import configparser
from pymongo import MongoClient
import os
import matplotlib.pyplot as plt

TOTAL_PROJECTS = 52

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


def pull_request_bool_cmp_time(wrt):
    projects = get_working_projects()
    yes_amount = 0
    yes_time = 0
    yes_percentage = 0
    no_amount = 0
    no_time = 0
    no_percentage = 0

    for project in projects:
        if project[wrt]:
            yes_amount += project["amount_of_pull_requests"]
            yes_time += project["amount_of_pull_requests"]*project["average_pull_request_merge_time"]
            yes_percentage += 1
        else:
            no_amount += project["amount_of_pull_requests"]
            no_time += project["amount_of_pull_requests"]*project["average_pull_request_merge_time"]
            no_percentage += 1

    yes_percentage = (yes_percentage / TOTAL_PROJECTS) * 100
    no_percentage = (no_percentage / TOTAL_PROJECTS) * 100

    return { f"yes ({yes_percentage:.2f}%)": yes_time//yes_amount, f"no ({no_percentage:.2f}%)": no_time//no_amount}

def pull_request_bool_cmp_time_multiple_types():
    projects = get_working_projects()

    yes_amount = 0
    yes_time = 0
    yes_percentage = 0
    no_amount = 0
    no_time = 0
    no_percentage = 0

    for project in projects:
        amount = sum(1 for value in [project["README_documentation"], project["comments_in_code"], project["wiki_present"], project["website_linked"]] if value)

        if amount >= 3:
            yes_amount += project["amount_of_pull_requests"]
            yes_time += project["amount_of_pull_requests"]*project["average_pull_request_merge_time"]
            yes_percentage += 1

        if amount <= 1:
            no_amount += project["amount_of_pull_requests"]
            no_time += project["amount_of_pull_requests"]*project["average_pull_request_merge_time"]
            no_percentage += 1

    yes_percentage = (yes_percentage / TOTAL_PROJECTS) * 100
    no_percentage = (no_percentage / TOTAL_PROJECTS) * 100

    return { f"doc types >= 3 ({yes_percentage:.2f}%)": yes_time//yes_amount, f"doc types <= 1 ({no_percentage:.2f}%)": no_time//no_amount}


def pull_request_bool_cmp_amount(wrt):
    projects = get_working_projects()
    yes_amount = 0
    no_amount = 0

    yes_percentage = 0
    no_percentage = 0

    for project in projects:
        if project[wrt]:
            yes_amount += project["amount_of_pull_requests"]
            yes_percentage += 1
        else:
            no_amount += project["amount_of_pull_requests"]
            no_percentage += 1

    yes_percentage = (yes_percentage / TOTAL_PROJECTS) * 100
    no_percentage = (no_percentage / TOTAL_PROJECTS) * 100

    return {f"yes ({yes_percentage:.2f}%)": yes_amount, f"no ({no_percentage:.2f}%)": no_amount}


def amount_of_contributors_per_period(wrt, true_or_false):
    projects = get_working_projects()
    contributor_per_period = []
    indexes = []
    total_projects = 0
    for i in range(10):
        contributor_per_period.append(0)
        indexes.append(i)

    for project in projects:
        if project[wrt] == true_or_false:
            total_projects += 1
            for i in range(0, 10):
                contributor_per_period[i] += project["periods"][i]["count"]

    average_contributor_per_period = [x / total_projects for x in contributor_per_period]

    return {indexes[i]: average_contributor_per_period[i] for i in range(10)}


def amount_per_contributor_group(wrt, true_or_false):
    projects = get_working_projects()

    contributor_per_group = [0, 0, 0]

    for project in projects:
        if project[wrt] == true_or_false:
            for submitter in project["reviewers"]:
                contributions = submitter["contributions"]
                if 0 < contributions < 10:
                    contributor_per_group[0] += 1
                elif 10 < contributions < 50:
                    contributor_per_group[1] += 1
                elif contributions > 50:
                    contributor_per_group[2] += 1

    return contributor_per_group


def generate_scatter_plot():
    # get the projects we want to work with
    projects = get_working_projects()
    # grabbing a lot of data from all the projects
    pull_request_amount = []
    pull_request_merge_time = []
    for project in projects:
        pull_request_amount.append(project["amount_of_pull_requests"])
        pull_request_merge_time.append(project["average_pull_request_merge_time"])

    plt.scatter(pull_request_amount, pull_request_merge_time)
    plt.xlabel("Amount of pull requests")
    plt.ylabel("Average merge time for a pull request (s)")
    # fig.tight_layout()
    plt.show()

def generate_merge_time_plots():
    readme_cmp_time = pull_request_bool_cmp_time("README_documentation")
    code_comments_cmp_time = pull_request_bool_cmp_time("comments_in_code")
    wiki_present_cmp_time = pull_request_bool_cmp_time("wiki_present")
    website_linked_cmp_time = pull_request_bool_cmp_time("website_linked")

    # processing the part with respect to average time
    fig, axs = plt.subplots(2,2)
    fig.text(0, 0.5, "Average merge time for a pull request (s)", va="center", rotation="vertical")
    axs[0,0].bar(list(readme_cmp_time.keys()), list(readme_cmp_time.values()))
    axs[0,0].set(xlabel="Does a project have a Readme?")
    axs[0,1].bar(list(code_comments_cmp_time.keys()), list(code_comments_cmp_time.values()))
    axs[0,1].set(xlabel="Does a project have comments?")
    axs[1,0].bar(list(wiki_present_cmp_time.keys()), list(wiki_present_cmp_time.values()))
    axs[1,0].set(xlabel="Does a project have a wiki?")
    axs[1,1].bar(list(website_linked_cmp_time.keys()), list(website_linked_cmp_time.values()))
    axs[1,1].set(xlabel="Does a project have a website?")
    fig.tight_layout()
    plt.show()

def generate_merge_time_plot_multiple_documentation_types():
    readme_cmp_time = pull_request_bool_cmp_time_multiple_types()

    # processing the part with respect to average time
    # plt.text(0, 0.5, "Average merge time for a pull request (s)", va="center", rotation="vertical")
    plt.bar(list(readme_cmp_time.keys()), list(readme_cmp_time.values()))
    plt.ylabel("Average merge time for a pull request (s)")
    plt.show()

def generate_amount_plots():
    readme_cmp_amount = pull_request_bool_cmp_amount("README_documentation")
    code_comments_cmp_amount = pull_request_bool_cmp_amount("comments_in_code")
    wiki_present_cmp_amount = pull_request_bool_cmp_amount("wiki_present")
    website_linked_cmp_amount = pull_request_bool_cmp_amount("website_linked")

    # processing the part with respect to amount of pull requests
    fig, axs = plt.subplots(2,2)
    fig.text(0, 0.5, "Total amount of pull requests", va="center", rotation="vertical")
    axs[0,0].bar(list(readme_cmp_amount.keys()), list(readme_cmp_amount.values()))
    axs[0,0].set(xlabel="Does a project have a Readme?")
    axs[0,1].bar(list(code_comments_cmp_amount.keys()), list(code_comments_cmp_amount.values()))
    axs[0,1].set(xlabel="Does a project have comments?")
    axs[1,0].bar(list(wiki_present_cmp_amount.keys()), list(wiki_present_cmp_amount.values()))
    axs[1,0].set(xlabel="Does a project have a wiki?")
    axs[1,1].bar(list(website_linked_cmp_amount.keys()), list(website_linked_cmp_amount.values()))
    axs[1,1].set(xlabel="Does a project have a website?")
    fig.tight_layout()
    plt.show()

def generate_contributors_gained_plots():
    readme_contributors_per_period = amount_of_contributors_per_period("README_documentation", True)
    readme_contributors_per_period_false = amount_of_contributors_per_period("README_documentation", False)

    code_comments_contributors_per_period = amount_of_contributors_per_period("comments_in_code", True)
    code_comments_contributors_per_period_false = amount_of_contributors_per_period("comments_in_code", False)

    wiki_present_contributors_per_period = amount_of_contributors_per_period("wiki_present", True)
    wiki_present_contributors_per_period_false = amount_of_contributors_per_period("wiki_present", False)

    website_linked_contributors_per_period = amount_of_contributors_per_period("website_linked", True)
    website_linked_contributors_per_period_false = amount_of_contributors_per_period("website_linked", False)

    fig, axs = plt.subplots(2, 2)
    fig.text(0, 0.5, "Contributors gained per period", va="center", rotation="vertical")
    axs[0, 0].plot(list(readme_contributors_per_period.keys()), list(readme_contributors_per_period.values()), label='yes')
    axs[0, 0].plot(list(readme_contributors_per_period_false.keys()), list(readme_contributors_per_period_false.values()), label='no')
    axs[0, 0].legend()  # Add legend to the first subplot
    axs[0, 0].set(xlabel="Does a project have a Readme?")
    axs[0, 1].plot(list(code_comments_contributors_per_period.keys()), list(code_comments_contributors_per_period.values()), label='yes')
    axs[0, 1].plot(list(code_comments_contributors_per_period_false.keys()), list(code_comments_contributors_per_period_false.values()), label='no')
    axs[0, 1].set(xlabel="Does a project have comments?")
    axs[0, 1].legend()  # Add legend to the first subplot
    axs[1, 0].plot(list(wiki_present_contributors_per_period.keys()), list(wiki_present_contributors_per_period.values()), label='yes')
    axs[1, 0].plot(list(wiki_present_contributors_per_period_false.keys()), list(wiki_present_contributors_per_period_false.values()), label='no')
    axs[1, 0].set(xlabel="Does a project have a wiki?")
    axs[1, 0].legend()  # Add legend to the first subplot
    axs[1, 1].plot(list(website_linked_contributors_per_period.keys()), list(website_linked_contributors_per_period.values()), label='yes')
    axs[1, 1].plot(list(website_linked_contributors_per_period_false.keys()), list(website_linked_contributors_per_period_false.values()), label='no')
    axs[1, 1].set(xlabel="Does a project have a website?")
    axs[1, 1].legend()  # Add legend to the first subplot
    fig.tight_layout()
    plt.show()


def generate_contributor_group_plots():
    readme_contributors_per_group = amount_per_contributor_group("README_documentation", True)
    readme_contributors_per_group_false = amount_per_contributor_group("README_documentation", False)

    code_comments_contributors_per_group = amount_per_contributor_group("comments_in_code", True)
    code_comments_contributors_per_group_false = amount_per_contributor_group("comments_in_code", False)

    wiki_present_contributors_per_group = amount_per_contributor_group("wiki_present", True)
    wiki_present_contributors_per_group_false = amount_per_contributor_group("wiki_present", False)

    website_linked_contributors_per_group = amount_per_contributor_group("website_linked", True)
    website_linked_contributors_per_group_false = amount_per_contributor_group("website_linked", False)

    dev_groups = ["New dev", "Contributing dev", "Core dev"]
    fig, axs = plt.subplots(2, 2)
    fig.text(0, 0.5, "Contributors per developer group", va="center", rotation="vertical")
    axs[0, 0].set_yscale('log')
    axs[0, 0].plot(dev_groups, readme_contributors_per_group, label="true")
    axs[0, 0].plot(dev_groups, readme_contributors_per_group_false, label="false")
    axs[0, 0].legend()  # Add legend to the first subplot
    axs[0, 0].set(xlabel="Does a project have a Readme?")
    axs[0, 1].set_yscale('log')
    axs[0, 1].plot(dev_groups, code_comments_contributors_per_group, label="true")
    axs[0, 1].plot(dev_groups, code_comments_contributors_per_group_false, label="false")
    axs[0, 1].legend()  # Add legend to the first subplot
    axs[0, 1].set(xlabel="Does a project have comments?")
    axs[1, 0].set_yscale('log')
    axs[1, 0].plot(dev_groups, wiki_present_contributors_per_group, label="true")
    axs[1, 0].plot(dev_groups, wiki_present_contributors_per_group_false, label="false")
    axs[1, 0].legend()  # Add legend to the first subplot
    axs[1, 0].set(xlabel="Does a project have a wiki?")
    axs[1, 1].set_yscale('log')
    axs[1, 1].plot(dev_groups, website_linked_contributors_per_group, label="true")
    axs[1, 1].plot(dev_groups, website_linked_contributors_per_group_false, label="false")
    axs[1, 1].legend()  # Add legend to the first subplot
    axs[1, 1].set(xlabel="Does a project have a website?")
    # ot
    fig.tight_layout()
    plt.show()

if __name__ == "__main__":
    generate_merge_time_plot_multiple_documentation_types()