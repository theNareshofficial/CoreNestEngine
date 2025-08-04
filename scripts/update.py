#!/usr/bin/env python3

import subprocess
import sys

def run_update():

    try:
        process = subprocess.run(
            ["git", "pull"],
            capture_output=True,
            text=True,
            check=True,  # This will raise an exception if git pull fails
            encoding='utf-8'
        )
        # If successful, return the standard output
        return (True, process.stdout)
    except FileNotFoundError:
        # This happens if 'git' is not installed or not in the PATH
        return (False, "Error: 'git' command not found. Is Git installed on the server?")
    except subprocess.CalledProcessError as e:
        # This happens if git pull returns a non-zero exit code (an error)
        error_message = f"Error during 'git pull':\n{e.stderr}"
        return (False, error_message)
    except Exception as e:
        # Catch any other unexpected errors
        return (False, f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    success, output = run_update()
    print(output)
    if not success:
        sys.exit(1)