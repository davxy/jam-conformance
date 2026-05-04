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
import random
import shlex
import string
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Union
from dataclasses import dataclass
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

@dataclass
class Config:
    """Constants and runtime configuration for the script.

    Instance fields are populated by `Config.from_args(args)` with precedence:
    CLI flag > env var > default. ClassVar fields are true constants.
    """

    # CLI/env-driven values
    host_data_path: str       # JAM_FUZZ_DATA_PATH
    docker_cpu_set: str       # JAM_FUZZ_DOCKER_CPU_SET
    run_docker: bool          # JAM_FUZZ_RUN_DOCKER, --no-docker
    targets_dir: str          # JAM_FUZZ_TARGETS_DIR
    targets_file: str         # JAM_FUZZ_TARGETS_FILE, --targets-file
    spec: str                 # JAM_FUZZ_SPEC, --spec
    log_level: str            # JAM_FUZZ_LOG_LEVEL

    # True constants
    DEFAULT_DOCKER_IMAGE: ClassVar[str] = "debian:stable-slim"
    DOCKER_PLATFORM: ClassVar[str] = "linux/amd64"
    # Standard JAM fuzz packaging paths inside the container (see fuzz-proto/README.md).
    CONTAINER_DATA_PATH: ClassVar[str] = "/tmp/jam_fuzz"
    CONTAINER_SOCK_PATH: ClassVar[str] = "/tmp/jam_fuzz/fuzz.sock"
    CURRENT_DIR: ClassVar[str] = os.getcwd()
    SCRIPT_DIR: ClassVar[str] = os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def _parse_bool(s: str) -> bool:
        return s.strip().lower() in ("1", "true", "yes", "y", "on")

    @classmethod
    def from_args(cls, args) -> "Config":
        cpu_default = f"0-{os.cpu_count() - 1}" if os.cpu_count() and os.cpu_count() > 1 else "0"

        run_docker = cls._parse_bool(os.environ.get("JAM_FUZZ_RUN_DOCKER", "1"))
        spec = os.environ.get("JAM_FUZZ_SPEC", "tiny")
        if args.action == "run":
            if args.no_docker:
                run_docker = False
            if args.spec:
                spec = args.spec

        return cls(
            host_data_path=os.environ.get("JAM_FUZZ_DATA_PATH", "/tmp/jam_fuzz"),
            docker_cpu_set=os.environ.get("JAM_FUZZ_DOCKER_CPU_SET", cpu_default),
            run_docker=run_docker,
            targets_dir=os.environ.get("JAM_FUZZ_TARGETS_DIR", f"{cls.CURRENT_DIR}/targets"),
            targets_file=args.targets_file or os.environ.get(
                "JAM_FUZZ_TARGETS_FILE", f"{cls.SCRIPT_DIR}/targets.json"
            ),
            spec=spec,
            log_level=os.environ.get("JAM_FUZZ_LOG_LEVEL", "info"),
        )


CONFIG: Optional[Config] = None

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
    gp_version: Optional[str] = None

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
        with open(CONFIG.targets_file, "r") as f:
            text = f.read().replace("{SOCK_PATH}", CONFIG.CONTAINER_SOCK_PATH)
    except FileNotFoundError:
        print(f"Error: targets.json not found at {CONFIG.targets_file}")
        sys.exit(1)

    try:
        targets_data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in targets.json: {e}")
        sys.exit(1)

    return {name: Target(name=name, **cfg) for name, cfg in targets_data.items()}


# Target configuration is loaded in main() after CLI args are parsed,
# so that --targets-file can override JAM_FUZZ_TARGETS_FILE.
TARGETS: Dict[str, Target] = {}


def get_target(target: str) -> Optional[Target]:
    return TARGETS.get(target)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
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

Environment variables (all overridable via CLI flags listed above):
  JAM_FUZZ_TARGETS_FILE    Path to targets JSON file (default: <script>/targets.json)
  JAM_FUZZ_TARGETS_DIR     Where downloaded targets are stored (default: ./targets)
  JAM_FUZZ_DATA_PATH       Host data directory (default: /tmp/jam_fuzz)
  JAM_FUZZ_RUN_DOCKER      Run in Docker (1/true/yes) or host (0/false/no) (default: 1)
  JAM_FUZZ_DOCKER_CPU_SET  CPU set for Docker containers (default: all cores)
  JAM_FUZZ_SPEC            Specification: tiny or full (default: tiny)
  JAM_FUZZ_LOG_LEVEL       Log level forwarded to the target (default: info)
  GITHUB_TOKEN             Optional bearer token for GitHub release lookups

Use 'info all' to see available targets.
        """,
    )

    parser.add_argument(
        "--os", choices=["linux", "macos"], help="Target OS (default: auto-detected)"
    )

    parser.add_argument(
        "--spec",
        choices=["tiny", "full"],
        default=None,
        help="Specification to use (tiny or full, overrides JAM_FUZZ_SPEC env var)"
    )

    parser.add_argument(
        "--targets-file",
        type=str,
        default=None,
        help="Path to targets JSON file (overrides JAM_FUZZ_TARGETS_FILE env var)",
    )

    subparsers = parser.add_subparsers(
        dest="action", help="Action to perform", required=True
    )

    # Get subcommand
    get_parser = subparsers.add_parser("get", help="Download target(s)")
    get_parser.add_argument(
        "target",
        metavar="TARGET",
        help='Target to download (or "all" for all targets)',
    )

    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Run target")
    run_parser.add_argument(
        "target", metavar="TARGET", help="Target to run"
    )

    run_parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Run on host instead of Docker (overrides JAM_FUZZ_RUN_DOCKER env var)",
    )
    run_parser.add_argument(
        "--target-args",
        type=str,
        default="",
        help="Extra target args to append to the ones found in target.json"
    )
    run_parser.add_argument(
        "--target-env",
        type=str,
        default="",
        help="Extra environment variables (space-separated KEY=VALUE pairs) to extend target env"
    )

    run_parser.add_argument(
        "--container-name",
        type=str,
        help="Specify custom Docker container name (default: auto-generated with random suffix)",
    )

    run_parser.add_argument(
        "--docker-elevate-priority",
        action="store_true",
        help="Elevate Docker container priority (Linux only, requires sudo)",
    )

    # Info subcommand
    info_parser = subparsers.add_parser("info", help="Show target information")
    info_parser.add_argument(
        "target",
        metavar="TARGET",
        help='Target to show info for (or "all" for all targets)',
    )

    # Clean subcommand
    clean_parser = subparsers.add_parser("clean", help="Clean target files")
    clean_parser.add_argument(
        "target",
        metavar="TARGET",
        help='Target to clean (or "all" for all targets)',
    )

    # List subcommand
    list_parser = subparsers.add_parser("list", help="List all available targets")
    list_parser.add_argument(
        "--gp-version",
        type=str,
        help="Filter targets by gp-version (e.g., 0.7.0, 0.7.1)",
    )

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


def get_available_targets() -> List[str]:
    return sorted(list(TARGETS.keys()))


def _clean_host_data() -> None:
    try:
        shutil.rmtree(CONFIG.host_data_path)
    except FileNotFoundError:
        pass


def post_actions(target_name: str, os_name: str) -> bool:
    target = get_target(target_name)
    if not target:
        return False
    file = target.get_file(os_name)
    if not file:
        return False

    print(f"Performing post actions for {file}")
    target_dir = Path(f"{CONFIG.targets_dir}/{target_name}/latest")

    if target.post:
        subprocess.run(target.post, shell=True, check=True, cwd=target_dir)
        return True

    # Extract nested archives by peeling off extensions
    current_file = target_dir / file
    while current_file.exists():
        if current_file.suffix == ".zip":
            print(f"Extracting zip archive: {current_file}")
            subprocess.run(["unzip", str(current_file)], check=True, cwd=target_dir)
            current_file.unlink()
            current_file = current_file.with_suffix("")
        elif current_file.suffixes[-2:] == [".tar", ".gz"]:
            print(f"Extracting tar.gz archive: {current_file}")
            subprocess.run(["tar", "-xzf", str(current_file)], check=True, cwd=target_dir)
            current_file.unlink()
            current_file = current_file.with_suffix("").with_suffix("")
        elif current_file.suffix == ".tgz":
            print(f"Extracting tgz archive: {current_file}")
            subprocess.run(["tar", "-xzf", str(current_file)], check=True, cwd=target_dir)
            current_file.unlink()
            current_file = current_file.with_suffix("")
        elif current_file.suffixes[-2:] == [".tar", ".bz2"]:
            print(f"Extracting tar.bz2 archive: {current_file}")
            subprocess.run(["tar", "-xjf", str(current_file)], check=True, cwd=target_dir)
            current_file.unlink()
            current_file = current_file.with_suffix("").with_suffix("")
        elif current_file.suffix == ".tbz2":
            print(f"Extracting tbz2 archive: {current_file}")
            subprocess.run(["tar", "-xjf", str(current_file)], check=True, cwd=target_dir)
            current_file.unlink()
            current_file = current_file.with_suffix("")
        elif current_file.suffixes[-2:] == [".tar", ".xz"]:
            print(f"Extracting tar.xz archive: {current_file}")
            subprocess.run(["tar", "-xJf", str(current_file)], check=True, cwd=target_dir)
            current_file.unlink()
            current_file = current_file.with_suffix("").with_suffix("")
        elif current_file.suffix == ".txz":
            print(f"Extracting txz archive: {current_file}")
            subprocess.run(["tar", "-xJf", str(current_file)], check=True, cwd=target_dir)
            current_file.unlink()
            current_file = current_file.with_suffix("")
        elif current_file.suffix == ".tar":
            print(f"Extracting tar archive: {current_file}")
            subprocess.run(["tar", "-xf", str(current_file)], check=True, cwd=target_dir)
            current_file.unlink()
            current_file = current_file.with_suffix("")
        else:
            # Not an archive, make it executable and stop
            print(f"Making file executable: {current_file}")
            current_file.chmod(0o755)
            break

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

        target_dir = Path(f"{CONFIG.targets_dir}/{target}")
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
        subprocess.run(["docker", "pull", "--platform", CONFIG.DOCKER_PLATFORM, docker_image], check=True)
        print(f"Successfully pulled Docker image: {docker_image}")
        return True
    except subprocess.CalledProcessError:
        print(f"Error: Failed to pull Docker image {docker_image}")
        return False


def get_github_release(target: str, os_name: str) -> bool:
    target_obj = TARGETS[target]
    repo = target_obj.repo
    file = target_obj.get_file(os_name)

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
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(url)
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            req.add_header("Authorization", f"token {github_token}")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            latest_tag = data["tag_name"]
    except Exception as e:
        print(f"Error: Could not fetch latest release tag: {e}")
        return False

    print(f"Latest version: {latest_tag}")

    # Construct download URL
    download_url = f"https://github.com/{repo}/releases/download/{latest_tag}/{file}"
    print(f"Downloading from: {download_url}")

    # Download to a temporary file to avoid race conditions when
    # multiple targets share the same filename (e.g., jamzilla and jamzilla-int)
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file}") as tmp:
            tmp_path = tmp.name
        urllib.request.urlretrieve(download_url, tmp_path)
    except Exception as e:
        print(f"Error: Download failed: {e}")
        return False

    print(f"Downloaded target to: {tmp_path}")
    target_dir = Path(f"{CONFIG.targets_dir}/{target}")
    target_dir_rev = target_dir / latest_tag

    target_dir_rev.mkdir(parents=True, exist_ok=True)
    shutil.move(tmp_path, target_dir_rev / file)
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


def is_rootless_docker() -> bool:
    """Detect if Docker is running in rootless mode."""
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.SecurityOptions}}"],
            capture_output=True, text=True, check=True,
        )
        return "rootless" in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_docker_image(target: str, args, image: Optional[str] = None, cmd: Optional[str] = None) -> None:
    target_obj = TARGETS[target]
    if image is None:
        image = target_obj.image
    if cmd is None:
        cmd = target_obj.cmd
    env = target_obj.env

    # Use custom container name if provided, otherwise generate unique name with random suffix
    if args.container_name:
        container_name = args.container_name
    else:
        # Generate unique container name with random suffix to allow parallel instances
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        container_name = f"{target}-{random_suffix}"

    print(f"Running '{target}' on docker image")
    print(f"Command: '{cmd}'")
    print(f"Container: '{container_name}'")

    try:
        print_docker_image_info(image)
    except (subprocess.CalledProcessError, IndexError, ValueError):
        print(f"Error: Docker image '{image}' not found locally.")
        print(f"Please run: {sys.argv[0]} get {target}")
        sys.exit(1)

    # Clean start: remove any leftover data directory from previous runs
    # This ensures the socket and other runtime files are fresh
    _clean_host_data()

    # Create host data directory
    os.makedirs(CONFIG.host_data_path, exist_ok=True)
    # Ensure the directory is world-writable so the container user can create files
    # (needed for rootless Docker where the mapped user may differ from the host user)
    os.chmod(CONFIG.host_data_path, 0o777)
    print(f"Host data path: {CONFIG.host_data_path}")

    def cleanup_docker():
        print(f"Cleaning up Docker container {container_name}...")
        subprocess.run(["docker", "kill", container_name], capture_output=True)
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        _clean_host_data()

    def signal_handler(signum, frame):
        cleanup_docker()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Pre-flight cleanup: remove any existing container with the same name
    print(f"Ensuring no leftover container with name {container_name}...")
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "--init",
        "--platform",
        CONFIG.DOCKER_PLATFORM,
        "--cpuset-cpus",
        f"{CONFIG.docker_cpu_set}",
        "--cpu-shares",
        "2048",
        "--cpu-quota",
        "-1",
        "--memory",
        "16g",
        "--memory-swap",
        "16g",
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
        f"{CONFIG.host_data_path}:{CONFIG.CONTAINER_DATA_PATH}",
    ]

    # In rootful Docker, run as the host user so files are owned correctly.
    # In rootless Docker, container root already maps to the host user,
    # so --user would cause double UID remapping and permission errors.
    rootless = is_rootless_docker()
    if rootless:
        print("Detected rootless Docker, skipping --user flag")
    else:
        docker_cmd.extend(["--user", f"{os.getuid()}:{os.getgid()}"])

    # Standard JAM fuzz packaging environment variables (see fuzz-proto/README.md).
    # Set first so target.json `env` and --target-env can still override them.
    docker_cmd.extend([
        "-e", "JAM_FUZZ=1",
        "-e", f"JAM_FUZZ_SPEC={CONFIG.spec}",
        "-e", f"JAM_FUZZ_DATA_PATH={CONFIG.CONTAINER_DATA_PATH}",
        "-e", f"JAM_FUZZ_SOCK_PATH={CONFIG.CONTAINER_SOCK_PATH}",
        "-e", f"JAM_FUZZ_LOG_LEVEL={CONFIG.log_level}",
    ])

    if env:
        for var in env.split():
            docker_cmd.extend(["-e", var])

    if args.target_env:
        for var in args.target_env.split():
            docker_cmd.extend(["-e", var])

    if image == CONFIG.DEFAULT_DOCKER_IMAGE:
        docker_cmd.extend(["-w", "/jam"])
        docker_cmd.extend(["-e", "HOME=/jam"])
        docker_cmd.extend(["-v", f"{CONFIG.targets_dir}/{target}/latest:/jam"])

    docker_cmd.append(image)

    # Handle cmd as string
    if cmd:
        docker_cmd.extend(shlex.split(cmd))

    # Add priority args for Linux if requested
    current_os = get_os()
    if current_os == "linux" and args.docker_elevate_priority:
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
            f"{CONFIG.docker_cpu_set}",
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

    # Show gp_version
    if target.gp_version:
        print(f"GP Version: {target.gp_version}")

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
    target_dir = Path(f"{CONFIG.targets_dir}/{target.name}/latest")
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
            print(f"Error: Target {target} not found")
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
    target_obj = get_target(target)
    if target_obj is None:
        print(f"Unknown target '{target}'")
        print(f"Available targets: {' '.join(get_available_targets())} all")
        return False

    if target_obj.is_repo_target():
        if not target_obj.supports_os(os_name):
            print(f"Error: No {os_name} version available for {target}")
            return False
        return get_github_release(target, os_name)
    if target_obj.is_docker_target():
        return get_docker_image(target)

    print(f"Error: Target {target} has neither repo nor image configured")
    return False


def handle_list_action(gp_version: Optional[str] = None) -> bool:
    """Handle the list action to show all available targets."""
    available_targets = get_available_targets()

    if gp_version == "all":
        gp_version = None

    # Filter by gp_version if provided
    if gp_version:
        filtered_targets = []
        for target_name in available_targets:
            target = get_target(target_name)
            if target and target.gp_version == gp_version:
                filtered_targets.append(target_name)
        available_targets = filtered_targets

        if not available_targets:
            print(f"No targets found for gp-version: {gp_version}")
            return True

        for target in available_targets:
            print(target)
    else:
        # Group targets by gp_version
        gp_version_groups = {}
        for target_name in available_targets:
            target = get_target(target_name)
            if target:
                target_gp_version = target.gp_version if target.gp_version else "unknown"
                if target_gp_version not in gp_version_groups:
                    gp_version_groups[target_gp_version] = []
                gp_version_groups[target_gp_version].append(target_name)

        # Sort gp versions in descending order (most recent first)
        sorted_gp_versions = sorted(gp_version_groups.keys(), reverse=True)

        # Print targets grouped by gp_version
        for i, gp_ver in enumerate(sorted_gp_versions):
            if i > 0:
                print()  # Add blank line between groups
            print(gp_ver)
            print("=" * len(gp_ver))
            for target in sorted(gp_version_groups[gp_ver]):
                print(target)

    return True


def handle_clean_action(target: str) -> bool:
    """Handle the clean action for a target or all targets."""
    if target == "all":
        targets_dir = Path(f"{CONFIG.targets_dir}")
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
        target_dir = Path(f"{CONFIG.targets_dir}/{target}")
        if target_dir.exists():
            print(f"Cleaning target {target}...")
            shutil.rmtree(target_dir)
            print(f"Target {target} cleaned successfully!")
        else:
            print(f"Target {target} not found or already clean.")
        return True


def handle_run_action(target: str, os_name: str, args) -> bool:
    """Handle the run action for a target."""
    target_obj = get_target(target)
    if target_obj is None:
        print(f"Unknown target '{target}'")
        print(f"Available targets: {' '.join(get_available_targets())}")
        return False

    if target_obj.is_docker_target():
        run_docker_image(target, args)
        return True
    if target_obj.is_repo_target():
        run_target(target, os_name, args)
        return True

    print(f"Error: Target {target} has neither repo nor image configured")
    return False


def run_target(target: str, os_name: str, args) -> None:
    target_obj = TARGETS[target]
    command = target_obj.get_cmd(os_name)

    if not command:
        print(f"Error: No run command specified for {target} on {os_name}")
        return

    target_dir = Path(f"{CONFIG.targets_dir}/{target}/latest")
    if not target_dir.exists():
        print(f"Error: Target dir not found: {target_dir}")
        print(f"Get the target first with: get {target}")
        sys.exit(1)

    full_command = f"./{command}"
    if target_obj.args is not None:
        full_command += f" {target_obj.args}"
    if args.target_args:
        full_command += f" {args.target_args}"

    if CONFIG.run_docker:
        # Ensure the default Docker image is available locally
        try:
            subprocess.run(
                ["docker", "image", "inspect", CONFIG.DEFAULT_DOCKER_IMAGE],
                check=True, capture_output=True,
            )
        except subprocess.CalledProcessError:
            print(f"Docker image '{CONFIG.DEFAULT_DOCKER_IMAGE}' not found locally. Pulling...")
            subprocess.run(
                ["docker", "pull", "--platform", CONFIG.DOCKER_PLATFORM, CONFIG.DEFAULT_DOCKER_IMAGE],
                check=True,
            )
        # Run the host binary inside a dedicated default Docker image,
        # without mutating the cached Target.
        run_docker_image(target, args, image=CONFIG.DEFAULT_DOCKER_IMAGE, cmd=full_command)
    else:
        cleanup_done = False
        target_pid = None

        def cleanup():
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
            _clean_host_data()

        def signal_handler(signum, frame):
            cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Build the child env explicitly so we don't leak overrides into the
        # parent process. JAM_FUZZ_SPEC must be forwarded since downstream
        # targets read it from their environment.
        child_env = os.environ.copy()
        child_env["JAM_FUZZ_SPEC"] = CONFIG.spec
        for var_string in (target_obj.env or "", args.target_env):
            for var in var_string.split():
                if "=" in var:
                    key, value = var.split("=", 1)
                    child_env[key] = value

        try:
            process = subprocess.Popen(full_command, shell=True, env=child_env, cwd=target_dir)
            target_pid = process.pid
            print(f"Waiting for target termination (pid={target_pid})")
            process.wait()
        finally:
            cleanup()


def main():
    global CONFIG, TARGETS

    parser = create_parser()
    args = parser.parse_args()

    CONFIG = Config.from_args(args)
    TARGETS = load_targets()

    action = args.action
    target = getattr(args, 'target', None)

    # Determine OS
    if args.os:
        os_name = args.os
    elif CONFIG.run_docker:
        # use linux, since we are running in a fixed Debian Docker image
        os_name = "linux"
    else:
        os_name = get_os()
        if os_name is None:
            print("Unsupported OS", file=sys.stderr)
            sys.exit(1)

    success = False
    if action == "info":
        success = handle_info_action(target, os_name)
    elif action == "get":
        success = handle_get_action(target, os_name)
    elif action == "run":
        success = handle_run_action(target, os_name, args)
    elif action == "clean":
        success = handle_clean_action(target)
    elif action == "list":
        gp_version = getattr(args, 'gp_version', None)
        success = handle_list_action(gp_version)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
