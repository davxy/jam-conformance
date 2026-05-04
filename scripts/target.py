#!/usr/bin/env python3

import os
import sys
import subprocess
import tempfile
import shutil
import json
import urllib.request
import signal
import argparse
import random
import shlex
import string
from pathlib import Path
from typing import ClassVar, Dict, List, Optional
from dataclasses import dataclass
import ssl
import platform

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

    @classmethod
    def from_args(cls, args) -> "Config":
        cpu_default = f"0-{os.cpu_count() - 1}"

        spec = os.environ.get("JAM_FUZZ_SPEC", "tiny")
        if args.action == "run" and args.spec:
            spec = args.spec

        return cls(
            host_data_path=os.environ.get("JAM_FUZZ_DATA_PATH", "/tmp/jam_fuzz"),
            docker_cpu_set=os.environ.get("JAM_FUZZ_DOCKER_CPU_SET", cpu_default),
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
    image: Optional[str] = None
    file: Optional[str] = None
    cmd: Optional[str] = None
    args: Optional[str] = None
    env: Optional[str] = None
    gp_version: Optional[str] = None

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


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="JAM conformance target manager - download and run JAM implementation targets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                       # List all available targets
  %(prog)s get jamzig                 # Download jamzig target
  %(prog)s run boka                   # Run boka target
  %(prog)s info boka                  # Show info for boka target

Environment variables (all overridable via CLI flags listed above):
  JAM_FUZZ_TARGETS_FILE    Path to targets JSON file (default: <script>/targets.json)
  JAM_FUZZ_TARGETS_DIR     Where downloaded targets are stored (default: ./targets)
  JAM_FUZZ_DATA_PATH       Host data directory (default: /tmp/jam_fuzz)
  JAM_FUZZ_DOCKER_CPU_SET  CPU set for Docker containers (default: all cores)
  JAM_FUZZ_SPEC            Specification: tiny or full (default: tiny)
  JAM_FUZZ_LOG_LEVEL       Log level forwarded to the target (default: info)
  GITHUB_TOKEN             Optional bearer token for GitHub release lookups
        """,
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
    get_parser = subparsers.add_parser("get", help="Download target")
    get_parser.add_argument(
        "target",
        metavar="TARGET",
        help="Target to download",
    )

    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Run target")
    run_parser.add_argument(
        "target", metavar="TARGET", help="Target to run"
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
        help="Target to show info for",
    )

    # Clean subcommand
    clean_parser = subparsers.add_parser("clean", help="Clean target files")
    clean_parser.add_argument(
        "target",
        metavar="TARGET",
        help="Target to clean",
    )

    # List subcommand
    list_parser = subparsers.add_parser("list", help="List all available targets")
    list_parser.add_argument(
        "--gp-version",
        type=str,
        help="Filter targets by gp-version (e.g., 0.7.0, 0.7.1)",
    )

    return parser


def _clean_host_data() -> None:
    try:
        shutil.rmtree(CONFIG.host_data_path)
    except FileNotFoundError:
        pass


# Trailing suffixes -> extractor command. Multi-suffix entries must come first
# so e.g. .tar.gz isn't peeled as just .tar.
ARCHIVE_EXTRACTORS = [
    ((".tar", ".gz"),  ["tar", "-xzf"]),
    ((".tar", ".bz2"), ["tar", "-xjf"]),
    ((".tar", ".xz"),  ["tar", "-xJf"]),
    ((".zip",),        ["unzip"]),
    ((".tgz",),        ["tar", "-xzf"]),
    ((".tbz2",),       ["tar", "-xjf"]),
    ((".txz",),        ["tar", "-xJf"]),
    ((".tar",),        ["tar", "-xf"]),
]


def post_actions(target: Target) -> bool:
    if not target.file:
        return False

    print(f"Performing post actions for {target.file}")
    target_dir = Path(f"{CONFIG.targets_dir}/{target.name}/latest")

    # Extract nested archives by peeling off extensions
    current_file = target_dir / target.file
    while current_file.exists():
        for suffixes, cmd in ARCHIVE_EXTRACTORS:
            if tuple(current_file.suffixes[-len(suffixes):]) == suffixes:
                ext = "".join(suffixes).lstrip(".")
                print(f"Extracting {ext} archive: {current_file}")
                subprocess.run(cmd + [str(current_file)], check=True, cwd=target_dir)
                current_file.unlink()
                for _ in suffixes:
                    current_file = current_file.with_suffix("")
                break
        else:
            # No archive matched: treat as the final binary
            print(f"Making file executable: {current_file}")
            current_file.chmod(0o755)
            break

    return True


def get_docker_image(target: Target) -> bool:
    if not target.image:
        print(f"Error: No Docker image specified for {target.name}")
        return False

    print(f"Pulling Docker image: {target.image}")

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
        subprocess.run(["docker", "pull", "--platform", CONFIG.DOCKER_PLATFORM, target.image], check=True)
        print(f"Successfully pulled Docker image: {target.image}")
        return True
    except subprocess.CalledProcessError:
        print(f"Error: Failed to pull Docker image {target.image}")
        return False


def get_github_release(target: Target) -> bool:
    if not target.repo:
        print(f"Error: missing repository information for {target.name}")
        return False

    # Get the latest release tag from GitHub API
    print("Fetching latest release information...")
    try:
        url = f"https://api.github.com/repos/{target.repo}/releases/latest"
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
    download_url = f"https://github.com/{target.repo}/releases/download/{latest_tag}/{target.file}"
    print(f"Downloading from: {download_url}")

    # Download to a temporary file to avoid race conditions when
    # multiple targets share the same filename (e.g., jamzilla and jamzilla-int)
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{target.file}") as tmp:
            tmp_path = tmp.name
        urllib.request.urlretrieve(download_url, tmp_path)
    except Exception as e:
        print(f"Error: Download failed: {e}")
        return False

    print(f"Downloaded target to: {tmp_path}")
    target_dir = Path(f"{CONFIG.targets_dir}/{target.name}")
    target_dir_rev = target_dir / latest_tag

    target_dir_rev.mkdir(parents=True, exist_ok=True)
    shutil.move(tmp_path, target_dir_rev / target.file)
    print(f"* Target downloaded to: {target_dir_rev}")


    latest_link = target_dir / "latest"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(target_dir_rev.resolve())

    return post_actions(target)


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


def run_docker_image(target: Target, args) -> None:
    # Use custom container name if provided, otherwise generate unique name with random suffix
    if args.container_name:
        container_name = args.container_name
    else:
        # Generate unique container name with random suffix to allow parallel instances
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        container_name = f"{target.name}-{random_suffix}"

    print(f"Running '{target.name}' on docker image")
    print(f"Command: '{target.cmd}'")
    print(f"Container: '{container_name}'")

    try:
        print_docker_image_info(target.image)
    except (subprocess.CalledProcessError, IndexError, ValueError):
        print(f"Error: Docker image '{target.image}' not found locally.")
        print(f"Please run: {sys.argv[0]} get {target.name}")
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

    def cleanup():
        print(f"Cleaning up Docker container {container_name}...")
        subprocess.run(["docker", "kill", container_name], capture_output=True)
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        _clean_host_data()

    def signal_handler(signum, frame):
        cleanup()
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

    for var in f"{target.env or ''} {args.target_env}".split():
        docker_cmd.extend(["-e", var])

    if target.is_repo_target():
        # The target's image/cmd were overwritten upstream to wrap a host
        # binary; mount its downloaded directory at /jam so it's executable.
        docker_cmd.extend(["-w", "/jam"])
        docker_cmd.extend(["-e", "HOME=/jam"])
        docker_cmd.extend(["-v", f"{CONFIG.targets_dir}/{target.name}/latest:/jam"])

    docker_cmd.append(target.image)

    # Handle cmd as string
    if target.cmd:
        docker_cmd.extend(shlex.split(target.cmd))

    # Add priority args for Linux if requested
    if args.docker_elevate_priority and platform.system().lower() == "linux":
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
        cleanup()


def run_target(target: Target, args) -> None:
    if not target.cmd:
        print(f"Error: No run command specified for {target.name}")
        return

    target_dir = Path(f"{CONFIG.targets_dir}/{target.name}/latest")
    if not target_dir.exists():
        print(f"Error: Target dir not found: {target_dir}")
        print(f"Get the target first with: get {target.name}")
        sys.exit(1)

    full_command = f"./{target.cmd}"
    if target.args is not None:
        full_command += f" {target.args}"
    if args.target_args:
        full_command += f" {args.target_args}"

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
    # Wrap the host binary in a dedicated default Docker image.
    # `target.repo` is left intact, which run_docker_image uses as the
    # signal to mount the downloaded host-binary directory into /jam.
    target.image = CONFIG.DEFAULT_DOCKER_IMAGE
    target.cmd = full_command
    run_docker_image(target, args)


def print_target_info(target: Target) -> None:
    """Print detailed information about a target."""
    print(f"Name: {target.name}")

    if target.gp_version:
        print(f"GP Version: {target.gp_version}")

    target_type = []
    if target.is_docker_target():
        target_type.append("Docker")
    if target.is_repo_target():
        target_type.append("Repository")
    print(f"Type: {', '.join(target_type)}")

    if target.is_repo_target():
        print(f"Repository: https://github.com/{target.repo}")
        target_dir = Path(f"{CONFIG.targets_dir}/{target.name}/latest")
        if target_dir.exists():
            print(f"Downloaded: {target_dir}")
    elif target.is_docker_target():
        try:
            print_docker_image_info(target.image)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Status: Not downloaded (Docker image not found locally)")
    else:
        print("Status: Not downloaded")

    if target.file:
        print(f"File: {target.file}")
    if target.cmd:
        print(f"Command: {target.cmd}")
    if target.args:
        print(f"Arguments: {target.args}")
    if target.env:
        print(f"Environment: {target.env}")


def handle_info_action(target: Target) -> bool:
    """Handle the info action for a target."""
    print_target_info(target)
    return True


def handle_get_action(target: Target) -> bool:
    """Handle the get action for a target."""
    print(f"Downloading {target.name}...")
    if target.is_repo_target():
        return get_github_release(target)
    return get_docker_image(target)


def handle_list_action(all_targets: Dict[str, Target], gp_version: Optional[str]) -> bool:
    """Handle the list action to show all available targets."""
    names = sorted(all_targets)

    if gp_version:
        filtered = [n for n in names if all_targets[n].gp_version == gp_version]
        if not filtered:
            print(f"No targets found for gp-version: {gp_version}")
            return True
        for name in filtered:
            print(name)
        return True

    # Group by gp_version, most recent first
    groups: Dict[str, List[str]] = {}
    for name in names:
        v = all_targets[name].gp_version or "unknown"
        groups.setdefault(v, []).append(name)

    for i, gp_ver in enumerate(sorted(groups, reverse=True)):
        if i > 0:
            print()
        print(gp_ver)
        print("=" * len(gp_ver))
        for name in sorted(groups[gp_ver]):
            print(name)
    return True


def handle_clean_action(target: Target) -> bool:
    """Handle the clean action for a target."""
    target_dir = Path(f"{CONFIG.targets_dir}/{target.name}")
    if target_dir.exists():
        print(f"Cleaning target {target.name}...")
        shutil.rmtree(target_dir)
        print(f"Target {target.name} cleaned successfully!")
    else:
        print(f"Target {target.name} not found or already clean.")
    return True


def handle_run_action(target: Target, args) -> bool:
    """Handle the run action for a target."""
    if target.is_docker_target():
        run_docker_image(target, args)
    else:
        run_target(target, args)
    return True


def main():
    global CONFIG

    parser = create_parser()
    args = parser.parse_args()

    CONFIG = Config.from_args(args)
    all_targets = load_targets()

    action = args.action
    target = getattr(args, 'target', None)

    success = False
    if action == "list":
        success = handle_list_action(all_targets, args.gp_version)
    else:
        # info / get / run / clean all need a single resolved Target
        target_obj = all_targets.get(target)
        if target_obj is None:
            print(f"Unknown target '{target}'")
            print(f"Available targets: {' '.join(sorted(all_targets))}")
            sys.exit(1)
        if action == "info":
            success = handle_info_action(target_obj)
        elif action == "get":
            success = handle_get_action(target_obj)
        elif action == "run":
            success = handle_run_action(target_obj, args)
        elif action == "clean":
            success = handle_clean_action(target_obj)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
