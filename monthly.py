"""Build monthly.json: commits per contributor per month across all GNOME-Nepal repos.

Output shape (deterministic, so it only changes when the underlying data does):
{
  "months": {
    "2026-11": [
      {"login": "...", "html_url": "...", "avatar_url": "...", "commits": 12},
      ...  # sorted by commits desc, then login
    ],
    ...
  }
}

Months are UTC calendar months of each commit's author date, counting commits on
each repository's default branch. Merge commits, commits without a linked GitHub
user (e.g. the automated "refreshing contributor list" commits) and bot accounts
are skipped.
On any API error the script exits without writing, so a partial file is never committed.
"""

import json
import os
import sys
from collections import defaultdict

import requests

ORG_NAME = "GNOME-Nepal"
BASE_URL = "https://api.github.com"
OUTPUT = "monthly.json"
IGNORED_LOGINS = {"actions-user"}

session = requests.Session()
session.headers.update(
    {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {os.getenv('MAINTAINERS_POLLING_TOKEN')}",
    }
)


def get_all(url, params=None, allow_empty_repo=False):
    """Fetch every page of a GitHub list endpoint, or exit on error."""
    items = []
    params = {"per_page": 100, **(params or {})}
    while url:
        response = session.get(url, params=params, timeout=30)
        if allow_empty_repo and response.status_code == 409:  # repository is empty
            return []
        if response.status_code != 200:
            sys.exit(f"GET {response.url} failed: {response.status_code} {response.text[:200]}")
        items.extend(response.json())
        url = response.links.get("next", {}).get("url")
        params = None  # the "next" URL already carries the query string
    return items


def main():
    repos = get_all(f"{BASE_URL}/orgs/{ORG_NAME}/repos")

    counts = defaultdict(lambda: defaultdict(int))  # month -> login -> commits
    users = {}  # login -> profile info

    for repo in repos:
        commits = get_all(
            f"{BASE_URL}/repos/{ORG_NAME}/{repo['name']}/commits", allow_empty_repo=True
        )
        for commit in commits:
            if len(commit.get("parents", [])) > 1:
                continue  # merge commits ("Merge pull request #..."), not authored work
            author = commit.get("author")
            if not author or author.get("type") != "User" or author["login"] in IGNORED_LOGINS:
                continue
            month = commit["commit"]["author"]["date"][:7]  # "YYYY-MM" (ISO 8601, UTC)
            counts[month][author["login"]] += 1
            users[author["login"]] = {
                "login": author["login"],
                "html_url": author["html_url"],
                "avatar_url": author["avatar_url"],
            }

    months = {
        month: sorted(
            ({**users[login], "commits": n} for login, n in per_user.items()),
            key=lambda u: (-u["commits"], u["login"].lower()),
        )
        for month, per_user in sorted(counts.items())
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"months": months}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {OUTPUT}: {len(months)} months, {len(users)} contributors")


if __name__ == "__main__":
    main()
