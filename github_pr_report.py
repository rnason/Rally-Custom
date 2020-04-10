###############
# Imports:    #
###############
# Import Pip Installed Modules:
from github import Github
from cloudmage.jinjautils import JinjaUtils
from progress.bar import Bar
from datetime import datetime
from atlassian import Confluence
import json
import os
import sys

# Get the current date
NOW = datetime.now()

# Set Access Tokens that will be used to fetch data from the Github API.
AUTH_TOKEN = os.environ["INPUT_REPO_TOKEN"]
NAMESPACE = os.environ["INPUT_REPO_NAMESPACE"]
VERBOSE = os.environ["INPUT_VERBOSE_MODE"]
IS_ORG = os.environ["INPUT_IS_ORGANIZATION"]
OPEN_THRESHOLD = os.environ["INPUT_OPEN_DAYS_THRESHOLD"]
NOTIFY = os.environ["INPUT_SEND_NOTIFICATIONS"]

# Actions likes to pass strings, so validate incoming datatypes
if isinstance(VERBOSE, str):
    VERBOSE = True if VERBOSE.lower() == "true" else False
if isinstance(IS_ORG, str):
    IS_ORG = True if IS_ORG.lower() == "true" else False
if isinstance(NOTIFY, str):
    NOTIFY = True if NOTIFY.lower() == "true" else False
OPEN_THRESHOLD = int(OPEN_THRESHOLD)

# Carry on... Nothing to see here
print("\n")
print(f"Constructing Search Query for {NAMESPACE} Repositories...\n")
print(f"Pull Request Open Days Threshold is set to {OPEN_THRESHOLD} days.")
print(f"Notifications Enabled: {NOTIFY}")
print(f"Verbose Mode Enabled: {VERBOSE}")

# Set Jinja Template and Output Paths
JinjaTemplatePath = os.path.join(os.getcwd(), 'templates')
JinjaOutputPath = os.path.join(os.getcwd(), 'reports')
JinjaOutputFile = "OpenPRs.html"

# Instantiate JinjaUtils Object and Load the Open PR Report Template.
try:
    JinjaObj = JinjaUtils(verbose=VERBOSE)
    JinjaObj.template_directory = JinjaTemplatePath
    JinjaObj.load = 'Github_Open_PR_Report.j2'
except Exception as e:
    print("An unexpected error occurred instantiating a new Jinja Object:\n")
    raise e

try:
    # Instantiate a Github object using the Github Personal Access Token.
    GithubObj = Github(AUTH_TOKEN, per_page=100)
except Exception as e:
    print("An unexpected error occurred instantiating a new Github Object:\n")
    raise e

    # Construct an object specifc to the desired Github Organization
    # Execute a search for all open pull requests
    # from the specified Github organizations account
    # Search filters can be found on githubs documentation page:
    # https://help.github.com/en/github/searching-for-information-on-github/ \
    # searching-issues-and-pull-requests
try:
    if IS_ORG:
        GithubOrgObj = GithubObj.get_organization(NAMESPACE)
        print("Searching Repository Type: Organization")
        Issues = GithubObj.search_issues(
            'is:unmerged',
            org=NAMESPACE,
            state='open',
            type='pr'
        )
    else:
        print("Searching Repository Type: User")
        Issues = GithubObj.search_issues(
            'is:unmerged',
            user=NAMESPACE,
            state='open',
            type='pr'
        )
except Exception as e:
    print("An unexpected error occurred querying the Github issues API:\n")
    raise e

# Construct a list to hold discovered PR data
OpenPullRequests = []

print(f"\nSearch Returned {Issues.totalCount} Open Pull Requests \
within {NAMESPACE} Repositories")

# If no results were returned then exit
if Issues.totalCount == 0:
    print("Exiting Workflow...")
    sys.exit()

print("Validating Search Results...\n")

ProgressBar = Bar('Processing', max=Issues.totalCount)

# For each returned issue, parse the desired data.
try:
    for issue in Issues:
        # Temp item data containers
        pull_request_dataset = {}
        pull_request_reviewers = []
        pull_request_comment = f"@{issue.user.login} "

        # Get pull request object
        PullRequestObj = issue.repository.get_pull(issue.number)

        # If the flagged Pull Request is merged, ignore it
        if (
            PullRequestObj.merged or
            PullRequestObj.merged_at is not None or
            PullRequestObj.merged_by is not None
        ):
            continue

        # Get designated pull request reviewers
        RequestedReviewersObj = PullRequestObj.get_review_requests()
        # Users
        for user in RequestedReviewersObj[0]:
            pull_request_reviewers.append(user.login)
            pull_request_comment += f"@{user.login} "
        # Teams
        for user in RequestedReviewersObj[1]:
            pull_request_reviewers.append(user.name)
            pull_request_comment += f"@{user.name} "

        # Get pull request reviews
        PullReviewsObj = PullRequestObj.get_reviews()
        if PullReviewsObj.totalCount > 0:
            for review in PullReviewsObj:
                pr_user = f"{review.user.login}: {review.state}"
                if review.user.login not in pull_request_comment:
                    pull_request_comment += f"@{review.user.login} "
                if review.user.login in pull_request_reviewers:
                    index = pull_request_reviewers.index(review.user.login)
                    pull_request_reviewers[index] = pr_user
                else:
                    pull_request_reviewers.append(pr_user)

        # Set the pull request age, and update the pull_request_dataset object
        issue_age = NOW - PullRequestObj.created_at

        # Set the Notification message:
        pull_request_comment += f"{issue.html_url} has been open for \
{OPEN_THRESHOLD} days or longer. Please review the pull request, \
and merge or close at the earliest convenience. This reminder notification \
will be sent daily until this open pull request has been resolved. \
Thank you."

        # If send_notifications true, create a mention comment on the PR
        if int(issue_age.days) > int(OPEN_THRESHOLD):
            if VERBOSE:
                print(f"{issue.html_url} Exceeded the Open Days Limit!")
                print("Constructing pull request notification comment:")
                print(f"\n{pull_request_comment}\n")
            if NOTIFY:
                PullRequestObj.create_issue_comment(pull_request_comment)
                if VERBOSE:
                    print("Notification comment published successfully!\n")
            else:
                if VERBOSE:
                    print("Notifications currently disabled: The constructed \
notification comment was not published to the pull request.\n")
        else:
            if VERBOSE:
                print(f"{issue.html_url} Within the Open Days Limit.\n")

        # Construct Required DataPoint Dictionary to render the report:
        pull_request_dataset.update(
            id=issue.id,
            repository=issue.repository.name,
            repository_url=issue.repository.html_url,
            number=issue.number,
            submitter=issue.user.login,
            reviewers=pull_request_reviewers,
            link=issue.html_url,
            title=issue.title,
            body=issue.body,
            created=PullRequestObj.created_at,
            age=issue_age,
            age_days=int(issue_age.days),
            state=PullRequestObj.state,
            is_merged=PullRequestObj.merged,
            merged=PullRequestObj.merged_at,
            mergable=PullRequestObj.mergeable,
            merge_state=PullRequestObj.mergeable_state,
            merged_by=PullRequestObj.merged_by,
            review_count=PullReviewsObj.totalCount,
            days_open_threshold=int(OPEN_THRESHOLD)
        )

        # Add the storage object to the OpenPullRequests list
        OpenPullRequests.append(pull_request_dataset)
        ProgressBar.next()

    ProgressBar.finish()

    if VERBOSE:
        print("Printing Collected Open Pull Request DataSet: ")
        for pr in OpenPullRequests:
            print(f"\n{pr}\n")

    print(
        f"""{len(OpenPullRequests)}/{Issues.totalCount} of the returned \
search results were verified as open pull requests.\n"""
    )
except Exception as e:
    print("An unexpected error occurred parsing the PR response dataset:\n")
    raise e

# Set the report path
REPORT = os.path.join(JinjaOutputPath, JinjaOutputFile)

# Render the JinjaObj Template with the collected data set.
try:
    print(f"Jinja is Rendering: {REPORT}...")
    JinjaObj.render(
        RepoNamespace=NAMESPACE,
        OpenPullRequests=OpenPullRequests
    )
except Exception as e:
    print("Jinja encountered an unexpected error attempting to render \
the Open Pull Request html report:\n")
    raise e

# Ensure that the output directory exists, and then render the report.
try:
    if not os.path.exists(JinjaOutputPath):
        os.mkdir(JinjaOutputPath)
except Exception as e:
    print(f"An unexpected error occurred attempting to create {REPORT}:\n")
    raise e

try:
    print(f"Jinja is Writing File: {REPORT}...")
    JinjaObj.write(
        output_directory=JinjaOutputPath,
        output_file=JinjaOutputFile,
        backup=False
    )
except Exception as e:
    print(f"Jinja encountered an unexpected error attempting to write \
the Open Pull Request html report to {REPORT}:\n")
    raise e

if os.path.isfile(REPORT):
    print(f"Jinja completed the generation of {REPORT} successfully!")
else:
    print("Jinja failed attempting to generate {Report}. \
Please enable verbose mode for additional details by passing \
'verbose_mode: true' into the github workflow yaml file!")

"""
Use the Confluence-CLI to update the CCOE Wiki
"""
# # Define the confluence-cli command to update the report page.
# try:
#     print("\nUpdating Confluence with latest dataset...\n")
#     CCOEWIKI = Confluence(
#         url="https://ccoewiki.tapestry.com",
#         username="rnason",
#         password="Engage2019!!"
#     )

#     Update = CCOEWIKI.update_page(
#         parent_id=None,
#         page_id=9175117,
#         title="Open Pull Requests",
#         body=JinjaObj.rendered
#     )
# except Exception as e:
#     print("An unexpected error occurred attempting to update the \
# Github Open Pull Requests Wiki (https://ccoewiki.tapestry.com):\n")
#     if VERBOSE:
#         print(f"\nException: {e}\n")
# finally:
#     if VERBOSE:
#         print("Update Response Received:\n")
#         print(json.dumps(Update, indent=4, sort_keys=True))
#         print("\n")

#     if Update.get('id') == 9175117 and Update.get('status') == "current":
#         print(f"Confluence has been updated successfully!")
#     else:
#         print(f"Confluence update attempt failed with return code \
# {Update.get('statusCode')}:")
#         print(f"\tReason: {Update.get('reason')}")
#         print(f"\tMessage: {Update.get('message')}")
#         print("\n\n")
