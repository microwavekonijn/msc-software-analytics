# msc-software-analytics

## overview
This Python codebase aims to analyze the dynamics of open-source collaboration, specifically focusing on small JavaScript projects hosted on GitHub. The primary objectives include understanding the impact of documentation on review speed, new contributor retention, and overall project dynamics.

## Problem and Objectives:
The increasing interconnectedness of the world has led to a rise in global collaboration in software development. However, understanding the factors that enhance or hinder this collaboration is crucial. This project seeks to address the following objectives:

Investigate the influence of documentation on review speed and new contributor retention.
Explore the relationship between documentation types and project dynamics.
Provide insights into the role of documentation in fostering global collaboration in open-source projects.
Summary of Findings:
The findings suggest that while documentation does play a role in project dynamics, its impact on collaboration metrics is nuanced. Despite initial expectations, no clear correlation emerged between the presence of documentation and collaboration metrics such as review speed and new contributor retention.

## Methodology
The methodology employed in this analysis is detailed below, providing explanations for methodological choices.

### Data Collection:
Utilized the GitHub API to gather pull request data from small JavaScript projects.
Filtered projects based on criteria such as download counts and pull request activity.
Stored data in a MongoDB collection for further analysis.

### Data Analysis and Visualization:

Analyzed documentation types and their impact on metrics such as review speed and new contributor retention.
Used pyplot for data manipulation, visualization, and statistical analysis.
Considered factors such as project size, pull request activity, and contributor dynamics.

Created graphs and visualizations using pyplot to illustrate findings.
Interpreted results to draw conclusions about the relationship between documentation and collaboration metrics.

### Documentation Enhancement:

Identified areas for potential improvement in project documentation based on findings.
Considered the implications of documentation on project scalability and developer understanding.

## Replication Instructions:
To replicate this study, follow these steps:

1. Clone this repository to your local machine.
2. Ensure Python and necessary libraries (e.g. matplotlib, pyplot, mongodb, datetime) are installed.
3. Retrieve GitHub API tokens for data collection (optional but recommended for larger-scale analysis).
4. Connect to your own MongoDB database.
5. Run github.py, update_projects.py and contributor_scripts.py in that order to store the data in MongoDB.
6. Customize analysis parameters in generate_graphs.py as needed for specific research objectives.