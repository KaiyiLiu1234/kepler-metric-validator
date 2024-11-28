#!/usr/bin/env bash

set -eu -o pipefail

trap exit_all INT
exit_all() {
	pkill -P $$
}

run() {
	echo "❯ $*"
	"$@"
	echo "      ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾"
}

usage() {
    echo "Usage: $0 -r <cpu_range> -c <cpus> -d <mount_dir> -l <load_curve>"
    echo "  -r <cpu_range>   CPU range for stress-ng taskset (Default: '15')"
    echo "  -c <cpus>    Number of CPUs to use for stress-ng (Default: '1')"
    echo "  -d <mount_dir>   Directory to mount for logging (Default: '/tmp')"
    echo "  -l <load_curve>  Load curve as a comma-separated list (Default: '0:5,50:20,75:20,100:20,75:20,50:20')"
    exit 1
}

main() {

    DEFAULT_CPU_RANGE="15"
    DEFAULT_CPUS="1"
    DEFAULT_MOUNT_DIR="/tmp"
    DEFAULT_LOAD_CURVE_STR="0:5,50:20,75:20,100:20,75:20,50:20"

    # Parse command-line options
    while getopts "r:c:d:l:" opt; do
        case "$opt" in
            r) cpu_range="$OPTARG" ;;
            c) cpus="$OPTARG" ;;
            d) mount_dir="$OPTARG" ;;
            l) load_curve_str="$OPTARG" ;;
            *) usage ;;
        esac
    done

    cpu_range="${cpu_range:-$DEFAULT_CPU_RANGE}"
    cpus="${cpus:-$DEFAULT_CPUS}"
    load_curve_str="${load_curve_str:-$DEFAULT_LOAD_CURVE_STR}"
    MOUNT_DIR="${mount_dir:-$DEFAULT_MOUNT_DIR}"

    IFS=',' read -r -a load_curve <<< "$load_curve_str"

    TIME_INTERVAL_LOG="${MOUNT_DIR}/time_interval.log"

    > "$TIME_INTERVAL_LOG"

    start_time=$(date +%s)
    echo "Stress Start Time: $start_time" >> "$TIME_INTERVAL_LOG"

	for x in "${load_curve[@]}"; do
		local load="${x%%:*}"
		local time="${x##*:}s"
		run taskset -c "$cpu_range" stress-ng --cpu "$cpus" --cpu-method ackermann --cpu-load "$load" --timeout "$time"
	done

    end_time=$(date +%s)
    echo "Stress End Time: $end_time" >> "$TIME_INTERVAL_LOG"
}

main "$@"