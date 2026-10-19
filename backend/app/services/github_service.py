import os
from github import Github
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("REPO_NAME", "Kailash-18/OmniSight")

def create_pull_request_for_fix(
    run_id: str, 
    target_file: str, 
    file_content: str, 
    commit_message: str, 
    pr_title: str, 
    pr_body: str
) -> str:
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is missing.")

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)

    default_branch = repo.default_branch
    base_branch_ref = repo.get_branch(default_branch)

    branch_name = f"omnisight-fix-{run_id}"

    repo.create_git_ref(
        ref=f"refs/heads/{branch_name}",
        sha=base_branch_ref.commit.sha
    )

    try:
        file_node = repo.get_contents(target_file, ref=default_branch)
        repo.update_file(
            path=target_file,
            message=commit_message,
            content=file_content,
            sha=file_node.sha,
            branch=branch_name
        )
    except Exception:
        repo.create_file(
            path=target_file,
            message=commit_message,
            content=file_content,
            branch=branch_name
        )

    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base=default_branch
    )

    return pr.html_url