#!/usr/bin/env python3

import os
import sys
import subprocess
import tempfile
import shutil
import json
import urllib.request
import signal
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

# Set DEFAULT_SOCK to /tmp/jam_target.sock if not already set
TARGET_SOCK = os.environ.get("DEFAULT_SOCK", "/tmp/jam_target.sock")

# Used to run binaries when target is not provided as a docker image
DEFAULT_DOCKER_IMAGE = "debian:stable-slim"

# Maximum number of cores to use for docker containers
DOCKER_CPU_SET = os.environ.get("DOCKER_CPU_SET", "16-32")

# Whether to run targets in docker containers (1) or directly on host (0)
RUN_DOCKER = int(os.environ.get("RUN_DOCKER", "1"))

# Forces a platform for docker commands (run, pull, etc)
DOCKER_PLATFORM = "linux/amd64"

# Set directory variables
CURRENT_DIR = os.getcwd()
TARGETS_DIR = os.environ.get("TARGETS_DIR", f"{CURRENT_DIR}/targets")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGETS_FILE = os.environ.get("TARGETS_FILE", f"{SCRIPT_DIR}/targets.json")

@dataclass
class Target:
    name: str
    repo: Optional[str] = None
    clone: Optional[int] = None
    image: Optional[str] = None
    file: Optional[Union[str, Dict[str, str]]] = None
    cmd: Optional[Union[str, Dict[str, str]]] = None
    args: Optional[str] = None
    env: Optional[str] = None
    post: Optional[str] = None

    def get_file(self, os_name: str) -> Optional[str]:
        """Get the file for the given OS."""
        if not self.file:
            return None
        if isinstance(self.file, str):
            return self.file
        return self.file.get(os_name)

    def get_cmd(self, os_name: str) -> Optional[str]:
        """Get the command for the given OS."""
        if not self.cmd:
            return None
        if isinstance(self.cmd, str):
            return self.cmd
        return self.cmd.get(os_name)

    def get_args(self) -> Optional[str]:
        """Get the arguments."""
        return self.args

    def supports_os(self, os_name: str) -> bool:
        """Check if target supports the given OS."""
        if not self.file:
            return True
        if isinstance(self.file, str):
            return True
        return os_name in self.file

    def is_docker_target(self) -> bool:
        """Check if this is a Docker target."""
        return self.image is not None

    def is_repo_target(self) -> bool:
        """Check if this is a repository target."""
        return self.repo is not None


def load_targets() -> Dict[str, Target]:
    """Load target configuration from JSON file and convert to Target instances."""
    try:
        with open(TARGETS_FILE, "r") as f:
            targets_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: targets.json not found at {TARGETS_FILE}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in targets.json: {e}")
        sys.exit(1)

    targets = {}

    for target_name, target_config in targets_data.items():
        # Process string values to replace {TARGET_SOCK} placeholder
        processed_config = {}
        for key, value in target_config.items():
            if isinstance(value, str) and "{TARGET_SOCK}" in value:
                processed_config[key] = value.format(TARGET_SOCK=TARGET_SOCK)
            elif isinstance(value, dict):
                # Handle nested dictionaries (file.linux, cmd.macos, etc.)
                processed_dict = {}
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str) and "{TARGET_SOCK}" in sub_value:
                        processed_dict[sub_key] = sub_value.format(
                            TARGET_SOCK=TARGET_SOCK
                        )
                    elif isinstance(sub_value, list):
                        # Handle lists in nested dictionaries
                        processed_list = []
                        for item in sub_value:
                            if isinstance(item, str) and "{TARGET_SOCK}" in item:
                                processed_list.append(
                                    item.format(TARGET_SOCK=TARGET_SOCK)
                                )
                            else:
                                processed_list.append(item)
                        processed_dict[sub_key] = processed_list
                    else:
                        processed_dict[sub_key] = sub_value
                processed_config[key] = processed_dict
            elif isinstance(value, list):
                # Handle lists (args, cmd as list)
                processed_list = []
                for item in value:
                    if isinstance(item, str) and "{TARGET_SOCK}" in item:
                        processed_list.append(item.format(TARGET_SOCK=TARGET_SOCK))
                    else:
                        processed_list.append(item)
                processed_config[key] = processed_list
            elif isinstance(value, str) and "{TARGET_SOCK}" in value:
                processed_config[key] = value.format(TARGET_SOCK=TARGET_SOCK)
            else:
                processed_config[key] = value

        targets[target_name] = Target(name=target_name, **processed_config)

    return targets


# Load target configuration from JSON file
TARGETS = load_targets()


def get_target(target: str) -> Optional[Target]:
    if target in TARGETS:
        return TARGETS[target]
    else:
        print(f"Error: Target {target} not found")
        return None


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    available_targets = get_available_targets()

    parser = argparse.ArgumentParser(
        description="JAM conformance target manager - download and run JAM implementation targets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s get all                    # Download all targets
  %(prog)s get jamzig                 # Download jamzig target
  %(prog)s run boka                   # Run boka target
  %(prog)s --os macos get jamzig      # Download jamzig for macOS
  %(prog)s run --no-docker spacejam   # Run spacejam directly on host
  %(prog)s info all                   # Show info for all targets

Environment variables:
  DEFAULT_SOCK    Socket path (default: /tmp/jam_target.sock)
  RUN_DOCKER      Run in Docker (1) or host (0) (default: 1)
  DOCKER_CORES    Max cores for Docker (default: 32)

Use 'info all' to see available targets.
        """,
    )

    parser.add_argument(
        "--os", choices=["linux", "macos"], help="Target OS (default: auto-detected)"
    )

    subparsers = parser.add_subparsers(
        dest="action", help="Action to perform", required=True
    )

    # Get subcommand
    get_parser = subparsers.add_parser("get", help="Download target(s)")
    get_parser.add_argument(
        "target",
        choices=available_targets + ["all"],
        metavar="TARGET",
        help='Target to download (or "all" for all targets)',
    )

    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Run target")
    run_parser.add_argument(
        "target", choices=available_targets, metavar="TARGET", help="Target to run"
    )

    docker_group = run_parser.add_mutually_exclusive_group()
    docker_group.add_argument(
        "--docker",
        action="store_true",
        help="Force Docker usage (overrides RUN_DOCKER env var)",
    )
    docker_group.add_argument(
        "--no-docker",
        action="store_true",
        help="Force host usage (overrides RUN_DOCKER env var)",
    )

    # Info subcommand
    info_parser = subparsers.add_parser("info", help="Show target information")
    info_parser.add_argument(
        "target",
        choices=available_targets + ["all"],
        metavar="TARGET",
        help='Target to show info for (or "all" for all targets)',
    )

    # Clean subcommand
    clean_parser = subparsers.add_parser("clean", help="Clean target files")
    clean_parser.add_argument(
        "target",
        choices=available_targets + ["all"],
        metavar="TARGET",
        help='Target to clean (or "all" for all targets)',
    )

    # List subcommand
    subparsers.add_parser("list", help="List all available targets")

    return parser


def get_os() -> Optional[str]:
    import platform

    system = platform.system()
    if system == "Linux":
        return "linux"
    elif system == "Darwin":
        return "macos"
    else:
        return None


def is_docker_target(target: str) -> bool:
    return target in TARGETS and TARGETS[target].is_docker_target()


def is_repo_target(target: str) -> bool:
    return target in TARGETS and TARGETS[target].is_repo_target()


def get_available_targets() -> List[str]:
    return sorted(list(TARGETS.keys()))


def target_supports_os(name: str, os_name: str) -> bool:
    target = get_target(name)
    if target is None:
        return False
    if not target.supports_os(os_name):
        print(f"Error: No {os_name} version available for {name}", file=sys.stderr)
        return False
    return True


def get_target_file(name: str, os_name: str) -> Optional[str]:
    target = get_target(name)
    if target is None:
        return None
    return target.get_file(os_name)


def post_actions(target_name: str, os_name: str) -> bool:
    target = get_target(target_name)
    if not target:
        return False
    file = target.get_file(os_name)
    if not file:
        return False

    print(f"Performing post actions for {file}")
    target_dir = Path(f"{TARGETS_DIR}/{target_name}/latest")
    os.chdir(target_dir)

    if target.post:
        subprocess.run(target.post, shell=True, check=True)
    else:
        # Extract nested archives by peeling off extensions
        current_file = Path(file)
        while current_file.exists():
            if current_file.suffix == ".zip":
                print(f"Extracting zip archive: {current_file}")
                subprocess.run(["unzip", str(current_file)], check=True)
                current_file.unlink()
                current_file = current_file.with_suffix("")
            elif current_file.suffixes[-2:] == [".tar", ".gz"]:
                print(f"Extracting tar.gz archive: {current_file}")
                subprocess.run(["tar", "-xzf", str(current_file)], check=True)
                current_file.unlink()
                current_file = current_file.with_suffix("").with_suffix("")
            elif current_file.suffix == ".tgz":
                print(f"Extracting tgz archive: {current_file}")
                subprocess.run(["tar", "-xzf", str(current_file)], check=True)
                current_file.unlink()
                current_file = current_file.with_suffix("")
            elif current_file.suffixes[-2:] == [".tar", ".bz2"]:
                print(f"Extracting tar.bz2 archive: {current_file}")
                subprocess.run(["tar", "-xjf", str(current_file)], check=True)
                current_file.unlink()
                current_file = current_file.with_suffix("").with_suffix("")
            elif current_file.suffix == ".tbz2":
                print(f"Extracting tbz2 archive: {current_file}")
                subprocess.run(["tar", "-xjf", str(current_file)], check=True)
                current_file.unlink()
                current_file = current_file.with_suffix("")
            elif current_file.suffixes[-2:] == [".tar", ".xz"]:
                print(f"Extracting tar.xz archive: {current_file}")
                subprocess.run(["tar", "-xJf", str(current_file)], check=True)
                current_file.unlink()
                current_file = current_file.with_suffix("").with_suffix("")
            elif current_file.suffix == ".txz":
                print(f"Extracting txz archive: {current_file}")
                subprocess.run(["tar", "-xJf", str(current_file)], check=True)
                current_file.unlink()
                current_file = current_file.with_suffix("")
            elif current_file.suffix == ".tar":
                print(f"Extracting tar archive: {current_file}")
                subprocess.run(["tar", "-xf", str(current_file)], check=True)
                current_file.unlink()
                current_file = current_file.with_suffix("")
            else:
                # Not an archive, make it executable and stop
                print(f"Making file executable: {current_file}")
                current_file.chmod(0o755)
                break

    os.chdir(CURRENT_DIR)
    return True


def clone_github_repo(target: str, os_name: str, repo: str) -> bool:
    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(
            ["git", "clone", f"https://github.com/{repo}", "--depth", "1", temp_dir],
            check=True,
        )

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = result.stdout.strip()
        print(f"Cloning last revision: {commit_hash}")

        target_dir = Path(f"{TARGETS_DIR}/{target}")
        print(f"Cloned to {target_dir}")

        target_dir.mkdir(parents=True, exist_ok=True)
        target_dir_rev = target_dir / commit_hash

        shutil.move(temp_dir, target_dir_rev)

        latest_link = target_dir / "latest"
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(target_dir_rev.resolve())

        post_actions(target, os_name)

    return True


def get_docker_image(target: str) -> bool:
    if target not in TARGETS:
        print(f"Error: Target {target} not found")
        return False

    target_obj = TARGETS[target]
    docker_image = target_obj.image

    if not docker_image:
        print(f"Error: No Docker image specified for {target}")
        return False

    print(f"Pulling Docker image: {docker_image}")

    if not shutil.which("docker"):
        print("Error: Docker is not installed or not in PATH")
        return False

    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("Error: Docker daemon is not running or not accessible")
        print("Please start Docker and try again")
        return False

    try:
        subprocess.run(["docker", "pull", "--platform", DOCKER_PLATFORM, docker_image], check=True)
        print(f"Successfully pulled Docker image: {docker_image}")
        return True
    except subprocess.CalledProcessError:
        print(f"Error: Failed to pull Docker image {docker_image}")
        return False


def get_github_release(target: str, os_name: str) -> bool:
    if target not in TARGETS:
        print(f"Error: Target {target} not found")
        return False

    target_obj = TARGETS[target]
    repo = target_obj.repo
    file = get_target_file(target, os_name)

    if not repo:
        print(f"Error: missing repository information for {target}")
        return False

    if target_obj.clone == 1:
        print(
            f"Info: No release file specified for {target} on {os_name}, cloning repository instead"
        )
        return clone_github_repo(target, os_name, repo)

    # Get the latest release tag from GitHub API
    print("Fetching latest release information...")
    try:
        with urllib.request.urlopen(
            f"https://api.github.com/repos/{repo}/releases/latest"
        ) as response:
            data = json.loads(response.read().decode())
            latest_tag = data["tag_name"]
    except Exception as e:
        print(f"Error: Could not fetch latest release tag: {e}")
        return False

    print(f"Latest version: {latest_tag}")

    # Construct download URL
    download_url = f"https://github.com/{repo}/releases/download/{latest_tag}/{file}"
    print(f"Downloading from: {download_url}")

    # Download the file
    try:
        urllib.request.urlretrieve(download_url, file)
    except Exception as e:
        print(f"Error: Download failed: {e}")
        return False

    print(f"Downloading target to file: {file}")
    target_dir = Path(f"{TARGETS_DIR}/{target}")
    target_dir_rev = target_dir / latest_tag

    target_dir_rev.mkdir(parents=True, exist_ok=True)
    shutil.move(file, target_dir_rev / file)
    print(f"* Target downloaded to: {target_dir_rev}")


    latest_link = target_dir / "latest"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(target_dir_rev.resolve())

    return post_actions(target, os_name)


def print_docker_image_info(image):
    result = subprocess.run(
        ["docker", "inspect", image, "--format", "{{.Id}}\n{{.Created}}"],
        capture_output=True,
        text=True,
        check=True
    )
    lines = result.stdout.strip().split('\n')
    image_id = lines[0]
    created = lines[1] if len(lines) > 1 else "Unknown"
    # Strip "sha256:" prefix if present
    if image_id.startswith("sha256:"):
        image_id = image_id[7:]
    image_id = image_id[:12]  # Short ID
    print(f"Image: {image}")
    print(f"Image ID: {image_id}")
    print(f"Created: {created}")


def run_docker_image(target: str) -> None:
    if target not in TARGETS:
        print(f"Error: Target {target} not found")
        return

    target_obj = TARGETS[target]
    image = target_obj.image
    cmd = target_obj.cmd
    env = target_obj.env

    print(f"Running {target} on docker image")
    print(f"Command: {cmd}")

    try:
        print_docker_image_info(image)
    except (subprocess.CalledProcessError, IndexError, ValueError):
        print(f"Error: Docker image '{image}' not found locally.")
        print(f"Please run: {sys.argv[0]} get {target}")
        sys.exit(1)

    def cleanup_docker():
        print(f"Cleaning up Docker container {target}...")
        subprocess.run(["docker", "kill", target], capture_output=True)
        try:
            os.unlink(TARGET_SOCK)
        except FileNotFoundError:
            pass

    def signal_handler(signum, frame):
        cleanup_docker()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        target,
        "--init",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--platform",
        DOCKER_PLATFORM,
        "--cpuset-cpus",
        f"{DOCKER_CPU_SET}",
        "--cpu-shares",
        "2048",
        "--cpu-quota",
        "-1",
        "--memory",
        "8g",
        "--memory-swap",
        "8g",
        "--shm-size",
        "1g",
        "--ulimit",
        "nofile=65536:65536",
        "--ulimit",
        "nproc=32768:32768",
        "--sysctl",
        "net.core.somaxconn=65535",
        "--sysctl",
        "net.ipv4.tcp_tw_reuse=1",
        "--security-opt",
        "seccomp=unconfined",
        "--security-opt",
        "apparmor=unconfined",
        "--cap-add",
        "SYS_NICE",
        "--cap-add",
        "SYS_RESOURCE",
        "--cap-add",
        "IPC_LOCK",
        "-v",
        "/tmp:/tmp",
    ]

    if env:
        docker_cmd.extend(["-e", env])

    if image == DEFAULT_DOCKER_IMAGE:
        docker_cmd.extend(["-w", "/jam"])
        docker_cmd.extend(["-e", "HOME=/jam"])
        docker_cmd.extend(["-v", f"{TARGETS_DIR}/{target}/latest:/jam"])

    docker_cmd.append(image)

    # Handle cmd as string
    if cmd:
        import shlex
        docker_cmd.extend(shlex.split(cmd))

    # Add priority args for Linux
    current_os = get_os()
    if current_os == "linux":
        priority_cmd = [
            "sudo",
            "chrt",
            "-f",
            "99",
            "nice",
            "-n",
            "-20",
            "ionice",
            "-c1",
            "-n0",
            "taskset",
            "-c",
            f"{DOCKER_CPU_SET}",
        ]
        docker_cmd = priority_cmd + docker_cmd

    try:
        process = subprocess.Popen(docker_cmd)
        print(f"Waiting for target termination (pid={process.pid})")
        exit_code = process.wait()
        print(f"Target process exited with status: {exit_code}")
    finally:
        cleanup_docker()


def print_target_info(target: Target, os_name: str) -> None:
    """Print detailed information about a target."""
    print(f"\n=== {target.name.upper()} ===")
    print(f"Name: {target.name}")

    # Show OS support
    supported_oses = []
    for os_check in ["linux", "macos"]:
        if target.supports_os(os_check):
            supported_oses.append(os_check)
    print(f"Supported OS: {', '.join(supported_oses)}")

    # Show target type
    target_type = []
    if target.is_docker_target():
        target_type.append("Docker")
    if target.is_repo_target():
        target_type.append("Repository")
    print(f"Type: {', '.join(target_type)}")

    # Check if target is downloaded/available
    target_dir = Path(f"{TARGETS_DIR}/{target.name}/latest")
    if target.is_repo_target():
        print(f"Repository: https://github.com/{target.repo}")
        if target_dir.exists():
            print(f"Downloaded: {target_dir}")
    elif target.is_docker_target():
        # Check if Docker image exists locally
        try:
            print_docker_image_info(target.image)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Status: Not downloaded (Docker image not found locally)")
    else:
        print("Status: Not downloaded")

    if target.clone:
        print(f"Clone Mode: {'Yes' if target.clone == 1 else 'No'}")

    if target.file:
        if isinstance(target.cmd, dict):
            print("Files:")
            for os_key, file_path in target.file.items():
                print(f"  {os_key}: {file_path}")
        else:
            print(f"File: {target.file}")

    if target.cmd:
        if isinstance(target.cmd, dict):
            print("Commands:")
            for os_key, cmd in target.cmd.items():
                print(f"  {os_key}: {cmd}")
        else:
            print(f"Command: {target.cmd}")

    if target.args:
        print(f"Arguments: {target.args}")

    if target.env:
        print(f"Environment: {target.env}")


def handle_info_action(target: str, os_name: str) -> bool:
    """Handle the info action for a target or all targets."""
    if target == "all":
        for target_name in get_available_targets():
            handle_info_action(target_name, os_name)
    else:
        target_obj = get_target(target)
        if target_obj is None:
            return False
        print_target_info(target_obj, os_name)
    return True


def handle_get_action(target: str, os_name: str) -> bool:
    """Handle the get action for a target or all targets."""
    print(f"Downloading {target} for {os_name}...")

    if target == "all":
        available_targets = get_available_targets()
        failed_targets = []
        for target in available_targets:
            print("----------------------------------")
            success = handle_get_action(target, os_name)
            if not success:
                failed_targets.append(target)
        if not failed_targets:
            print("All targets downloaded successfully!")
            return True
        else:
            print(
                f"Failed to download the following targets: {' '.join(failed_targets)}"
            )
            total_targets = len(available_targets)
            successful = total_targets - len(failed_targets)
            print(
                f"Successfully downloaded: {successful} out of {total_targets} targets"
            )
            return False
    elif is_repo_target(target):
        if target_supports_os(target, os_name):
            return get_github_release(target, os_name)
        else:
            return False
    elif is_docker_target(target):
        return get_docker_image(target)
    else:
        available_targets = get_available_targets()
        print(f"Unknown target '{target}'")
        print(f"Available targets: {' '.join(available_targets)} all")
        return False


def handle_list_action() -> bool:
    """Handle the list action to show all available targets."""
    available_targets = get_available_targets()
    for target in available_targets:
        print(target)
    return True


def handle_clean_action(target: str) -> bool:
    """Handle the clean action for a target or all targets."""
    if target == "all":
        targets_dir = Path(f"{TARGETS_DIR}")
        if targets_dir.exists():
            print("Cleaning all target files...")
            for item in targets_dir.iterdir():
                if item.is_dir():
                    print(f"Removing {item}")
                    shutil.rmtree(item)
            print("All target files cleaned successfully!")
        else:
            print("No target files to clean.")
        return True
    else:
        target_dir = Path(f"{TARGETS_DIR}/{target}")
        if target_dir.exists():
            print(f"Cleaning target {target}...")
            shutil.rmtree(target_dir)
            print(f"Target {target} cleaned successfully!")
        else:
            print(f"Target {target} not found or already clean.")
        return True


def handle_run_action(target: str, os_name: str) -> bool:
    """Handle the run action for a target."""
    if is_docker_target(target):
        run_docker_image(target)
        return True
    elif is_repo_target(target):
        run_target(target, os_name)
        return True
    else:
        available_targets = get_available_targets()
        print(f"Unknown target '{target}'")
        print(f"Available targets: {' '.join(available_targets)}")
        return False


def run_target(target: str, os_name: str) -> None:
    if target not in TARGETS:
        print(f"Error: Target {target} not found")
        return

    target_obj = TARGETS[target]
    command = target_obj.get_cmd(os_name)

    if not command:
        print(f"Error: No run command specified for {target} on {os_name}")
        return

    target_dir = Path(f"{TARGETS_DIR}/{target}/latest")
    if not target_dir.exists():
        print(f"Error: Target dir not found: {target_dir}")
        # Try to find the newest directory as fallback
        base_dir = Path(f"targets/{target}")
        if base_dir.exists():
            try:
                newest_dir = max(base_dir.iterdir(), key=lambda p: p.stat().st_mtime)
                if newest_dir.is_dir():
                    print(f"Using newest available directory: {newest_dir}")
                    target_dir = newest_dir
                else:
                    raise ValueError("No directories found")
            except (ValueError, OSError):
                print(f"Get the target first with: get {target}")
                sys.exit(1)
        else:
            print(f"Get the target first with: get {target}")
            sys.exit(1)

    full_command = f"./{command}"
    command_args = target_obj.get_args()
    if command_args is not None:
        full_command += f" {command_args}"

    if RUN_DOCKER == 1:
        # Overwrite target information and run it in a dedicated docker image
        target_obj = TARGETS[target]
        target_obj.image = DEFAULT_DOCKER_IMAGE
        target_obj.cmd = full_command
        run_docker_image(target)
    else:
        cleanup_done = False
        target_pid = None

        def cleanup():
            os.chdir(CURRENT_DIR)
            nonlocal cleanup_done, target_pid
            if cleanup_done:
                return
            cleanup_done = True

            print(f"Cleaning up {target}...")
            if target_pid:
                print(f"Killing target {target_pid}...")
                try:
                    os.kill(target_pid, signal.SIGTERM)
                    time.sleep(1)
                    os.kill(target_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            try:
                os.unlink(TARGET_SOCK)
            except FileNotFoundError:
                pass

        def signal_handler(signum, frame):
            cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        target_obj = TARGETS[target]
        env = target_obj.env
        if env:
            # Export environment variables
            for var in env.split():
                if "=" in var:
                    key, value = var.split("=", 1)
                    os.environ[key] = value

        try:
            os.chdir(target_dir)
            process = subprocess.Popen(full_command, shell=True)
            target_pid = process.pid
            print(f"Waiting for target termination (pid={target_pid})")
            process.wait()
        finally:
            cleanup()


def main():
    global RUN_DOCKER

    parser = create_parser()
    args = parser.parse_args()

    action = args.action
    target = getattr(args, 'target', None)

    # Handle Docker override from command line (only for run action)
    if action == "run":
        if hasattr(args, "docker") and args.docker:
            RUN_DOCKER = 1
        elif hasattr(args, "no_docker") and args.no_docker:
            RUN_DOCKER = 0

    # Determine OS
    if args.os:
        os_name = args.os
    elif RUN_DOCKER == 1:
        # use linux, since we are running in a fixed Debian Docker image
        os_name = "linux"
    else:
        os_name = get_os()
        if os_name is None:
            print("Unsupported OS", file=sys.stderr)
            sys.exit(1)

    print(f"Action: {action}, Target: {target}, OS: {os_name}")

    success = False
    if action == "info":
        success = handle_info_action(target, os_name)
    elif action == "get":
        success = handle_get_action(target, os_name)
    elif action == "run":
        success = handle_run_action(target, os_name)
    elif action == "clean":
        success = handle_clean_action(target)
    elif action == "list":
        success = handle_list_action()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
