#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Change to the script's directory
cd $SCRIPT_DIR

# Set DEFAULT_SOCK to /tmp/jam_target.sock if not already set
TARGET_SOCK=${DEFAULT_SOCK:-"/tmp/jam_target.sock"}

# Used to run binaries when target is not provided as a docker image
SENSIBLE_DOCKER_IMAGE="debian:stable-slim"

# Target configuration using associative array with dot notation
declare -A TARGETS

# === VINWOLF ===
TARGETS[vinwolf.repo]="bloppan/conformance_testing"
TARGETS[vinwolf.clone]=1
TARGETS[vinwolf.file.linux]="linux/tiny/x86_64/vinwolf-target"
TARGETS[vinwolf.cmd.linux]="${TARGETS[vinwolf.file.linux]}"
TARGETS[vinwolf.args]="--fuzz $TARGET_SOCK"

# === JAMZIG ===
TARGETS[jamzig.repo]="jamzig/conformance-releases"
TARGETS[jamzig.clone]=1
TARGETS[jamzig.file.linux]="tiny/linux/x86_64/jam_conformance_target"
TARGETS[jamzig.file.macos]="tiny/linux/aarch64/jam_conformance_target"
TARGETS[jamzig.cmd.linux]="${TARGETS[jamzig.file.linux]}"
TARGETS[jamzig.cmd.macos]="${TARGETS[jamzig.file.macos]}"
TARGETS[jamzig.args]="--socket $TARGET_SOCK"

# === PYJAMAZ ===
TARGETS[pyjamaz.image]="jamdottech/pyjamaz:latest"
TARGETS[pyjamaz.cmd]="fuzzer target --db-path=/tmp/pyjamaz_fuzzer_db --socket-path $TARGET_SOCK"

# === JAMPY ===
TARGETS[jampy.repo]="dakk/jampy-releases"
TARGETS[jampy.clone]=1
TARGETS[jampy.file.linux]="dist/jampy-target-0.7.0_x86-64.zip"
TARGETS[jampy.cmd]="jampy-target-0.7.0_x86-64/jampy-target-0.7.0_x86-64"
TARGETS[jampy.args]="--socket-file $TARGET_SOCK"

# === JAMDUNA ===
TARGETS[jamduna.repo]="jam-duna/jamtestnet"
TARGETS[jamduna.file.linux]="duna_target_linux"
TARGETS[jamduna.file.macos]="duna_target_mac"
TARGETS[jamduna.cmd.linux]="${TARGETS[jamduna.file.linux]}"
TARGETS[jamduna.cmd.macos]="${TARGETS[jamduna.file.macos]}"
TARGETS[jamduna.args]="-socket $TARGET_SOCK"

# === JAMIXIR ===
TARGETS[jamixir.repo]="jamixir/jamixir-releases"
TARGETS[jamixir.file.linux]="jamixir_linux-x86-64_0.7.0_tiny.tar.gz"
TARGETS[jamixir.cmd]="jamixir"
TARGETS[jamixir.args]="fuzzer --log info --socket-path $TARGET_SOCK"

# === JAVAJAM ===
TARGETS[javajam.image]="ghcr.io/methodfive/javajam:latest-amd64"
TARGETS[javajam.cmd]="fuzz $TARGET_SOCK"

# === JAMZILLA ===
TARGETS[jamzilla.repo]="ascrivener/jamzilla-conformance-releases"
TARGETS[jamzilla.file.linux]="fuzzserver-tiny-amd64-linux"
TARGETS[jamzilla.file.macos]="fuzzserver-tiny-arm64-darwin"
TARGETS[jamzilla.cmd.linux]="fuzzserver-tiny-amd64-linux"
TARGETS[jamzilla.cmd.macos]="fuzzserver-tiny-arm64-darwin"
TARGETS[jamzilla.args]="-socket $TARGET_SOCK"

# === SPACEJAM ===
TARGETS[spacejam.repo]="spacejamapp/specjam"
TARGETS[spacejam.file.linux]="spacejam-0.7.0-linux-amd64.tar.gz"
TARGETS[spacejam.file.macos]="spacejam-0.7.0-macos-arm64.tar.gz"
TARGETS[spacejam.cmd]="spacejam fuzz target $TARGET_SOCK"

# === TSJAM ===
TARGETS[tsjam.repo]="vekexasia/tsjam-releases"
TARGETS[tsjam.file.linux]="tsjam-fuzzer-target.tgz.zip"
TARGETS[tsjam.cmd]="tsjam-fuzzer-target/jam-fuzzer-target --socket $TARGET_SOCK"
TARGETS[tsjam.env]="JAM_CONSTANTS=tiny"

# === BOKA ===
TARGETS[boka.image]="acala/boka:latest"
TARGETS[boka.cmd]="fuzz target --socket-path $TARGET_SOCK"

# === TURBOJAM ===
TARGETS[turbojam.image]="r2rationality/turbojam-fuzz:latest"
TARGETS[turbojam.cmd]="fuzzer-api $TARGET_SOCK"

# === GRAYMATTER ===
TARGETS[graymatter.image]="ghcr.io/jambrains/graymatter/gm:conformance-fuzzer-latest"
TARGETS[graymatter.cmd]="fuzz-m1-target --stay-open --listen $TARGET_SOCK"

# === FASTROLL ===
TARGETS[fastroll.repo]="fastroll-jam/fastroll-releases"
TARGETS[fastroll.file.linux]="fastroll-linux-x86_64-tiny"
TARGETS[fastroll.file.macos]="fastroll-macos-aarch64-tiny"
TARGETS[fastroll.cmd.linux]="${TARGETS[fastroll.file.linux]}"
TARGETS[fastroll.cmd.macos]="${TARGETS[fastroll.file.macos]}"
TARGETS[fastroll.args]="fuzz --socket $TARGET_SOCK"

# === GOSSAMER ===
TARGETS[gossamer.repo]="chainsafe/gossamer-jam-releases"
TARGETS[gossamer.file.linux]="gossamer-jam-tiny-linux-amd64"
TARGETS[gossamer.file.macos]="gossamer-jam-tiny-macos-arm64"
TARGETS[gossamer.cmd.linux]="${TARGETS[gossamer.file.linux]}"
TARGETS[gossamer.cmd.macos]="${TARGETS[gossamer.file.macos]}"
TARGETS[gossamer.args]="target --socket $TARGET_SOCK"

### Auxiliary functions:

show_usage() {
    local script_name=$1
    echo "Usage: $script_name <get|run> <target>"
    echo "Available targets: ${AVAILABLE_TARGETS[*]} all"
    echo "Available OSes: linux, macos"
    echo "Default OS: linux (auto-detected)"
}

validate_target() {
    if [[ "$TARGET" != "all" ]] && ! is_repo_target "$TARGET" && ! is_docker_target "$TARGET"; then
        echo "Unknown target '$TARGET'" >&2
        echo "Available targets: ${AVAILABLE_TARGETS[*]} all" >&2
        return 1
    fi
    return 0
}

get_os() {
    case "$(uname -s)" in
        Linux) echo "linux" ;;
        Darwin) echo "macos" ;;
        *) echo "Unsupported OS: $UNAME_S" >&2; exit 1 ;;
    esac
}

validate_os() {
    local os=$1
    if [[ "$os" != "linux" && "$os" != "macos" ]]; then
        echo "Error: Unsupported OS '$os'" >&2
        echo "Supported OSes: linux, macos" >&2
        return 1
    fi
    return 0
}

is_docker_target() {
    [[ -v TARGETS[$TARGET.image] ]]
}

is_repo_target() {
    [[ -v TARGETS[$TARGET.repo] ]]
}

# Get list of available targets
get_available_targets() {
    local targets=()
    for key in "${!TARGETS[@]}"; do
        local target_name="${key%%.*}"
        if [[ ! " ${targets[@]} " =~ " ${target_name} " ]]; then
            targets+=("$target_name")
        fi
    done
    printf '%s\n' "${targets[@]}" | sort
}

AVAILABLE_TARGETS=($(get_available_targets))

# Returns 0 if the target supports the given os, 1 otherwise
target_supports_os() {
    local target=$1
    local os=$2
    # If no file entry, support all OSes
    if [[ ! -v TARGETS[$target.file] ]]; then
        return 0
    fi
    # If file.<os> entry exists, support only that OS
    if [[ -v TARGETS[$target.file.$os] ]]; then
        return 0
    fi
    # If file entry exists, support both OSes
    if [[ -v TARGETS[$target.file] ]]; then
        return 0
    fi
    echo "Error: No $os version available for $target" >&2
    return 1
}

# Function to get the correct file for a target and os
get_target_file() {
    local target=$1
    local os=$2
    local file="${TARGETS[${target}.file.${os}]}"
    if [ -z "$file" ]; then
        file="${TARGETS[${target}.file]}"
        if [ -z "$file" ]; then
            echo ""
            return 1
        fi
    fi
    echo "$file"
    return 0
}
 
# Check if there is a defined "post" action.
# If not check if file is an archive and extract it, or make it executable
post_actions() {
    local target=$1
    local os=$2
    local file=$(get_target_file "$target" "$os")
    echo "Performing post actions"
    pushd "targets/$target/latest"
    local post="${TARGETS[$target.post]}"
    if [ ! -z "$post" ]; then
        bash -c "$post"
    else
        # Extract nested archives by peeling off extensions
        local current_file="$file"     
        while [[ -f "$current_file" ]]; do
            case "$current_file" in
                *.zip)
                    echo "Extracting zip archive: $current_file"
                    unzip "$current_file" && rm "$current_file"
                    current_file="${current_file%.zip}"
                    ;;
                *.tar.gz)
                    echo "Extracting tar.gz archive: $current_file"
                    tar -xzf "$current_file" && rm "$current_file"
                    current_file="${current_file%.tar.gz}"
                    ;;
                *.tgz)
                    echo "Extracting tgz archive: $current_file"
                    tar -xzf "$current_file" && rm "$current_file"
                    current_file="${current_file%.tgz}"
                    ;;
                *.tar.bz2)
                    echo "Extracting tar.bz2 archive: $current_file"
                    tar -xjf "$current_file" && rm "$current_file"
                    current_file="${current_file%.tar.bz2}"
                    ;;
                *.tbz2)
                    echo "Extracting tbz2 archive: $current_file"
                    tar -xjf "$current_file" && rm "$current_file"
                    current_file="${current_file%.tbz2}"
                    ;;
                *.tar.xz)
                    echo "Extracting tar.xz archive: $current_file"
                    tar -xJf "$current_file" && rm "$current_file"
                    current_file="${current_file%.tar.xz}"
                    ;;
                *.txz)
                    echo "Extracting txz archive: $current_file"
                    tar -xJf "$current_file" && rm "$current_file"
                    current_file="${current_file%.txz}"
                    ;;
                *.tar)
                    echo "Extracting tar archive: $current_file"
                    tar -xf "$current_file" && rm "$current_file"
                    current_file="${current_file%.tar}"
                    ;;
                *)
                    # Not an archive, make it executable and stop
                    echo "Making file executable: $current_file"
                    chmod +x "$current_file"
                    break
                    ;;
            esac
        done
    fi
    popd

    return 0
}

clone_github_repo() {
    local target=$1
    local os=$2
    local repo=$3
    local temp_dir=$(mktemp -d)

    git clone "https://github.com/$repo" --depth 1 "$temp_dir"
    local commit_hash=$(cd "$temp_dir" && git rev-parse --short HEAD)
    echo "Cloning last revisin: $commit_hash"
    local target_dir="targets/$target"
    echo "Cloned to $target_dir"

    mkdir -p "$target_dir"
    local target_dir_rev="$target_dir/$commit_hash"
    mv "$temp_dir" "$target_dir_rev"

    rm -f "$target_dir/latest"
    ln -s "$(realpath $target_dir_rev)" "$target_dir/latest"

    post_actions "$target" "$os"
   
    return 0
}

get_docker_image() {
    local target=$1
    local docker_image="${TARGETS[$target.image]}"

    if [ -z "$docker_image" ]; then
        echo "Error: No Docker image specified for $target"
        return 1
    fi

    echo "Pulling Docker image: $docker_image"

    if ! command -v docker &> /dev/null; then
        echo "Error: Docker is not installed or not in PATH"
        return 1
    fi

    if ! docker info &> /dev/null; then
        echo "Error: Docker daemon is not running or not accessible"
        echo "Please start Docker and try again"
        return 1
    fi

    if ! docker pull "$docker_image"; then
        echo "Error: Failed to pull Docker image $docker_image"
        return 1
    fi

    echo "Successfully pulled Docker image: $docker_image"

    return 0
}

get_github_release() {
    local target=$1
    local os=$2
    local repo="${TARGETS[$target.repo]}"
    local file=$(get_target_file "$target" "$os")
    local clone="${TARGETS[$target.clone]}"

    if [ -z "$repo" ]; then
        echo "Error: missing repository information for $target"
        return 1
    fi

    if [[ "$clone" == 1 ]]; then
        echo "Info: No release file specified for $target on $os, cloning repository instead"
        clone_github_repo "$target" "$os" "$repo"
        return 0
    fi

    # Get the latest release tag from GitHub API
    echo "Fetching latest release information..."
    local latest_tag=$(curl -s "https://api.github.com/repos/$repo/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    if [ -z "$latest_tag" ]; then
        echo "Error: Could not fetch latest release tag"
        return 1
    fi
    echo "Latest version: $latest_tag"

    # Construct download URL
    local download_url="https://github.com/$repo/releases/download/$latest_tag/$file"
    echo "Downloading from: $download_url"

    # Download the file
    curl -L -o "$file" "$download_url"
    if [ $? -ne 0 ]; then
        echo "Error: Download failed"
        return 1
    fi

    local target_dir="targets/$target"
    local target_dir_rev="$target_dir/${latest_tag}"

    mkdir -p "$target_dir_rev"
    mv "$file" "$target_dir_rev/"

    rm -f "$target_dir/latest"
    ln -s "$(realpath $target_dir_rev)" "$target_dir/latest"

    post_actions "$target" "$os"
}

# Run the target in a performance optimized docker instance
#
# Performance optimization parameters:
# - nice -n -20: Sets highest CPU priority for docker process (-20 is highest, 19 is lowest)
# - ionice -c1 -n0: Sets real-time I/O scheduling class with highest priority (0)
# - --cpuset-cpus="0-16": Restricts container to use only CPU cores 0-16
# - --cpu-shares=2048: Sets relative CPU weight (default 1024), higher = more CPU priority
# - --security-opt seccomp=unconfined: Disables seccomp filtering for better performance
# - --security-opt apparmor=unconfined: Disables AppArmor restrictions for better performance
# - --cap-add=SYS_NICE: Allows container to change process priorities
# - --cap-add=SYS_RESOURCE: Allows container to modify resource limits
# - --platform linux/amd64: Forces x86_64 architecture for consistency
run_docker_image() {
    local target=$1
    local image="${TARGETS[$target.image]}"
    local cmd="${TARGETS[$target.cmd]}"
    local env="${TARGETS[$target.env]}"

    echo "Running $target on docker image $image (command $cmd)"

    if ! docker image inspect "$image" >/dev/null 2>&1; then
        if [[ $image != $SENSIBLE_DOCKER_IMAGE ]]; then
            echo "Error: Docker image '$image' not found locally."
            echo "Please run: $0 get $target"
            exit 1
        fi
    fi

    cleanup_docker() {
        echo "Cleaning up Docker container $target..."
        docker kill "$target" 2>/dev/null || true
        rm -f "$TARGET_SOCK"
    }

    trap cleanup_docker EXIT INT TERM

    local env_args=""
    if [ -n "$env" ]; then
        env_args="-e $env"
    fi

    local wd_args=""
    if [[ $image == $SENSIBLE_DOCKER_IMAGE ]]; then
        wd_args="-w /jam"
    fi
    

    sudo chrt -f 99 nice -n -20 ionice -c1 -n0 taskset -c 0-32 \
    docker run \
        --rm \
        --name "$target" \
        --user "$(id -u):$(id -g)" \
        --platform linux/amd64 \
        --cpuset-cpus="0-32" \
        --cpu-shares=2048 \
        --memory=8g \
        --memory-swap=8g \
        --oom-kill-disable \
        --shm-size=1g \
        --ulimit nofile=65536:65536 \
        --ulimit nproc=32768:32768 \
        --sysctl net.core.somaxconn=65535 \
        --sysctl net.ipv4.tcp_tw_reuse=1 \
        --security-opt seccomp=unconfined \
        --security-opt apparmor=unconfined \
        --cap-add=SYS_NICE \
        --cap-add=SYS_RESOURCE \
        --cap-add=IPC_LOCK \
        -v /tmp:/tmp \
        -v "$SCRIPT_DIR/targets/$target/latest":/jam \
        $wd_args \
        $env_args \
        "$image" $cmd &

    TARGET_PID=$!
    echo "Waiting for target termination (pid=$TARGET_PID)"
    wait $TARGET_PID
}

run() {
    local target=$1
    local os=$2
    local command=""
    local args="${TARGETS[${target}.args]}"
    # Prefer os-specific command, fallback to generic
    if [[ -v TARGETS[${target}.cmd.${os}] ]]; then
        command="${TARGETS[${target}.cmd.${os}]}"
    elif [[ -v TARGETS[${target}.cmd] ]]; then
        command="${TARGETS[${target}.cmd]}"
    else
        echo "Error: No run command specified for $target on $os"
        return 1
    fi

    local target_dir="targets/$target/latest"
    if [ ! -d "$target_dir" ]; then
        echo "Error: Target dir not found: $target_dir"
        # Try to find the newest directory as fallback
        local base_dir="targets/$target"
        if [ -d "$base_dir" ]; then
            local newest_dir=$(find "$base_dir" -maxdepth 1 -type d ! -name "$(basename "$base_dir")" -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
            if [ -n "$newest_dir" ] && [ -d "$newest_dir" ]; then
                echo "Using newest available directory: $newest_dir"
                target_dir="$newest_dir"
            else
                echo "Get the target first with: get $target"
                exit 1
            fi
        else
            echo "Get the target first with: get $target"
            exit 1
        fi
    fi

    # Overwrite target information and run it in a dedicated docker image
    TARGETS[$target.image]="$SENSIBLE_DOCKER_IMAGE"
    TARGETS[$target.cmd]="./$command $args"
    run_docker_image "$target"
}

### Main script logic
if [ $# -lt 2 ]; then
    show_usage "$0"
    exit 1
fi

ACTION="$1"
TARGET="$2"
OS=$(get_os)

validate_os "$OS" || exit 1
validate_target "$TARGET" || exit 1

echo "Action: $ACTION, Target: $TARGET, OS: $OS"

case "$ACTION" in
    "get")
        if [ "$TARGET" = "all" ]; then
            echo "Downloading all targets: ${AVAILABLE_TARGETS[*]}"
            failed_targets=()
            for TARGET in "${AVAILABLE_TARGETS[@]}"; do
                echo "Downloading $TARGET for $OS..."
                if is_repo_target; then
                    if target_supports_os "$TARGET" "$OS"; then
                        if ! get_github_release "$TARGET" "$OS"; then
                            echo "Failed to download $TARGET"
                            failed_targets+=("$TARGET")
                        fi
                    else
                        echo "Skipping $TARGET: No $OS support available"
                    fi
                elif is_docker_target; then
                    if ! get_docker_image "$TARGET"; then
                        echo "Failed to pull Docker image for $TARGET"
                        failed_targets+=("$TARGET")
                    fi
                else
                    echo "Error: Unknown target type for $TARGET"
                    failed_targets+=("$TARGET")
                fi
                echo ""
            done
            # Report summary
            if [ ${#failed_targets[@]} -eq 0 ]; then
                echo "All targets downloaded successfully!"
            else
                echo "Failed to download the following targets: ${failed_targets[*]}"
                echo "Successfully downloaded: $((${#AVAILABLE_TARGETS[@]} - ${#failed_targets[@]})) out of ${#AVAILABLE_TARGETS[@]} targets"
                exit 1
            fi
        elif is_repo_target "$TARGET"; then
            if target_supports_os "$TARGET" "$OS"; then
                get_github_release "$TARGET" "$OS"
            else
                exit 1
            fi
        elif is_docker_target "$TARGET"; then
            get_docker_image "$TARGET"
        else
            echo "Unknown target '$TARGET'"
            echo "Available targets: ${AVAILABLE_TARGETS[*]} all"
            exit 1
        fi
        ;;
    "run")
        if is_docker_target "$TARGET"; then
            run_docker_image "$TARGET"
        elif is_repo_target "$TARGET"; then
            run "$TARGET" "$OS"
        else
            echo "Unknown target '$TARGET'"
            echo "Available targets: ${AVAILABLE_TARGETS[*]}"
            exit 1
        fi
        ;;
    *)
        echo "Unknown action '$ACTION'"
        echo "Usage: $0 <get|run> <target>"
        exit 1
        ;;
esac
