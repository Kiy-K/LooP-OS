import requests
from loop.plugins import Plugin
from loop.plugins.registry import PluginRegistry


class SlackNotifierPlugin(Plugin):
    """
    Slack integration plugin.
    Features: Send notifications to Slack.
    """
    def setup(self, kernel):
        """
        Initialize the plugin with the kernel.

        Args:
            kernel (Kernel): The active kernel instance.
        """
        self.kernel = kernel

    def get_webhook_url(self):
        """
        Retrieve the Slack webhook URL from settings.

        Returns:
            str: The webhook URL.
        """
        return PluginRegistry().get_setting("slack_notifier", "webhook_url")

    def send_message(self, message):
        """
        Send a message to Slack via webhook.

        Args:
            message (str): The text message to send.

        Returns:
            str: Success or error message.
        """
        webhook_url = self.get_webhook_url()
        if not webhook_url:
            return "Error: Slack Webhook URL not configured. Use 'loop plugin settings slack_notifier webhook_url <URL>'."

        try:
            payload = {"text": message}
            resp = requests.post(webhook_url, json=payload)
            resp.raise_for_status()
            return "Message sent to Slack."
        except Exception as e:
            return f"Error sending message to Slack: {e}"

    def get_shell_commands(self):
        """
        Register Slack shell commands.

        Returns:
            dict: Mapping of command names to functions.
        """
        return {
            "slack": self.send_message
        }

    def get_agent_tools(self):
        """
        Register Slack tools for the agent.

        Returns:
            list: List of tool dictionaries.
        """
        return [
            {
                "name": "slack_notify",
                "description": "Send a message to Slack. Args: message",
                "func": self.send_message
            }
        ]
