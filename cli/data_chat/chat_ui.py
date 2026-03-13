"""Chat UI for terminal-based conversational data exploration."""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

from cli.data_chat.chat_agent import DataChatAgent


class DataChatUI:
    """Rich-based terminal UI for conversational data exploration."""

    COMMANDS = {
        "/exit": "Exit the chat session",
        "/quit": "Exit the chat session",
        "/reports": "List available reports",
        "/summary": "Get a high-level summary of the analysis",
        "/clear": "Clear conversation history",
        "/help": "Show available commands",
    }

    def __init__(self, console: Console, chat_agent: DataChatAgent, ticker: str, analysis_date: str):
        """Initialize the chat UI.

        Args:
            console: Rich console instance
            chat_agent: The chat agent for processing questions
            ticker: The ticker symbol being analyzed
            analysis_date: The date of the analysis
        """
        self.console = console
        self.chat_agent = chat_agent
        self.ticker = ticker
        self.analysis_date = analysis_date

    def _display_welcome(self):
        """Display welcome message and available commands."""
        context_summary = self.chat_agent.data_accessor.get_context_summary()

        welcome_text = f"""[bold green]Chat with Your Analysis Data[/bold green]

Ask questions about the {self.ticker} analysis from {self.analysis_date}.

[bold]Available Data:[/bold]
{context_summary}
[bold]Commands:[/bold]
  /summary  - Get a high-level summary
  /reports  - List available reports
  /clear    - Clear conversation history
  /help     - Show all commands
  /exit     - Exit chat

[dim]Type your question and press Enter.[/dim]"""

        self.console.print(Panel(welcome_text, title="Data Chat", border_style="green"))
        self.console.print()

    def _display_response(self, response: str):
        """Display an AI response."""
        self.console.print(Panel(
            Markdown(response),
            title="Answer",
            border_style="blue",
            padding=(1, 2)
        ))
        self.console.print()

    def _display_reports(self):
        """Display list of available reports."""
        reports = self.chat_agent.data_accessor.get_available_reports()
        reports_text = "[bold]Available Reports:[/bold]\n"
        for report in reports:
            reports_text += f"  - {report}\n"
        reports_text += "\n[dim]You can ask about any of these reports.[/dim]"
        self.console.print(Panel(reports_text, title="Reports", border_style="cyan"))
        self.console.print()

    def _display_help(self):
        """Display help information."""
        help_text = "[bold]Available Commands:[/bold]\n"
        for cmd, desc in self.COMMANDS.items():
            help_text += f"  {cmd:12} - {desc}\n"
        help_text += "\n[bold]Example Questions:[/bold]\n"
        help_text += "  - What was the overall sentiment?\n"
        help_text += "  - Why did the portfolio manager make this decision?\n"
        help_text += "  - What were the key technical indicators?\n"
        help_text += "  - Summarize the bull vs bear debate\n"
        help_text += "  - What were the main risk factors?\n"
        self.console.print(Panel(help_text, title="Help", border_style="yellow"))
        self.console.print()

    def _handle_command(self, command: str) -> bool:
        """Handle a command.

        Args:
            command: The command string (starting with /)

        Returns:
            True if should continue, False if should exit
        """
        cmd = command.lower().strip()

        if cmd in ("/exit", "/quit"):
            self.console.print("[dim]Exiting chat...[/dim]")
            return False

        elif cmd == "/reports":
            self._display_reports()

        elif cmd == "/summary":
            self.console.print("[dim]Generating summary...[/dim]")
            summary = self.chat_agent.get_summary()
            self._display_response(summary)

        elif cmd == "/clear":
            self.chat_agent.clear_history()
            self.console.print("[dim]Conversation history cleared.[/dim]\n")

        elif cmd == "/help":
            self._display_help()

        else:
            self.console.print(f"[yellow]Unknown command: {cmd}. Type /help for available commands.[/yellow]\n")

        return True

    def run_chat_loop(self):
        """Run the main chat interaction loop."""
        self._display_welcome()

        while True:
            try:
                # Get user input
                user_input = self.console.input("[bold green]You:[/bold green] ").strip()

                if not user_input:
                    continue

                # Check for commands
                if user_input.startswith("/"):
                    if not self._handle_command(user_input):
                        break
                    continue

                # Process question
                self.console.print("[dim]Thinking...[/dim]")
                response = self.chat_agent.ask(user_input)
                self._display_response(response)

            except KeyboardInterrupt:
                self.console.print("\n[dim]Exiting chat...[/dim]")
                break
            except EOFError:
                self.console.print("\n[dim]Exiting chat...[/dim]")
                break
