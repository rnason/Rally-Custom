# Github Open Pull Request Scheduled Report Action

## Build Container

docker rmi github/search_prs:latest
docker build -t github/search_prs .

## Run Container

docker run -it --rm \
--name GithubSearch \
-h GithubSearch \
-e INPUT_REPO_TOKEN="{TOKEN}" \
-e INPUT_REPO_NAMESPACE="tapestryinc" \
-e INPUT_VERBOSE_MODE="false" \
-e INPUT_IS_ORGANIZATION="true" \
-e INPUT_OPEN_DAYS_THRESHOLD=5 \
-e INPUT_SEND_NOTIFICATIONS=false \
github/search_prs:latest

github/search_prs:latest

## More Documentation coming soon
