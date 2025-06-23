"""
GitHub PR Scheduler - A tool to create and schedule GitHub pull requests.

This application provides a GUI interface to:
1. Create pull requests immediately
2. Schedule pull requests for later
3. Manage scheduled pull requests

Author: Ritaban Ghosh
License: MIT
"""

import os
import subprocess
import json
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from tkcalendar import Calendar, DateEntry
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Application Constants
APP_NAME = "GitHub PR Scheduler"
APP_VERSION = "1.0.0"
CONFIG_FILE = Path.home() / '.github_pr_scheduler.json'
MAX_HISTORY_ENTRIES = 10
DEFAULT_BASE_BRANCHES = ['main']

# Global State
class AppState:
    def __init__(self):
        self.scheduled_prs: Dict[int, Dict[str, Any]] = {}
        self.next_pr_id: int = 1
        self.history: Dict[str, list] = {
            'repos': [],
            'usernames': [],
            'branches': [],
            'titles': []
        }
        self.gui_instance = None

app_state = AppState()

# Configuration Management
class ConfigManager:
    """Handles loading, saving, and updating application configuration."""
    
    @staticmethod
    def load_config() -> None:
        """Load configuration and history from file."""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    app_state.scheduled_prs = data.get('scheduled_prs', {})
                    app_state.next_pr_id = data.get('next_pr_id', 1)
                    app_state.history = data.get('history', {
                        'repos': [],
                        'usernames': [],
                        'branches': [],
                        'titles': []
                    })
        except Exception as e:
            messagebox.showwarning("Configuration Warning", 
                                 f"Failed to load configuration: {str(e)}\n" 
                                 "Using default settings.")

    @staticmethod
    def save_config() -> None:
        """Save configuration and history to file."""
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump({
                    'scheduled_prs': app_state.scheduled_prs,
                    'next_pr_id': app_state.next_pr_id,
                    'history': app_state.history
                }, f, indent=2)
        except Exception as e:
            messagebox.showwarning("Save Configuration Error", 
                                 f"Failed to save configuration: {str(e)}")

    @staticmethod
    def update_history(field: str, value: str) -> None:
        """Update history for a specific field.
        
        Args:
            field: The history field to update ('repos', 'usernames', etc.)
            value: The value to add to the history
        """
        if field in app_state.history and value and value not in app_state.history[field]:
            app_state.history[field].insert(0, value)
            if len(app_state.history[field]) > MAX_HISTORY_ENTRIES:
                app_state.history[field].pop()
            ConfigManager.save_config()

# Pull Request Management
class PRManager:
    """Handles GitHub pull request operations and validation."""

    @staticmethod
    def validate_inputs(inputs: Dict[str, str]) -> bool:
        """Validate all required inputs before creating PR.
        
        Args:
            inputs: Dictionary containing PR creation fields
            
        Returns:
            bool: True if all required fields are present and valid
        """
        required_fields = {
            'Local Git Repo': inputs.get('repo_path', ''),
            'Origin Repository': inputs.get('repo', ''),
            'Forked Username': inputs.get('username', ''),
            'Forked Branch': inputs.get('branch', ''),
            'Base Branch': inputs.get('base', ''),
            'PR Title': inputs.get('title', '')
        }
        
        missing = [field for field, value in required_fields.items() if not value.strip()]
        if missing:
            messagebox.showerror(
                "Validation Error", 
                f"Please fill in the following required fields:\n{chr(10).join(missing)}"
            )
            return False
        return True

    @staticmethod
    def create_pr(git_repo_path: str, repo: str, head: str, base: str, 
                  title: str, body: str, pr_id: Optional[int] = None) -> bool:
        """Create a pull request using GitHub CLI.
        
        Args:
            git_repo_path: Path to local Git repository
            repo: Origin repository name (org/repo)
            head: Forked account's branch (username:branch)
            base: Origin repo branch (base branch)
            title: Title for the PR
            body: Body text for the PR
            pr_id: Optional ID for scheduled PRs
            
        Returns:
            bool: True if PR creation was successful
        """
        try:
            # Verify and change to the Git repository directory
            repo_path = Path(git_repo_path)
            if not (repo_path.exists() and (repo_path / '.git').exists()):
                messagebox.showerror(
                    "Repository Error", 
                    f"Invalid Git repository path: {git_repo_path}"
                )
                return False
                
            os.chdir(git_repo_path)

            # Construct and execute the GitHub CLI command
            command = [
                "gh", "pr", "create",
                "--repo", repo,
                "--head", head,
                "--base", base,
                "--title", title,
                "--body", body
            ]

            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                messagebox.showinfo(
                    "Success", 
                    f"Pull request {pr_id if pr_id else ''} created successfully!"
                )
                
                # Clean up scheduled PR if applicable
                if pr_id and pr_id in app_state.scheduled_prs:
                    del app_state.scheduled_prs[pr_id]
                    ConfigManager.save_config()
                return True
            else:
                messagebox.showerror(
                    "PR Creation Error", 
                    f"Failed to create PR {pr_id if pr_id else ''}:\n{result.stderr}"
                )
                return False

        except Exception as e:
            messagebox.showerror(
                "System Error", 
                f"An unexpected error occurred: {str(e)}"
            )
            return False

# Scheduler Management
class PRScheduler:
    """Handles scheduling and management of pull requests."""

    @staticmethod
    def schedule_pr(git_repo_path: str, repo: str, head: str, base: str, 
                   title: str, body: str, schedule_datetime: datetime) -> Optional[int]:
        """Schedule a pull request for creation at a specific time.
        
        Args:
            git_repo_path: Path to local Git repository
            repo: Origin repository name
            head: Forked branch reference
            base: Target branch
            title: PR title
            body: PR description
            schedule_datetime: When to create the PR
            
        Returns:
            Optional[int]: PR ID if scheduled successfully, None otherwise
        """
        delay = (schedule_datetime - datetime.now()).total_seconds()
        if delay <= 0:
            messagebox.showerror("Scheduling Error", "Scheduled time must be in the future.")
            return None

        # Create new PR entry
        pr_id = app_state.next_pr_id
        app_state.next_pr_id += 1

        # Store PR details
        app_state.scheduled_prs[pr_id] = {
            "repo": repo,
            "head": head,
            "base": base,
            "title": title,
            "body": body,
            "time": schedule_datetime,
            "git_repo_path": git_repo_path,
            "job": None
        }

        # Schedule the PR creation
        def create_scheduled_pr():
            if PRManager.create_pr(git_repo_path, repo, head, base, title, body, pr_id):
                ConfigManager.save_config()

        # Get GUI instance from app_state
        gui = app_state.gui_instance
        if gui:
            pr_job = gui.root.after(int(delay * 1000), create_scheduled_pr)
            app_state.scheduled_prs[pr_id]["job"] = pr_job
        else:
            app_state.scheduled_prs[pr_id]["job"] = None

        ConfigManager.save_config()
        messagebox.showinfo("Scheduling Success", 
                          f"PR #{pr_id} scheduled for {schedule_datetime.strftime('%Y-%m-%d %H:%M')}")
        return pr_id

    @staticmethod
    def cancel_scheduled_pr(pr_id: int) -> bool:
        """Cancel a scheduled pull request.
        
        Args:
            pr_id: ID of the PR to cancel
            
        Returns:
            bool: True if cancelled successfully
        """
        if pr_id not in app_state.scheduled_prs:
            return False

        # Cancel the scheduled job
        if app_state.scheduled_prs[pr_id].get("job"):
            gui = app_state.gui_instance
            if gui:
                gui.root.after_cancel(app_state.scheduled_prs[pr_id]["job"])

        # Remove from scheduled PRs
        del app_state.scheduled_prs[pr_id]
        ConfigManager.save_config()
        return True

    @staticmethod
    def reschedule_pr(pr_id: int, new_datetime: datetime) -> bool:
        """Reschedule an existing pull request.
        
        Args:
            pr_id: ID of the PR to reschedule
            new_datetime: New scheduled time
            
        Returns:
            bool: True if rescheduled successfully
        """
        if pr_id not in app_state.scheduled_prs:
            return False

        pr_details = app_state.scheduled_prs[pr_id]
        
        # Cancel current schedule
        PRScheduler.cancel_scheduled_pr(pr_id)
        
        # Create new schedule
        new_pr_id = PRScheduler.schedule_pr(
            pr_details["git_repo_path"],
            pr_details["repo"],
            pr_details["head"],
            pr_details["base"],
            pr_details["title"],
            pr_details["body"],
            new_datetime
        )
        
        return new_pr_id is not None

# UI Event Handlers
class UIEventHandler:
    """Handles UI events and user interactions."""

    @classmethod
    def browse_repo(cls, gui_instance) -> None:
        """Open directory browser for selecting local Git repository."""
        dir_path = filedialog.askdirectory()
        if dir_path:
            gui_instance.entry_repo_path.set(dir_path)

    @classmethod
    def create_pr_now(cls, gui_instance) -> None:
        """Handle 'Create PR Now' button click."""
        inputs = cls._get_input_values(gui_instance)
        if not PRManager.validate_inputs(inputs):
            return

        # Update history
        cls._update_input_history(gui_instance)

        # Create PR
        PRManager.create_pr(
            inputs["git_repo_path"],
            inputs["repo"],
            inputs["head"],
            inputs["base"],
            inputs["title"],
            inputs["body"]
        )

    @classmethod
    def schedule_pr(cls, gui_instance) -> None:
        """Handle 'Schedule PR' button click."""
        inputs = cls._get_input_values(gui_instance)
        if not PRManager.validate_inputs(inputs):
            return

        # Update history
        cls._update_input_history(gui_instance)

        # Get schedule time
        schedule_date = gui_instance.cal.get_date()
        schedule_hour = int(gui_instance.hour_spinbox.get())
        schedule_minute = int(gui_instance.minute_spinbox.get())

        schedule_datetime = datetime(
            schedule_date.year,
            schedule_date.month,
            schedule_date.day,
            schedule_hour,
            schedule_minute
        )

        # Schedule PR
        PRScheduler.schedule_pr(
            inputs["git_repo_path"],
            inputs["repo"],
            inputs["head"],
            inputs["base"],
            inputs["title"],
            inputs["body"],
            schedule_datetime
        )

    @classmethod
    def cancel_pr(cls, pr_id: int, gui_instance) -> None:
        """Cancel a scheduled pull request."""
        if PRScheduler.cancel_scheduled_pr(pr_id):
            cls.update_scheduled_prs(gui_instance)
            gui_instance.update_status(f"PR #{pr_id} cancelled successfully")

    @classmethod
    def edit_pr(cls, pr_id: int, gui_instance) -> None:
        """Edit a scheduled pull request."""
        if pr_id not in app_state.scheduled_prs:
            return

        new_date = gui_instance.cal.get_date()
        new_hour = int(gui_instance.hour_spinbox.get())
        new_minute = int(gui_instance.minute_spinbox.get())
        new_datetime = datetime(
            new_date.year,
            new_date.month,
            new_date.day,
            new_hour,
            new_minute
        )

        if PRScheduler.reschedule_pr(pr_id, new_datetime):
            cls.update_scheduled_prs(gui_instance)
            gui_instance.update_status(f"PR #{pr_id} rescheduled successfully")

    @classmethod
    def _update_input_history(cls, gui_instance) -> None:
        """Update history for input fields.
        
        Args:
            gui_instance: Instance of the GUI class containing the input widgets
        """
        ConfigManager.update_history('repos', gui_instance.entry_repo.get())
        ConfigManager.update_history('usernames', gui_instance.entry_fork_user.get())
        ConfigManager.update_history('branches', gui_instance.entry_fork_branch.get())
        ConfigManager.update_history('titles', gui_instance.entry_title.get())

    @classmethod
    def _get_input_values(cls, gui_instance) -> Dict[str, str]:
        """Get current values from input fields.
        
        Args:
            gui_instance: Instance of the GUI class containing the input widgets
            
        Returns:
            Dict[str, str]: Dictionary containing input field values
        """
        return {
            "git_repo_path": gui_instance.entry_repo_path.get(),
            "repo": gui_instance.entry_repo.get(),
            "head": f"{gui_instance.entry_fork_user.get()}:{gui_instance.entry_fork_branch.get()}",
            "base": gui_instance.entry_base.get(),
            "title": gui_instance.entry_title.get(),
            "body": gui_instance.entry_body.get("1.0", tk.END).strip()
        }

    @classmethod
    def update_scheduled_prs(cls, gui_instance) -> None:
        """Update the display of scheduled PRs.
        
        Args:
            gui_instance: Instance of the GUI class containing the frame_scheduled_prs widget
        """
        frame = gui_instance.frame_scheduled_prs
        for widget in frame.winfo_children():
            widget.destroy()  # Clear previous widgets

        if not app_state.scheduled_prs:
            ttk.Label(frame, text="No PRs scheduled", style='Info.TLabel').pack(pady=10)
            return

        # Create headers
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(header_frame, text="ID", width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="Title", width=30).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="Scheduled Time", width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(header_frame, text="Actions", width=15).pack(side=tk.LEFT, padx=5)

        ttk.Separator(frame, orient='horizontal').pack(fill='x', padx=5)

        for pr_id, details in app_state.scheduled_prs.items():
            pr_frame = ttk.Frame(frame)
            pr_frame.pack(fill="x", padx=5, pady=2)

            ttk.Label(pr_frame, text=f"#{pr_id}", width=5).pack(side=tk.LEFT, padx=5)
            ttk.Label(pr_frame, text=details['title'][:40], width=30).pack(side=tk.LEFT, padx=5)
            ttk.Label(pr_frame, text=details['time'].strftime('%Y-%m-%d %H:%M'), width=20).pack(side=tk.LEFT, padx=5)

            btn_frame = ttk.Frame(pr_frame)
            btn_frame.pack(side=tk.LEFT, padx=5)

            ttk.Button(btn_frame, text="Edit", style='Small.TButton', 
                     command=lambda pr_id=pr_id: UIEventHandler.edit_pr(pr_id, gui_instance)).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Cancel", style='Small.Danger.TButton',
                     command=lambda pr_id=pr_id: UIEventHandler.cancel_pr(pr_id, gui_instance)).pack(side=tk.LEFT, padx=2)

# GUI Setup and Management
class GUI:
    """Handles the main window and widget setup."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("800x600")
        
        # Set this instance in app_state
        app_state.gui_instance = self
        
        self.setup_styles()
        self.create_variables()
        self.create_widgets()
        self.setup_layout()
        
        # Load configuration and initialize display
        ConfigManager.load_config()
        UIEventHandler.update_scheduled_prs(self)

    def setup_styles(self) -> None:
        """Configure ttk styles for widgets."""
        self.style = ttk.Style()
        self.style.configure('Accent.TButton', background='#0066cc')
        self.style.configure('Small.TButton', padding=2)
        self.style.configure('Small.Danger.TButton', padding=2)
        self.style.configure('Info.TLabel', foreground='gray')

    def create_variables(self) -> None:
        """Create tkinter variables for widgets."""
        self.entry_repo_path = tk.StringVar()
        self.entry_repo = tk.StringVar()
        self.entry_fork_user = tk.StringVar()
        self.entry_fork_branch = tk.StringVar()
        self.entry_base = tk.StringVar()
        self.entry_title = tk.StringVar()

    def create_widgets(self) -> None:
        """Create all GUI widgets."""
        self.create_main_frames()
        self.create_input_fields()
        self.create_schedule_fields()
        self.create_action_buttons()
        self.create_scheduled_prs_view()
        self.create_status_bar()

    def create_main_frames(self) -> None:
        """Create main organizational frames."""
        self.frame_inputs = ttk.LabelFrame(self.root, text="PR Details", padding="10")
        self.frame_schedule = ttk.LabelFrame(self.root, text="Schedule", padding="10")
        self.frame_actions = ttk.Frame(self.root, padding="10")

    def create_input_fields(self) -> None:
        """Create input fields for PR details."""
        # Local Git Repo Path
        self.create_labeled_field(self.frame_inputs, 0, "Local Git Repo Path:", 
                                self.entry_repo_path, "Select your local Git repository directory")
        ttk.Button(self.frame_inputs, text="Browse", 
                  command=lambda: UIEventHandler.browse_repo(self)).grid(row=0, column=2, padx=5)

        # Origin Repository
        self.create_labeled_field(self.frame_inputs, 1, "Origin Repository (org/repo):", 
                                self.entry_repo, "Format: organization/repository", 
                                values=app_state.history['repos'])

        # Forked Account Username
        self.create_labeled_field(self.frame_inputs, 2, "Forked Account Username:", 
                                self.entry_fork_user, "Your GitHub username", 
                                values=app_state.history['usernames'])

        # Forked Branch
        self.create_labeled_field(self.frame_inputs, 3, "Forked Branch:", 
                                self.entry_fork_branch, "Your branch containing the changes", 
                                values=app_state.history['branches'])

        # Origin Base Branch
        self.create_labeled_field(self.frame_inputs, 4, "Origin Base Branch:", 
                                self.entry_base, "Target branch for the PR", 
                                values=DEFAULT_BASE_BRANCHES)

        # PR Title
        self.create_labeled_field(self.frame_inputs, 5, "PR Title:", 
                                self.entry_title, "Brief description of your changes", 
                                values=app_state.history['titles'])

        # PR Body
        tk.Label(self.frame_inputs, text="PR Body:").grid(row=6, column=0, sticky="e", padx=5)
        self.entry_body = tk.Text(self.frame_inputs, width=60, height=4)
        self.entry_body.grid(row=6, column=1, sticky="ew", padx=5)
        self.create_tooltip(self.frame_inputs, 6, "Detailed description of your changes")

    def create_schedule_fields(self) -> None:
        """Create date and time selection widgets."""
        # Date selector
        tk.Label(self.frame_schedule, text="Schedule Date:").grid(row=0, column=0, sticky="e", padx=5)
        self.cal = DateEntry(self.frame_schedule, width=12, background='darkblue',
                           foreground='white', borderwidth=2, date_pattern="dd-mm-yyyy")
        self.cal.grid(row=0, column=1, sticky="w", padx=5)
        self.create_tooltip(self.frame_schedule, 0, "(DD-MM-YYYY format)")

        # Time selector
        tk.Label(self.frame_schedule, text="Schedule Time:").grid(row=1, column=0, sticky="e", padx=5)
        frame_time = ttk.Frame(self.frame_schedule)
        frame_time.grid(row=1, column=1, sticky="w", padx=5)

        self.hour_spinbox = ttk.Spinbox(frame_time, from_=0, to=23, width=2, format="%02.0f")
        self.hour_spinbox.pack(side=tk.LEFT)
        ttk.Label(frame_time, text=":").pack(side=tk.LEFT)
        self.minute_spinbox = ttk.Spinbox(frame_time, from_=0, to=59, width=2, format="%02.0f")
        self.minute_spinbox.pack(side=tk.LEFT)
        self.create_tooltip(self.frame_schedule, 1, "(24-hr format)")

    def create_action_buttons(self) -> None:
        """Create action buttons."""
        ttk.Button(self.frame_actions, text="Create PR Now", 
                  command=lambda: UIEventHandler.create_pr_now(self), 
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(self.frame_actions, text="Schedule PR", 
                  command=lambda: UIEventHandler.schedule_pr(self)).pack(side=tk.LEFT, padx=5)

    def create_scheduled_prs_view(self) -> None:
        """Create the scheduled PRs display area."""
        # Container frame
        self.frame_scheduled_prs_container = ttk.LabelFrame(
            self.root, text="Scheduled Pull Requests", padding="10")

        # Scrollable canvas setup
        self.canvas = tk.Canvas(self.frame_scheduled_prs_container)
        self.scrollbar = ttk.Scrollbar(
            self.frame_scheduled_prs_container, orient="vertical", command=self.canvas.yview)
        self.frame_scheduled_prs = ttk.Frame(self.canvas)

        # Configure scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas_frame = self.canvas.create_window(
            (0, 0), window=self.frame_scheduled_prs, anchor="nw")

        # Bind events for proper scrolling behavior
        self.frame_scheduled_prs.bind("<Configure>", self.configure_scroll_region)
        self.canvas.bind("<Configure>", 
                        lambda e: self.canvas.itemconfig(self.canvas_frame, width=self.canvas.winfo_width()))

    def create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)

    def setup_layout(self) -> None:
        """Arrange all widgets in the main window."""
        # Main frames
        self.frame_inputs.pack(fill="x", padx=10, pady=5)
        self.frame_schedule.pack(fill="x", padx=10, pady=5)
        self.frame_actions.pack(fill="x", padx=10, pady=5)

        # Scheduled PRs view
        self.frame_scheduled_prs_container.pack(fill="both", expand=True, padx=10, pady=5)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Status bar
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_labeled_field(self, parent: ttk.Frame, row: int, label: str, 
                           variable: tk.Variable, tooltip: str, values: list = None) -> None:
        """Create a labeled field with optional combobox and tooltip."""
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=5)
        if values is not None:
            ttk.Combobox(parent, textvariable=variable, width=60, 
                        values=values).grid(row=row, column=1, sticky="ew", padx=5)
        else:
            ttk.Entry(parent, textvariable=variable, 
                     width=60).grid(row=row, column=1, sticky="ew", padx=5)
        self.create_tooltip(parent, row, tooltip)

    def create_tooltip(self, parent: ttk.Frame, row: int, text: str) -> None:
        """Create a tooltip that appears on hover."""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(tooltip, text=text, justify=tk.LEFT,
                              background="#ffffe0", relief=tk.SOLID, borderwidth=1)
            label.pack()
            
            def hide_tooltip(event=None):
                tooltip.destroy()
                widget.bind('<Leave>', lambda e: None)
            
            tooltip.bind('<Leave>', hide_tooltip)
            widget.bind('<Leave>', hide_tooltip)
            
        widget = parent.grid_slaves(row=row, column=0)[0]
        widget.bind('<Enter>', show_tooltip)

    def configure_scroll_region(self, event: tk.Event) -> None:
        """Update scroll region when frame size changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.itemconfig(self.canvas_frame, width=self.canvas.winfo_width())

    def update_status(self, message: str) -> None:
        """Update status bar message."""
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def run(self) -> None:
        """Start the GUI main loop."""
        self.root.mainloop()

# Create and run the application
app = GUI()
app.run()
