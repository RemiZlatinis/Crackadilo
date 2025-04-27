"""
Crackadilo - Simplified wrapper for cracking WPA/WPA2 PMKID hashes using hashcat.


OS: Linux Only
Python version: 3.8+
Author: Remi Zlatinis

usage:
    python crackadilo.py <dirpath_to_cap_and_22000_files> <dirpath_to_wordlists> <dirpath_to_rules>

"""

import subprocess
import threading
import time
import sys
from pathlib import Path
from typing import Optional

WORDLISTS_DIR = Path("/mnt/d/Downloads/wordlists/")
RULES_DIR = Path("/usr/share/hashcat/rules/")

WORDLISTS = [
    {
        "title": "Test (rockyou-65)",
        "path": "rockyou-65.txt.gz",
        "rule": False,
    },
    {
        "title": "Ultra fast (rockyou-65 with rules)",
        "path": "rockyou-65.txt.gz",
        "rule": "best64.rule",
    },
    {"title": "Fast (hk_hlm_founds)", "path": "hk_hlm_founds.txt.gz", "rule": False},
    {"title": "Medium (hashkiller24)", "path": "hashkiller24.txt.gz", "rule": False},
    {"title": "Slow (weakpass_4)", "path": "weakpass_4.txt.gz", "rule": False},
    {
        "title": "Slower (hk_hlm_founds with rules)",
        "path": "hk_hlm_founds.txt.gz",
        "rule": "best64.rule",
    },
    {
        "title": "Slowest (hashkiller24 with rules)",
        "path": "hashkiller24.txt.gz",
        "rule": "best64.rule",
    },
]

BENCHMARK_RESULT_FILE = Path("benchmark_result.txt")


def loading_spinner(stop_event: threading.Event, message: str = "Processing..."):
    """Displays a spinning loading indicator."""
    spinner_chars = ["|", "/", "-", "\\"]
    while not stop_event.is_set():
        for char in spinner_chars:
            if stop_event.is_set():
                break
            sys.stdout.write(f"\r{message} {char}")
            sys.stdout.flush()
            time.sleep(0.1)
    sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")  # Clear the spinner line
    sys.stdout.flush()


def run_hashcat_benchmark() -> None:
    """Runs the hashcat benchmark command and displays a simplified output.

    If the benchmark cache file already exists, it will be used instead of running the benchmark again.

    Returns:
        None
    """
    command = ["hashcat", "-b", "-m", "22000"]
    process: Optional[subprocess.Popen] = None
    stop_spinner = threading.Event()
    spinner_thread: Optional[threading.Thread] = None
    output_lines: list[str] = []

    if BENCHMARK_RESULT_FILE.exists():
        with open(BENCHMARK_RESULT_FILE, "r") as f:
            first_line = f.readline()
            if first_line:
                print(first_line.strip())
                return None
    try:
        # Start the loading spinner in a separate thread
        spinner_thread = threading.Thread(target=loading_spinner, args=(stop_spinner,))
        spinner_thread.start()

        # Start the hashcat process
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # Decode stdout and stderr as text
        )

        # Wait for the process to complete and capture all output
        stdout, stderr = process.communicate()
        output_lines = stdout.strip().splitlines()  # Capture final stdout lines

        # Stop the spinner
        stop_spinner.set()
        if spinner_thread and spinner_thread.is_alive():
            spinner_thread.join()

        # Check for errors
        if process.returncode != 0:
            print(
                f"Error executing hashcat. Return code: {process.returncode}",
                file=sys.stderr,
            )
            if stderr:
                print(f"Stderr:\n{stderr}", file=sys.stderr)
            return None

        # Creating and print the display message with the device name and performance
        result = "Unknown hashes per second"
        device = "Unknown Device"

        for line in output_lines:
            if "Device" in line:
                device = line.split(":")[1].strip()
                device = device.split(", ")[0]
                continue

            if "Speed" in line:
                result = line.split(":")[1].strip()
                result = result.split("@")[0].strip()
                continue
        display_message = f"⏲️  Your {device} can perform: {result}"
        print(display_message)

        # Cache the benchmark result to a file
        with open(BENCHMARK_RESULT_FILE, "w") as f:
            f.write(display_message)

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return None
    finally:
        # Ensure spinner is stopped even if errors occur
        stop_spinner.set()
        if spinner_thread and spinner_thread.is_alive():
            spinner_thread.join()
        # Ensure process is terminated if it's still running
        if process and process.poll() is None:
            process.terminate()
            process.wait()


if __name__ == "__main__":
    # The directory containing the .cap and the .22000 files
    cap_files_path = Path("./hs/")

    # --- Validation ---
    # Check if the hashcat is installed on the system
    command = "hashcat --version"
    try:
        subprocess.check_output(command, shell=True)
        print("✅ Hashcat is installed.")
    except subprocess.CalledProcessError:
        print("❌ Hashcat is not installed. Please install it first.")
        exit(1)

    # Check if the hashcat tools are installed on the system
    command = "hcxdumptool --version"
    try:
        subprocess.check_output(command, shell=True)
        print("✅ The hcxdumptool is installed.")
    except subprocess.CalledProcessError:
        print("❌ The hcxdumptool is not installed. Please install it first.")
        exit(1)

    # Check if the cap files directory exists
    if cap_files_path.exists():
        # Check if there is at least one .cap or .22000 file in the directory
        cap_files = list(cap_files_path.glob("*.cap")) + list(
            cap_files_path.glob("*.22000")
        )
        if cap_files:
            print("✅ Capture files found.")
        else:
            print("⏭️ No .cap or .22000 files found in the directory.")
            exit(0)
    else:
        print("❌ Cap files directory not found. Please check the path.")
        exit(1)

    # Check if the wordlists directory exists
    if WORDLISTS_DIR.exists():
        # Check if the listed wordlists exist in the directory
        for wordlist in WORDLISTS:
            wordlist_path = WORDLISTS_DIR / wordlist["path"]
            if not wordlist_path.exists():
                print(f"❌ {wordlist['title']} not found. Please check the path.")
                exit(1)
        else:
            print("✅ All wordlists found.")
    else:
        print("❌ Wordlists directory not found. Please check the path.")
        exit(1)

    # Check if the rules directory exists
    if RULES_DIR.exists():
        # Check if the listed rules exist in the directory
        for wordlist in WORDLISTS:
            if wordlist["rule"]:
                rule_path = RULES_DIR / wordlist["rule"]
                if not rule_path.exists():
                    print(f"❌ {wordlist['rule']} not found. Please check the path.")
                    exit(1)
        else:
            print("✅ All rules found.")
    else:
        print("❌ Rules directory not found. Please check the path.")
        exit(1)

    print()
    # --- Validation END ---

    # ---

    # --- Benchmarking ---
    run_hashcat_benchmark()
    print()
    # --- Benchmarking END ---

    # --- Combining capture files ---
    # Convert .cap files to .22000 files
    for cap_file in cap_files_path.glob("*.cap"):
        # Check if the .cap file is already converted to .22000 else convert it
        if not (cap_file.with_suffix(".22000")).exists():
            print(f"🔄 Converting {cap_file} to .22000...")
            command = f"hcxpcapngtool -o {cap_file.with_suffix('.22000')} {cap_file}"
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            process.wait()  # Wait for the process to complete
            if process.returncode == 0:
                print(f"✅ Converted {cap_file} to .22000.")
            else:
                print(f"❌ Failed to convert {cap_file}.")
        else:
            print(f"⏭️  {cap_file.with_suffix('.22000')} already exists.")

    # Combine all .22000 files into one file
    pmkid_files = list(cap_files_path.glob("*.22000"))
    hashes = []
    combined_file = Path("combined.22000")
    for file in pmkid_files:
        with open(file, "r") as f:
            line = f.readline()
            hashes.append(line.strip())

    if len(hashes) == 0:
        print("⏭️ No hashes found in the .22000 files.")
        exit(0)
    else:
        with open(combined_file, "w") as f:
            for hash in hashes:
                f.write(hash + "\n")
            print(f'✅ All capture files combined into "./{combined_file}" file.')
    print()
    # --- Combining capture files END ---

    # --- Cracking Commands ---
    # Create the base command for hashcat
    base_command = [
        "-a 0",  # Attack mode 0 (straight aka dictionary attack)
        "-m 22000",  # Hash type for WPA/WPA2 PMKID
        "-w 3",  # Workload profile (3 = high performance)
        "--status",  # Show status of the cracking process
        "--status-timer=10",  # Show status every 10 seconds
    ]

    # Generate a session command for each (level) wordlist
    for wordlist in WORDLISTS:
        session = wordlist["title"].split("(")[0].strip().replace(" ", "_").lower()
        print(
            f"💻🔑🔓 Staring new cracking session: {wordlist["title"]} (session: {session})\n"
        )

        command = [
            "hashcat",
            *base_command,
            "--session",
            session,
            combined_file.absolute().__str__(),
            f"{WORDLISTS_DIR / wordlist['path']}",
            "" if wordlist["rule"] is False else f"-r {RULES_DIR / wordlist['rule']}",
        ]
        command = " ".join(command).replace("'", "").replace('"', "")
        # print(f"Command: {command}")
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        for line in process.stdout:
            print(line, end="")

        process.wait()
        print(f"\n🔚 Cracking session {session} completed.\n")
    # --- Cracking ---

    exit(0)
