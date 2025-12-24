import requests
from loop.plugins import Plugin
from loop.plugins.registry import PluginRegistry


class GithubPlugin(Plugin):
    """
    GitHub integration plugin.
    Features: list repos, create issues, view PRs.
    """
    def setup(self, kernel):
        """
        Initialize the plugin with the kernel.

        Args:
            kernel (Kernel): The active kernel instance.
        """
        self.kernel = kernel

    def get_token(self):
        """
        Retrieve the GitHub API token from settings.

        Returns:
            str: The API token, or None if not set.
        """
        return PluginRegistry().get_setting("github", "token")

    def get_headers(self):
        """
        Construct request headers with authentication.

        Returns:
            dict: The headers dictionary, or None if token is missing.
        """
        token = self.get_token()
        if not token:
            return None
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def list_repos(self, username=None):
        """
        List repositories for the authenticated user or a specified user.

        Args:
            username (str, optional): The username to list repos for. Defaults to authenticated user.

        Returns:
            str: A formatted list of repositories or error message.
        """
        headers = self.get_headers()
        if not headers:
            return "Error: GitHub token not configured. Use 'loop plugin settings github token <YOUR_TOKEN>'."

        url = "https://api.github.com/user/repos" if not username else f"https://api.github.com/users/{username}/repos"
        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            repos = resp.json()
            return "\n".join([f"{r['full_name']} (Stars: {r['stargazers_count']})" for r in repos])
        except Exception as e:
            return f"Error listing repos: {e}"

    def create_issue(self, repo, title, body=""):
        """
        Create a new issue in a repository.

        Args:
            repo (str): The repository name (owner/repo).
            title (str): The issue title.
            body (str, optional): The issue body description.

        Returns:
            str: Success message with URL, or error message.
        """
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
        """
        View Pull Requests for a repository.

        Args:
            repo (str): The repository name (owner/repo).
            state (str, optional): PR state ('open', 'closed', 'all'). Defaults to 'open'.

        Returns:
            str: A list of PRs or error message.
        """
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
        """
        Register GitHub shell commands.

        Returns:
            dict: Mapping of command names to functions.
        """
        return {
            "github_repos": self.list_repos,
            "github_issue": self.create_issue,
            "github_prs": self.view_prs
        }

    def get_agent_tools(self):
        """
        Register GitHub tools for the agent.

        Returns:
            list: List of tool dictionaries.
        """
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
