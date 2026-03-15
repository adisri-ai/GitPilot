import os
import shutil
from backend.github.github_cli import run_git_command, git_commit_push

BASE_REPO_DIR = "repos"

# --- HELPER ---
def ensure_repo_cloned(repo_name):
    """Ensures the repo is cloned locally."""
    os.makedirs(BASE_REPO_DIR, exist_ok=True)
    repo_path = os.path.join(BASE_REPO_DIR, repo_name)

    if not os.path.exists(os.path.join(repo_path, ".git")):
        # Clean up empty folder if exists
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)
        
        # Clone
        clone_cmd = ["gh", "repo", "clone", repo_name, repo_path]
        out, err = run_git_command(clone_cmd)
        
        if not os.path.exists(repo_path):
            raise Exception(f"Failed to clone repo: {err}")
            
        # Configure Identity for the agent
        run_git_command(["git", "config", "user.email", "agent@gitpilot.ai"], cwd=repo_path)
        run_git_command(["git", "config", "user.name", "GitPilot Agent"], cwd=repo_path)

    return repo_path

def run_gh_command(command: list):
    """Helper to run generic GH CLI commands."""
    cmd = ["gh"] + command
    out, err = run_git_command(cmd)
    if err and "error" in err.lower() and "warning" not in err.lower():
        return {"error": err.strip()}
    return {"output": out.strip(), "message": "Command executed successfully"}

# ----------------------
# REPO MANAGEMENT
# ----------------------
def create_repo(repo_name, private=False):
    visibility = "--private" if private else "--public"
    return run_gh_command(["repo", "create", repo_name, visibility, "--confirm", "--add-readme"])

def delete_repo(repo_name):
    return run_gh_command(["repo", "delete", repo_name, "--yes"])

def fork_repo(repo_name):
    return run_gh_command(["repo", "fork", repo_name, "--clone=false"])

def star_repo(repo_name):
    # 'gh repo archive' is different, using api for star
    return run_gh_command(["api", f"user/starred/{repo_name}", "-X", "PUT"])

def watch_repo(repo_name):
    return run_gh_command(["repo", "watch", repo_name])

def unwatch_repo(repo_name):
    return run_gh_command(["api", f"repos/{repo_name}/subscription", "-X", "DELETE"])

# ----------------------
# FILE MANAGEMENT
# ----------------------
def add_file(repo_name, file_path, content, commit_message="Add file via GitPilot"):
    try:
        repo_path = ensure_repo_cloned(repo_name)
        full_path = os.path.join(repo_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content if content else "")
            
        git_commit_push(repo_path, commit_message)
        return {"status": "success", "message": f"File {file_path} created."}
    except Exception as e:
        return {"error": str(e)}

def delete_file(repo_name, file_path, commit_message="Delete file via GitPilot"):
    try:
        repo_path = ensure_repo_cloned(repo_name)
        full_path = os.path.join(repo_path, file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            git_commit_push(repo_path, commit_message)
            return {"status": "success", "message": f"File {file_path} deleted."}
        return {"error": "File not found locally."}
    except Exception as e:
        return {"error": str(e)}

def update_file(repo_name, file_path, content, commit_message="Update file via GitPilot"):
    # Same as add_file logic (overwrite)
    return add_file(repo_name, file_path, content, commit_message)

# ----------------------
# BRANCHES
# ----------------------
def create_branch(repo_name, branch_name):
    try:
        repo_path = ensure_repo_cloned(repo_name)
        run_git_command(["git", "checkout", "-b", branch_name], cwd=repo_path)
        run_git_command(["git", "push", "-u", "origin", branch_name], cwd=repo_path)
        return {"status": "success", "message": f"Branch {branch_name} created."}
    except Exception as e:
        return {"error": str(e)}

def delete_branch(repo_name, branch_name):
    try:
        repo_path = ensure_repo_cloned(repo_name)
        run_git_command(["git", "push", "origin", "--delete", branch_name], cwd=repo_path)
        return {"status": "success", "message": f"Branch {branch_name} deleted."}
    except Exception as e:
        return {"error": str(e)}

def merge_branch(repo_name, head_branch, base_branch):
    # Uses GH API to merge branches via PR or direct merge usually requires checkout
    # Simplest way via CLI is to use `gh pr create --merge` or git commands
    # Here we do git merge
    try:
        repo_path = ensure_repo_cloned(repo_name)
        run_git_command(["git", "checkout", base_branch], cwd=repo_path)
        run_git_command(["git", "pull"], cwd=repo_path)
        run_git_command(["git", "merge", head_branch], cwd=repo_path)
        run_git_command(["git", "push"], cwd=repo_path)
        return {"status": "success", "message": f"Merged {head_branch} into {base_branch}."}
    except Exception as e:
        return {"error": str(e)}

# ----------------------
# PRs & ISSUES
# ----------------------
def create_pr(repo_name, title, body, head_branch, base_branch):
    return run_gh_command([
        "pr", "create", "--repo", repo_name, 
        "--title", title, "--body", body, 
        "--head", head_branch, "--base", base_branch
    ])

def merge_pr(repo_name, pr_number):
    return run_gh_command(["pr", "merge", str(pr_number), "--merge", "--repo", repo_name])

def close_pr(repo_name, pr_number):
    return run_gh_command(["pr", "close", str(pr_number), "--repo", repo_name])

def create_issue(repo_name, title, body):
    return run_gh_command(["issue", "create", "--repo", repo_name, "--title", title, "--body", body])

def close_issue(repo_name, issue_number):
    return run_gh_command(["issue", "close", str(issue_number), "--repo", repo_name])

def assign_issue(repo_name, issue_number, assignee):
    return run_gh_command(["issue", "edit", str(issue_number), "--add-assignee", assignee, "--repo", repo_name])

def add_label(repo_name, issue_number, label_name):
    return run_gh_command(["issue", "edit", str(issue_number), "--add-label", label_name, "--repo", repo_name])

def remove_label(repo_name, issue_number, label_name):
    return run_gh_command(["issue", "edit", str(issue_number), "--remove-label", label_name, "--repo", repo_name])

# ----------------------
# COLLABORATORS
# ----------------------
def add_collaborator(repo_name, username):
    return run_gh_command(["repo", "collaborator", "add", repo_name, username])

def remove_collaborator(repo_name, username):
    return run_gh_command(["repo", "collaborator", "remove", repo_name, username])

# ----------------------
# MISC
# ----------------------
def create_release(repo_name, release_tag, release_name, body):
    return run_gh_command(["release", "create", release_tag, "--repo", repo_name, "--title", release_name, "--notes", body])

def delete_release(repo_name, release_tag):
    return run_gh_command(["release", "delete", release_tag, "--repo", repo_name, "--yes"])

def trigger_workflow(repo_name, workflow_name):
    return run_gh_command(["workflow", "run", workflow_name, "--repo", repo_name])