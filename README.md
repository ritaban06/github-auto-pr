# AutoPRScheduler

## Overview

**AutoPRScheduler** is a Python script that automates the creation and scheduling of GitHub Pull Requests (PRs) using the GitHub CLI. It comes with a graphical user interface (GUI) built with Tkinter, allowing users to easily schedule PRs to be submitted at a later time. This tool is useful for developers and teams looking to automate their workflow with scheduled pull requests.

## Features

- **Automated PR Creation**: Leverages the GitHub CLI to create pull requests programmatically.
- **Scheduling**: Schedule PRs to be created at a future time.
- **GUI Interface**: Easy-to-use GUI to select Git repositories, PR details, and schedule the PR.
- **Error Handling**: Checks for valid Git repository paths and other potential issues.

## Requirements

- Python 3.x
- GitHub CLI (`gh`) installed and authenticated
- Tkinter for the GUI
- `tkcalendar` for scheduling functionality

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/ritaban06/github-auto-pr
   ```

2. Navigate to the project directory:

   ```bash
   cd AutoPRScheduler
   ```

3. Make sure you have the GitHub CLI installed and authenticated:

   ```bash
   gh auth login
   ```

## Usage

1. Run the script:

   ```bash
   python AutoPRScheduler.py
   ```

2. Use the GUI to:
   - Select the Git repository path.
   - Set the base and head branches for the PR.
   - Provide a title and description for the PR.
   - Schedule the PR to be created at a specified date and time.

## GUI Preview  
![AutoPRScheduler](<Screenshot 2025-06-23 164559.png>)  

## Example

1. Start the application.
2. Browse to your local Git repository.
3. Enter the PR details like title, description, base, and head branch.
4. Choose a date and time to schedule the PR.
5. The script will automatically create the PR using the GitHub CLI at the scheduled time.

   

## Dependencies

- **tkinter**: For the GUI.
- **tkcalendar**: For date and time picking in the schedule.
- **schedule**: For scheduling the PRs.

You can install the dependencies using `pip`:

```bash
pip install -r requirements.txt
```

## How to compile the exe

```bash
pyinstaller --onefile --noconsole --icon=favicon.ico AutoPRScheduler.py
```
| Option            | Description                                       |
| ----------------- | ------------------------------------------------- |
| `--onefile`       | Creates a single `.exe` instead of multiple files |
| `--noconsole`     | Hides terminal window (good for GUI apps)         |
| `--icon=icon.ico` | Adds a custom icon to your `.exe`                 |

## License

This project is licensed under the [MIT License](LICENSE.txt).

## Acknowledgments

- GitHub CLI (`gh`) for enabling the automation of pull requests.
