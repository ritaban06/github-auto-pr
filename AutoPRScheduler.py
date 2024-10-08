import os
import subprocess
import schedule
import time
import sys
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from tkcalendar import Calendar, DateEntry
from datetime import datetime

# Dictionary to hold scheduled PRs
scheduled_prs = {}
next_pr_id = 1  # Counter for unique PR IDs

# Function to create a PR using GitHub CLI
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
    git_repo_path = entry_repo_path.get()   # Local Git repository path
    repo = entry_repo.get()                 # Origin repository (org/repo)
    head = f"{entry_fork_user.get()}:{entry_fork_branch.get()}"  # Forked branch (username:branch)
    base = entry_base.get()                 # Base branch (origin branch)
    title = entry_title.get()               # PR title
    body = entry_body.get()                 # PR body

    create_pr(git_repo_path, repo, head, base, title, body)

# Handle "Schedule" button click
def schedule_task_gui():
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

# Local Git Repo Path
tk.Label(root, text="Local Git Repo Path:").grid(row=0, column=0)
entry_repo_path = tk.StringVar()
repo_path_entry = ttk.Combobox(root, textvariable=entry_repo_path, width=40)
repo_path_entry.grid(row=0, column=1)
tk.Button(root, text="Browse", command=browse_repo).grid(row=0, column=2)

# Origin Repo (org/repo)
tk.Label(root, text="Origin Repository (org/repo):").grid(row=1, column=0)
entry_repo = tk.StringVar()
repo_entry = ttk.Combobox(root, textvariable=entry_repo, width=40)
repo_entry.grid(row=1, column=1)

# Forked Account Username
tk.Label(root, text="Forked Account Username:").grid(row=2, column=0)
entry_fork_user = tk.StringVar()
fork_user_entry = ttk.Combobox(root, textvariable=entry_fork_user, width=40)
fork_user_entry.grid(row=2, column=1)

# Forked Branch
tk.Label(root, text="Forked Branch:").grid(row=3, column=0)
entry_fork_branch = tk.StringVar()
fork_branch_entry = ttk.Combobox(root, textvariable=entry_fork_branch, width=40)
fork_branch_entry.grid(row=3, column=1)

# Origin Branch (base branch)
tk.Label(root, text="Origin Base Branch:").grid(row=4, column=0)
entry_base = tk.StringVar()
base_entry = ttk.Combobox(root, textvariable=entry_base, width=40)
base_entry.grid(row=4, column=1)

# PR Title
tk.Label(root, text="PR Title:").grid(row=5, column=0)
entry_title = tk.StringVar()
title_entry = ttk.Combobox(root, textvariable=entry_title, width=40)
title_entry.grid(row=5, column=1)

# PR Body
tk.Label(root, text="PR Body:").grid(row=6, column=0)
entry_body = tk.StringVar()
body_entry = ttk.Combobox(root, textvariable=entry_body, width=40)
body_entry.grid(row=6, column=1)

# Date selector (calendar widget) and time selector (Spinbox)
tk.Label(root, text="Schedule Date:").grid(row=7, column=0)
cal = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern="yyyy-mm-dd")
cal.grid(row=7, column=1)

# Time selector (Spinbox for hours and minutes)
tk.Label(root, text="Schedule Time:").grid(row=8, column=0)
frame_time = tk.Frame(root)
frame_time.grid(row=8, column=1)
hour_spinbox = tk.Spinbox(frame_time, from_=0, to=23, width=2, format="%02.0f")  # Hours
hour_spinbox.pack(side=tk.LEFT)
tk.Label(frame_time, text=":").pack(side=tk.LEFT)
minute_spinbox = tk.Spinbox(frame_time, from_=0, to=59, width=2, format="%02.0f")  # Minutes
minute_spinbox.pack(side=tk.LEFT)

# Buttons to run the PR creation immediately or schedule it
btn_run_now = tk.Button(root, text="Run Now", command=run_now)
btn_run_now.grid(row=9, column=0, pady=10)

btn_schedule = tk.Button(root, text="Schedule", command=schedule_task_gui)
btn_schedule.grid(row=9, column=1, pady=10)

# Frame for showing scheduled PRs
frame_scheduled_prs = tk.Frame(root)
frame_scheduled_prs.grid(row=10, column=0, columnspan=3)
update_scheduled_prs()  # Initialize

# Run the GUI main loop
root.mainloop()
