import configparser
from collections import defaultdict
from datetime import datetime, timedelta
from pymongo import MongoClient

PERIODS = 10


# Connect to MongoDB
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

def aggregate():
    mdb_config = load_mongodb_config()
    # MongoDB URI string
    mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client[mdb_config['dbname']]

    aggregated_data = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'first_pull_request': None, 'last_pull_request': None}))

    pull_requests = db.pull_requests

    # Iterate over pull requests
    for pr in pull_requests.find():
        project = pr['project']
        submitter = pr['submitter']
        created_at = pr['created_at']

        aggregated_data[project][submitter]['count'] += 1
        if not aggregated_data[project][submitter]['first_pull_request']:
            aggregated_data[project][submitter]['first_pull_request'] = created_at
        aggregated_data[project][submitter]['last_pull_request'] = created_at

    # Prepare final result
    final_result = []
    for project, submitters_data in aggregated_data.items():
        project_reviews = {
            "project": project,
            "submitters": []
        }
        for submitter, review_data in submitters_data.items():
            submitter_info = {
                "name": submitter,
                "contributions": review_data['count'],
                "first_pull_request": review_data['first_pull_request'],
                "last_pull_request": review_data['last_pull_request']
            }
            project_reviews["submitters"].append(submitter_info)
        final_result.append(project_reviews)

    projects = db.projects
    print(final_result)
    for project in final_result:
        query = {"github": {"$regex": project['project']}}
        projects.update_many(query, {"$set": {
            "submitters": project['submitters']
        }})


def get_contributors_gained():
    mdb_config = load_mongodb_config()
    # MongoDB URI string
    mongo_uri = f"mongodb://{mdb_config['user']}:{mdb_config['password']}@{mdb_config['host']}:{mdb_config['port']}/{mdb_config['dbname']}?authSource=admin"
    client = MongoClient(mongo_uri)
    db = client[mdb_config['dbname']]
    collection = db.pull_requests

    # Dictionary to store aggregated information
    aggregated_data = defaultdict(
        lambda: {'first_pr_date': None, 'last_pr_date': None, 'periods': lambda: {'start': None, 'end': None, 'count': None}})

    # Iterate over pull requests
    for pr in collection.find():
        project = pr['project']
        created_at = pr['created_at']

        if not aggregated_data[project]['last_pr_date']:
            aggregated_data[project]['last_pr_date'] = created_at
        aggregated_data[project]['first_pr_date'] = created_at

    # Prepare final result
    final_result = []
    for project, project_data in aggregated_data.items():
        project_info = {
            "project": project,
            "first_pr_date": project_data['first_pr_date'],
            "last_pr_date": project_data['last_pr_date']
        }
        final_result.append(project_info)

    # Divide the total duration into 5 periods
    for project_data in final_result:
        start_time = datetime.strptime(project_data['first_pr_date'], "%Y-%m-%dT%H:%M:%SZ")
        end_time = datetime.strptime(project_data['last_pr_date'], "%Y-%m-%dT%H:%M:%SZ")
        total_duration = (end_time - start_time).total_seconds()
        period_duration = total_duration / PERIODS

        # Create a list to store the periods
        periods = []
        contributor_names = []

        # Iterate to create 5 periods
        for i in range(PERIODS):
            # Calculate the start and end time of each period
            period_start = start_time + timedelta(seconds=i * period_duration)
            period_end = start_time + timedelta(seconds=(i + 1) * period_duration)

            project_name = project_data['project']
            period_contributor_count = 0

            # Query with specified conditions
            query = {
                "project": project_name
            }

            for pr in collection.find(query):
                created_at = datetime.strptime(pr['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                if period_start < created_at < period_end and pr['submitter'] not in contributor_names:
                    contributor_names.append(pr['submitter'])
                    period_contributor_count += 1

            period_info = {
                "start": datetime.strftime(period_start, "%Y-%m-%dT%H:%M:%SZ"),
                "end": datetime.strftime(period_end, "%Y-%m-%dT%H:%M:%SZ"),
                "count": period_contributor_count
            }

            # Append the period to the list
            periods.append(period_info)

        project_data['periods'] = periods

    projects = db.projects
    print(final_result)
    for project in final_result:
        query = {"github": {"$regex": project['project']}}
        projects.update_many(query, {"$set": {
            "first_pr_date": project['first_pr_date'],
            "last_pr_date": project['last_pr_date'],
            "periods": project['periods']
        }})


if __name__ == '__main__':
    get_contributors_gained()