import os
import subprocess
import json
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from tkcalendar import DateEntry
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Constants
CONFIG_FILE = Path.home() / '.github_pr_scheduler.json'
MAX_HISTORY_ENTRIES = 10

# Dictionary to hold scheduled PRs and history
scheduled_prs: Dict[int, Dict[str, Any]] = {}
next_pr_id = 1
history: Dict[str, list] = {
    'repos': [],
    'usernames': [],
    'branches': [],
    'titles': []
}

def load_config():
    """Load configuration and history from file."""
    global scheduled_prs, next_pr_id, history
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                scheduled_prs = data.get('scheduled_prs', {})
                next_pr_id = data.get('next_pr_id', 1)
                history = data.get('history', {
                    'repos': [],
                    'usernames': [],
                    'branches': [],
                    'titles': []
                })
    except Exception as e:
        messagebox.showwarning("Warning", f"Failed to load configuration: {str(e)}")

def save_config():
    """Save configuration and history to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                'scheduled_prs': scheduled_prs,
                'next_pr_id': next_pr_id,
                'history': history
            }, f)
    except Exception as e:
        messagebox.showwarning("Warning", f"Failed to save configuration: {str(e)})")

def update_history(field: str, value: str):
    """Update history for a specific field."""
    if field in history and value and value not in history[field]:
        history[field].insert(0, value)
        if len(history[field]) > MAX_HISTORY_ENTRIES:
            history[field].pop()
        save_config()

# Function to create a PR using GitHub CLI
def validate_inputs() -> bool:
    """Validate all required inputs before creating PR."""
    required_fields = {
        'Local Git Repo': entry_repo_path.get(),
        'Origin Repository': entry_repo.get(),
        'Forked Username': entry_fork_user.get(),
        'Forked Branch': entry_fork_branch.get(),
        'Base Branch': entry_base.get(),
        'PR Title': entry_title.get()
    }
    
    missing = [field for field, value in required_fields.items() if not value.strip()]
    if missing:
        messagebox.showerror("Error", f"Please fill in the following required fields:\n{chr(10).join(missing)}")
        return False
    return True

def create_pr(git_repo_path, repo, head, base, title, body, pr_id=None):
    """
    This function changes to the specified Git repository directory,
    then uses the GitHub CLI (`gh`) to create a pull request.
    """
    try:
        os.chdir(git_repo_path)  # Change directory to the local Git repository
    except FileNotFoundError:
        messagebox.showerror("Error", f"Invalid Git repository path: {git_repo_path}")
        return

    # Construct the gh CLI command to create a pull request
    command = [
        "gh", "pr", "create",
        "--repo", repo,      # Origin repo name (org/repo)
        "--head", head,      # Forked account's branch
        "--base", base,      # Origin repo branch (base branch)
        "--title", title,    # Title for the PR
        "--body", body       # Body text for the PR
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        messagebox.showinfo("Success", f"Pull request {pr_id} created successfully!")
    else:
        messagebox.showerror("Error", f"Failed to create PR {pr_id}: {result.stderr}")

    if pr_id:
        del scheduled_prs[pr_id]  # Remove from scheduled PRs once executed
        update_scheduled_prs()

# Schedule the PR creation task at a specific time
def schedule_task(git_repo_path, repo, head, base, title, body, schedule_datetime, pr_id):
    def task():
        create_pr(git_repo_path, repo, head, base, title, body, pr_id)

    delay = (schedule_datetime - datetime.now()).total_seconds()
    if delay > 0:
        pr_job = root.after(int(delay * 1000), task)
        
        # Safely assign the job to the dictionary entry
        if pr_id in scheduled_prs:
            scheduled_prs[pr_id]["job"] = pr_job

        update_scheduled_prs()
        messagebox.showinfo("Info", f"PR {pr_id} scheduled for {schedule_datetime}.")
    else:
        messagebox.showerror("Error", "Scheduled time must be in the future.")


# Browse for local Git repo
def browse_repo():
    dir_path = filedialog.askdirectory()
    if dir_path:
        entry_repo_path.set(dir_path)

# Handle "Run Now" button click
def run_now():
    if not validate_inputs():
        return
        
    # Update history
    update_history('repos', entry_repo.get())
    update_history('usernames', entry_fork_user.get())
    update_history('branches', entry_fork_branch.get())
    update_history('titles', entry_title.get())
    git_repo_path = entry_repo_path.get()   # Local Git repository path
    repo = entry_repo.get()                 # Origin repository (org/repo)
    head = f"{entry_fork_user.get()}:{entry_fork_branch.get()}"  # Forked branch (username:branch)
    base = entry_base.get()                 # Base branch (origin branch)
    title = entry_title.get()               # PR title
    body = entry_body.get()                 # PR body

    create_pr(git_repo_path, repo, head, base, title, body)

# Handle "Schedule" button click
def schedule_task_gui():
    if not validate_inputs():
        return
        
    # Update history
    update_history('repos', entry_repo.get())
    update_history('usernames', entry_fork_user.get())
    update_history('branches', entry_fork_branch.get())
    update_history('titles', entry_title.get())
    global next_pr_id
    git_repo_path = entry_repo_path.get()
    repo = entry_repo.get()
    head = f"{entry_fork_user.get()}:{entry_fork_branch.get()}"
    base = entry_base.get()
    title = entry_title.get()
    body = entry_body.get()

    schedule_date = cal.get_date()
    schedule_hour = int(hour_spinbox.get())
    schedule_minute = int(minute_spinbox.get())

    schedule_datetime = datetime(schedule_date.year, schedule_date.month, schedule_date.day, schedule_hour, schedule_minute)

    # Create or edit the scheduled PR entry
    pr_id = next_pr_id
    next_pr_id += 1

    # Store the scheduled PR details in the dictionary
    scheduled_prs[pr_id] = {
        "repo": repo,
        "head": head,
        "base": base,
        "title": title,
        "body": body,
        "time": schedule_datetime,
        "job": None  # Initialize job as None, will assign after scheduling
    }

    # Schedule the task and assign the job to the dictionary
    schedule_task(git_repo_path, repo, head, base, title, body, schedule_datetime, pr_id)


    # Store the scheduled PR details
    pr_id = next_pr_id
    next_pr_id += 1
    scheduled_prs[pr_id] = {
        "repo": repo,
        "head": head,
        "base": base,
        "title": title,
        "body": body,
        "time": schedule_datetime,
    }

    schedule_task(git_repo_path, repo, head, base, title, body, schedule_datetime, pr_id)

# Update the display of scheduled PRs
def update_scheduled_prs():
    for widget in frame_scheduled_prs.winfo_children():
        widget.destroy()  # Clear previous widgets

    if not scheduled_prs:
        tk.Label(frame_scheduled_prs, text="No PRs scheduled").grid(row=0, column=0, columnspan=3)
        return

    row = 0
    for pr_id, details in scheduled_prs.items():
        pr_info = f"PR {pr_id}: {details['title']} - Scheduled for {details['time']}"
        
        # Display the PR details in a label
        lbl_pr = tk.Label(frame_scheduled_prs, text=pr_info)
        lbl_pr.grid(row=row, column=0, sticky="w", padx=10, pady=5)  # Left-align the label

        # Edit button
        btn_edit = tk.Button(frame_scheduled_prs, text="Edit", command=lambda pr_id=pr_id: edit_pr(pr_id))
        btn_edit.grid(row=row, column=1, padx=5, pady=5)

        # Cancel button
        btn_cancel = tk.Button(frame_scheduled_prs, text="Cancel", command=lambda pr_id=pr_id: cancel_pr(pr_id))
        btn_cancel.grid(row=row, column=2, padx=5, pady=5)

        row += 1  # Move to the next row for the next PR

# Cancel a scheduled PR
def cancel_pr(pr_id):
    if pr_id in scheduled_prs and scheduled_prs[pr_id]["job"] is not None:
        root.after_cancel(scheduled_prs[pr_id]["job"])
    del scheduled_prs[pr_id]
    update_scheduled_prs()

# Edit a scheduled PR
def edit_pr(pr_id):
    pr_details = scheduled_prs[pr_id]
    new_date = cal.get_date()  # For simplicity, just update time (similar to scheduling)
    new_hour = int(hour_spinbox.get())
    new_minute = int(minute_spinbox.get())
    new_datetime = datetime(new_date.year, new_date.month, new_date.day, new_hour, new_minute)

    cancel_pr(pr_id)  # Cancel current schedule
    schedule_task(entry_repo_path.get(), pr_details["repo"], pr_details["head"], pr_details["base"], pr_details["title"], pr_details["body"], new_datetime, pr_id)

# Create the main GUI window
root = tk.Tk()
root.title("GitHub PR Scheduler")
root.geometry("800x600")

# Create main frames for better organization
frame_inputs = ttk.LabelFrame(root, text="PR Details", padding="10")
frame_inputs.pack(fill="x", padx=10, pady=5)

frame_schedule = ttk.LabelFrame(root, text="Schedule", padding="10")
frame_schedule.pack(fill="x", padx=10, pady=5)

frame_actions = ttk.Frame(root, padding="10")
frame_actions.pack(fill="x", padx=10, pady=5)

# Load saved configuration
load_config()

# Local Git Repo Path
tk.Label(frame_inputs, text="Local Git Repo Path:").grid(row=0, column=0, sticky="e", padx=5)
entry_repo_path = tk.StringVar()
repo_path_entry = ttk.Combobox(frame_inputs, textvariable=entry_repo_path, width=60)
repo_path_entry.grid(row=0, column=1, sticky="ew", padx=5)
ttk.Button(frame_inputs, text="Browse", command=browse_repo).grid(row=0, column=2, padx=5)

# Add tooltip
repo_path_tooltip = ttk.Label(frame_inputs, text="Select your local Git repository directory")
repo_path_tooltip.grid(row=0, column=3, padx=5)
repo_path_tooltip.bind('<Enter>', lambda e: repo_path_tooltip.configure(foreground='blue'))
repo_path_tooltip.bind('<Leave>', lambda e: repo_path_tooltip.configure(foreground='black'))

# Origin Repo (org/repo)
tk.Label(frame_inputs, text="Origin Repository (org/repo):").grid(row=1, column=0, sticky="e", padx=5)
entry_repo = tk.StringVar()
repo_entry = ttk.Combobox(frame_inputs, textvariable=entry_repo, width=60, values=history['repos'])
repo_entry.grid(row=1, column=1, sticky="ew", padx=5)
repo_tooltip = ttk.Label(frame_inputs, text="Format: organization/repository")
repo_tooltip.grid(row=1, column=3, padx=5)

# Forked Account Username
tk.Label(frame_inputs, text="Forked Account Username:").grid(row=2, column=0, sticky="e", padx=5)
entry_fork_user = tk.StringVar()
fork_user_entry = ttk.Combobox(frame_inputs, textvariable=entry_fork_user, width=60, values=history['usernames'])
fork_user_entry.grid(row=2, column=1, sticky="ew", padx=5)
user_tooltip = ttk.Label(frame_inputs, text="Your GitHub username")
user_tooltip.grid(row=2, column=3, padx=5)

# Forked Branch
tk.Label(frame_inputs, text="Forked Branch:").grid(row=3, column=0, sticky="e", padx=5)
entry_fork_branch = tk.StringVar()
fork_branch_entry = ttk.Combobox(frame_inputs, textvariable=entry_fork_branch, width=60, values=history['branches'])
fork_branch_entry.grid(row=3, column=1, sticky="ew", padx=5)
branch_tooltip = ttk.Label(frame_inputs, text="Your branch containing the changes")
branch_tooltip.grid(row=3, column=3, padx=5)

# Origin Branch (base branch)
tk.Label(frame_inputs, text="Origin Base Branch:").grid(row=4, column=0, sticky="e", padx=5)
entry_base = tk.StringVar()
base_entry = ttk.Combobox(frame_inputs, textvariable=entry_base, width=60, values=['main', 'master', 'develop'])
base_entry.grid(row=4, column=1, sticky="ew", padx=5)
base_tooltip = ttk.Label(frame_inputs, text="Target branch for the PR")
base_tooltip.grid(row=4, column=3, padx=5)

# PR Title
tk.Label(frame_inputs, text="PR Title:").grid(row=5, column=0, sticky="e", padx=5)
entry_title = tk.StringVar()
title_entry = ttk.Combobox(frame_inputs, textvariable=entry_title, width=60, values=history['titles'])
title_entry.grid(row=5, column=1, sticky="ew", padx=5)
title_tooltip = ttk.Label(frame_inputs, text="Brief description of your changes")
title_tooltip.grid(row=5, column=3, padx=5)

# PR Body
tk.Label(frame_inputs, text="PR Body:").grid(row=6, column=0, sticky="e", padx=5)
entry_body = tk.Text(frame_inputs, width=60, height=4)
entry_body.grid(row=6, column=1, sticky="ew", padx=5)
body_tooltip = ttk.Label(frame_inputs, text="Detailed description of your changes")
body_tooltip.grid(row=6, column=3, padx=5)

# Date selector (calendar widget) and time selector (Spinbox)
tk.Label(frame_schedule, text="Schedule Date:").grid(row=0, column=0, sticky="e", padx=5)
cal = DateEntry(frame_schedule, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern="yyyy-mm-dd")
cal.grid(row=0, column=1, sticky="w", padx=5)
date_tooltip = ttk.Label(frame_schedule, text="Select date for PR creation")
date_tooltip.grid(row=0, column=2, padx=5)

# Time selector (Spinbox for hours and minutes)
tk.Label(frame_schedule, text="Schedule Time:").grid(row=1, column=0, sticky="e", padx=5)
frame_time = ttk.Frame(frame_schedule)
frame_time.grid(row=1, column=1, sticky="w", padx=5)
hour_spinbox = ttk.Spinbox(frame_time, from_=0, to=23, width=2, format="%02.0f")  # Hours
hour_spinbox.pack(side=tk.LEFT)
ttk.Label(frame_time, text=":").pack(side=tk.LEFT)
minute_spinbox = ttk.Spinbox(frame_time, from_=0, to=59, width=2, format="%02.0f")  # Minutes
minute_spinbox.pack(side=tk.LEFT)
time_tooltip = ttk.Label(frame_schedule, text="Set time in 24-hour format")
time_tooltip.grid(row=1, column=2, padx=5)

# Buttons to run the PR creation immediately or schedule it
btn_run_now = ttk.Button(frame_actions, text="Create PR Now", command=run_now, style='Accent.TButton')
btn_run_now.pack(side=tk.LEFT, padx=5)

btn_schedule = ttk.Button(frame_actions, text="Schedule PR", command=schedule_task_gui)
btn_schedule.pack(side=tk.LEFT, padx=5)

# Style configuration
style = ttk.Style()
style.configure('Accent.TButton', background='#0066cc')

# Frame for showing scheduled PRs
frame_scheduled_prs_container = ttk.LabelFrame(root, text="Scheduled Pull Requests", padding="10")
frame_scheduled_prs_container.pack(fill="both", expand=True, padx=10, pady=5)

# Add a scrollable frame for scheduled PRs
canvas = tk.Canvas(frame_scheduled_prs_container)
scrollbar = ttk.Scrollbar(frame_scheduled_prs_container, orient="vertical", command=canvas.yview)
frame_scheduled_prs = ttk.Frame(canvas)

# Configure scrolling
canvas.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

# Create a window inside the canvas for the frame
canvas_frame = canvas.create_window((0, 0), window=frame_scheduled_prs, anchor="nw")

# Update scroll region when frame size changes
def configure_scroll_region(event):
    canvas.configure(scrollregion=canvas.bbox("all"))
    # Update the canvas window size to match the frame width
    canvas.itemconfig(canvas_frame, width=canvas.winfo_width())

frame_scheduled_prs.bind("<Configure>", configure_scroll_region)
canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_frame, width=canvas.winfo_width()))

# Status bar
status_bar = ttk.Label(root, text="Ready", relief=tk.SUNKEN)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

def update_status(message):
    status_bar.config(text=message)
    root.update_idletasks()

# Override the update_scheduled_prs function
def update_scheduled_prs():
    for widget in frame_scheduled_prs.winfo_children():
        widget.destroy()  # Clear previous widgets

    if not scheduled_prs:
        ttk.Label(frame_scheduled_prs, text="No PRs scheduled", style='Info.TLabel').pack(pady=10)
        return

    # Create headers
    header_frame = ttk.Frame(frame_scheduled_prs)
    header_frame.pack(fill="x", padx=5, pady=5)
    ttk.Label(header_frame, text="ID", width=5).pack(side=tk.LEFT, padx=5)
    ttk.Label(header_frame, text="Title", width=30).pack(side=tk.LEFT, padx=5)
    ttk.Label(header_frame, text="Scheduled Time", width=20).pack(side=tk.LEFT, padx=5)
    ttk.Label(header_frame, text="Actions", width=15).pack(side=tk.LEFT, padx=5)

    ttk.Separator(frame_scheduled_prs, orient='horizontal').pack(fill='x', padx=5)

    for pr_id, details in scheduled_prs.items():
        pr_frame = ttk.Frame(frame_scheduled_prs)
        pr_frame.pack(fill="x", padx=5, pady=2)

        ttk.Label(pr_frame, text=f"#{pr_id}", width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(pr_frame, text=details['title'][:40], width=30).pack(side=tk.LEFT, padx=5)
        ttk.Label(pr_frame, text=details['time'].strftime('%Y-%m-%d %H:%M'), width=20).pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(pr_frame)
        btn_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Edit", style='Small.TButton', 
                 command=lambda pr_id=pr_id: edit_pr(pr_id)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Cancel", style='Small.Danger.TButton',
                 command=lambda pr_id=pr_id: cancel_pr(pr_id)).pack(side=tk.LEFT, padx=2)

# Configure styles
style = ttk.Style()
style.configure('Small.TButton', padding=2)
style.configure('Small.Danger.TButton', padding=2)
style.configure('Info.TLabel', foreground='gray')

# Initialize the display
update_scheduled_prs()

# Run the GUI main loop
root.mainloop()
