import requests
from fyodoros.plugins import Plugin
from fyodoros.plugins.registry import PluginRegistry

class SlackNotifierPlugin(Plugin):
    """
    Slack integration plugin.
    Features: Send notifications to Slack.
    """
    def setup(self, kernel):
        self.kernel = kernel

    def get_webhook_url(self):
        return PluginRegistry().get_setting("slack_notifier", "webhook_url")

    def send_message(self, message):
        webhook_url = self.get_webhook_url()
        if not webhook_url:
            return "Error: Slack Webhook URL not configured. Use 'fyodor plugin settings slack_notifier webhook_url <URL>'."

        try:
            payload = {"text": message}
            resp = requests.post(webhook_url, json=payload)
            resp.raise_for_status()
            return "Message sent to Slack."
        except Exception as e:
            return f"Error sending message to Slack: {e}"

    def get_shell_commands(self):
        return {
            "slack": self.send_message
        }

    def get_agent_tools(self):
        return [
            {
                "name": "slack_notify",
                "description": "Send a message to Slack. Args: message",
                "func": self.send_message
            }
        ]
