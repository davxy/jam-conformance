#!/usr/bin/env python
#
# Version 0.1.1

import argparse
import socket
import struct
import sys
import json
from pathlib import Path
from jam_types.fuzzer import FuzzerMessage, FEATURES_MASK, FEATURE_ANCESTRY, FEATURE_FORKS
from jam_types import ScaleBytes, spec


def raw_to_json(data):   
    scale_bytes = ScaleBytes(data)
    decoded = FuzzerMessage(data=scale_bytes).decode()
    return decoded

def response_check(response, precomputed) -> bool:
    expected_kind = next(iter(precomputed.keys()), None)
    message_kind = next(iter(response.keys()), None)

    if expected_kind != message_kind:
        print(f"Unexpected message kind {message_kind}, expected {expected_kind}")
        return False

    if message_kind == "error":
        # Error messages are out of spec and custom
        return True

    if message_kind == "peer_info":      
        target_peer_info = response["peer_info"]
        precomputed_peer_info = precomputed.get("peer_info", {})

        # Check features
        features_got = target_peer_info.get("fuzz_features")
        if features_got & ~FEATURES_MASK != 0:
            print(f"Unexpected Fuzzer features enabled: 0x{features_got:08x}")
            print("Valid features:")
            print(f"- Ancestry: 0x{FEATURE_ANCESTRY:08x}")
            print(f"- Forks: 0x{FEATURE_FORKS:08x}")
            return False
            
        
        # Check Fuzz version
        fuzz_version_got = target_peer_info.get("fuzz_version")
        fuzz_version_exp = precomputed_peer_info.get("fuzz_version")
        if fuzz_version_exp != fuzz_version_got:
            print("Unexpected Fuzzer protocol version.")
            print(f"Expected: {fuzz_version_exp}")
            print(f"Got:      {fuzz_version_got}")
            return False
        # Check JAM version
        jam_version_got = target_peer_info.get("jam_version")
        jam_version_exp = precomputed_peer_info.get("jam_version")
        if jam_version_exp != jam_version_got:
            print("Warning: Unexpected JAM protocol version.")
            print(f"Expected: {jam_version_exp}")
            print(f"Got:      {jam_version_got}")
        return True

    # All other messages must match
    is_matching = response == precomputed
    if not is_matching:
        print("Unexpected target response")
        print("--------------------------")
        print("Expected:")
        print(json.dumps(precomputed, indent=4))
        print("---")
        print("Returned:")
        print(json.dumps(response, indent=4))
    return is_matching


def print_message(json_obj, is_fuzzer, verbose):
    message_kind = next(iter(json_obj.keys()), None)
    if is_fuzzer:
        pre = "TX"
    else:
        pre = "RX"
    print(f"{pre}: {message_kind}")
    if verbose:
        print(json.dumps(json_obj, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Minifuzz - Send fuzzer messages to target socket')
    parser.add_argument('-d', '--trace-dir', required=True, 
                       help='Directory containing pre-constructed message files')
    parser.add_argument('-s', '--spec', type=str, default='tiny', choices=['tiny', 'full'],
                       help='Specification to use (default: tiny)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output (default: false)')
    parser.add_argument('--target-sock', default='/tmp/jam_target.sock',
                       help='Target socket path (default: /tmp/jam_target.sock)')
    parser.add_argument('--stop-after', type=int, default=1000,
                       help='Stop after processing this many file pairs (default: 1000)')

    args = parser.parse_args()

    spec.set_spec(args.spec)    
    
    trace_dir = Path(args.trace_dir)
    if not trace_dir.exists() or not trace_dir.is_dir():
        print(f"Error: Trace directory '{trace_dir}' does not exist or is not a directory")
        sys.exit(1)
    
    # Collect fuzzer and target session files
    fuzzer_files = []
    target_files = []
    for file_path in trace_dir.glob('*.bin'):
        if 'fuzzer' in file_path.name:
            fuzzer_files.append(file_path)
        elif 'target' in file_path.name:
            target_files.append(file_path)
    fuzzer_files.sort()
    target_files.sort()
    if len(target_files) != len(fuzzer_files):
        print(f"Error: Mismatch in file counts - {len(fuzzer_files)} fuzzer files but {len(target_files)} target files")
        sys.exit(1)
    
    print(f"Found {len(fuzzer_files)} fuzzer files to process")
    
    # Connect to target socket
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(args.target_sock)
        print(f"Connected to target socket: {args.target_sock}")
    except Exception as e:
        print(f"Error connecting to socket '{args.target_sock}': {e}")
        sys.exit(1)
    
    try:
        for i, (fuzzer_file, target_file) in enumerate(zip(fuzzer_files, target_files)):
            if i >= args.stop_after:
                print(f"\nStopping after {args.stop_after} file pairs as requested")
                break
            print("\n==========================================================================")
            print(f"Processing pair {i+1}: {fuzzer_file.name} <-> {target_file.name}")
            
            # Read fuzzer file binary content
            try:
                with open(fuzzer_file, 'rb') as f:
                    request_bytes = f.read()
            except Exception as e:
                print(f"Error reading fuzzer file '{fuzzer_file}': {e}")
                break

            try:
                request_msg = raw_to_json(request_bytes)
                print_message(request_msg, True, args.verbose)
            except Exception as e:
                print(f"Error decoding precomputed fuzzer request: {e}")
                break
            
            try:
                # Send fuzzer data length (4 bytes, little endian)
                request_len = len(request_bytes)
                request_len_bytes = struct.pack('<I', request_len)
                sock.sendall(request_len_bytes)
                # Send fuzzer file data
                sock.sendall(request_bytes)
                if args.verbose:
                    print(f"Sent {request_len} bytes from fuzzer file")
            except Exception as e:
                print(f"Error sending fuzzer request: {e}")
                break
            
            
            # Wait for response
            try:
                # Read response length (4 bytes, little endian)
                response_len_bytes = sock.recv(4)
                if len(response_len_bytes) != 4:
                    print("Error: Could not read response length")
                    break
                response_len = struct.unpack('<I', response_len_bytes)[0]
                # Read response data
                response_data = b''
                while len(response_data) < response_len:
                    chunk = sock.recv(response_len - len(response_data))
                    if not chunk:
                        print("Error: Connection closed while reading response")
                        break
                    response_data += chunk
                if args.verbose:
                    print(f"Received {response_len} bytes response")
            except Exception as e:
                print(f"Error reading target response: {e}")
                break

            # Decode reponse
            try:
                response_msg = raw_to_json(response_data)
                print_message(response_msg, False, args.verbose)
            except Exception as e:
                print(f"Error decoding target response: {e}")
                break
                
            # Read target file for some comparison
            try:
                with open(target_file, 'rb') as f:
                    precomputed_data = f.read()
                precomputed_response_msg = raw_to_json(precomputed_data)                   
            except Exception as e:
                print(f"Error reading precomputed target file '{target_file}': {e}")
                break

            if not response_check(response_msg, precomputed_response_msg):
                break               
    
    finally:
        sock.close()
        print("Connection closed")


if __name__ == '__main__':
    main()
