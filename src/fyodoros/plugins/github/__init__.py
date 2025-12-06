import requests
from fyodoros.plugins import Plugin
from fyodoros.plugins.registry import PluginRegistry

class GithubPlugin(Plugin):
    """
    GitHub integration plugin.
    Features: list repos, create issues, view PRs.
    """
    def setup(self, kernel):
        self.kernel = kernel

    def get_token(self):
        return PluginRegistry().get_setting("github", "token")

    def get_headers(self):
        token = self.get_token()
        if not token:
            return None
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def list_repos(self, username=None):
        headers = self.get_headers()
        if not headers:
            return "Error: GitHub token not configured. Use 'fyodor plugin settings github token <YOUR_TOKEN>'."

        url = "https://api.github.com/user/repos" if not username else f"https://api.github.com/users/{username}/repos"
        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            repos = resp.json()
            return "\n".join([f"{r['full_name']} (Stars: {r['stargazers_count']})" for r in repos])
        except Exception as e:
            return f"Error listing repos: {e}"

    def create_issue(self, repo, title, body=""):
        headers = self.get_headers()
        if not headers:
            return "Error: GitHub token not configured."

        url = f"https://api.github.com/repos/{repo}/issues"
        data = {"title": title, "body": body}
        try:
            resp = requests.post(url, headers=headers, json=data)
            resp.raise_for_status()
            issue = resp.json()
            return f"Issue created: {issue['html_url']}"
        except Exception as e:
            return f"Error creating issue: {e}"

    def view_prs(self, repo, state="open"):
        headers = self.get_headers()
        if not headers:
            return "Error: GitHub token not configured."

        url = f"https://api.github.com/repos/{repo}/pulls?state={state}"
        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            prs = resp.json()
            if not prs:
                return "No PRs found."
            return "\n".join([f"#{p['number']} {p['title']} ({p['user']['login']}) - {p['html_url']}" for p in prs])
        except Exception as e:
            return f"Error viewing PRs: {e}"

    def get_shell_commands(self):
        return {
            "github_repos": self.list_repos,
            "github_issue": self.create_issue,
            "github_prs": self.view_prs
        }

    def get_agent_tools(self):
        # Tools description for the Agent
        return [
            {
                "name": "github_repos",
                "description": "List GitHub repositories. Args: username (optional)",
                "func": self.list_repos
            },
            {
                "name": "github_issue",
                "description": "Create a GitHub issue. Args: repo (owner/name), title, body",
                "func": self.create_issue
            },
            {
                "name": "github_prs",
                "description": "View Pull Requests. Args: repo (owner/name), state (open/closed/all)",
                "func": self.view_prs
            }
        ]
