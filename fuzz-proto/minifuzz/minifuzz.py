#!/usr/bin/env python

import argparse
import os
import socket
import struct
import sys
import json
from pathlib import Path
from jam_types.fuzzer import FuzzerMessage
from jam_types import ScaleBytes


def raw_to_json(data):   
    scale_bytes = ScaleBytes(data)
    print("AAAAAAAAAAAA")
    decoded = FuzzerMessage(data=scale_bytes).decode()
    print("BBBBBBBBBB")
    # print(decoded)
    # print(json.dumps(decoded, indent=4))
    return decoded

def print_message(direction, json_obj):
    print(f"======================={direction}==========================")
    # if json_obj and isinstance(json_obj, dict):
    #     first_key = next(iter(json_obj.keys()), None)
    #     if first_key == "set_state":
    #         print("set_state")
    #     else:
    #         print(json.dumps(json_obj, indent=2))
    # else:
    #     print(json.dumps(json_obj, indent=2))

def main():
    parser = argparse.ArgumentParser(description='Minifuzz - Send fuzzer messages to target socket')
    parser.add_argument('--trace-dir', required=True, 
                       help='Directory containing pre-constructed message files')
    parser.add_argument('--target-sock', default='/tmp/jam-target.sock',
                       help='Target socket path (default: /tmp/jam-target.sock)')
    
    args = parser.parse_args()
    
    trace_dir = Path(args.trace_dir)
    if not trace_dir.exists() or not trace_dir.is_dir():
        print(f"Error: Trace directory '{trace_dir}' does not exist or is not a directory")
        sys.exit(1)
    
    # Find all binary files containing "fuzzer" in the name
    fuzzer_files = []
    for file_path in trace_dir.glob('*.bin'):
        if 'fuzzer' in file_path.name:
            fuzzer_files.append(file_path)
    if not fuzzer_files:
        print(f"No fuzzer binary files found in '{trace_dir}'")
        sys.exit(1)
    fuzzer_files.sort()

    target_files = []
    for file_path in trace_dir.glob('*.bin'):
        if 'target' in file_path.name:
            target_files.append(file_path)
    if not target_files:
        print(f"No target binary files found in '{trace_dir}'")
        sys.exit(1)
    target_files.sort()

    # Check that target_files and fuzzer_files sequences have the same length
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
            fuzzer_data =b""
            print(f"Processing pair {i+1}: {fuzzer_file.name} -> {target_file.name}")
            
            # Read fuzzer file binary content
            try:
                with open(fuzzer_file, 'rb') as f:
                    fuzzer_data = f.read()
            except Exception as e:
                print(f"Error reading fuzzer file '{fuzzer_file}': {e}")
                continue

            print("BYTES COUNT: ", len(fuzzer_data))
            json_obj = raw_to_json(fuzzer_data)
            # print_message("TX", json_obj)
            
            # Send fuzzer data length (4 bytes, little endian)
            length = len(fuzzer_data)
            length_bytes = struct.pack('<I', length)
            sock.sendall(length_bytes)
            
            # Send fuzzer file data
            sock.sendall(fuzzer_data)
            print(f"Sent {length} bytes from fuzzer file")
            
            # Wait for response
            try:
                # Read response length (4 bytes, little endian)
                response_length_bytes = sock.recv(4)
                if len(response_length_bytes) != 4:
                    print("Error: Could not read response length")
                    break
                
                response_length = struct.unpack('<I', response_length_bytes)[0]
                
                # Read response data
                response_data = b''
                while len(response_data) < response_length:
                    chunk = sock.recv(response_length - len(response_data))
                    if not chunk:
                        print("Error: Connection closed while reading response")
                        break
                    response_data += chunk
                
                print(f"Received {len(response_data)} bytes response")

                # json_obj = raw_to_json(response_data)
                # print_message("RX", json_obj)

                
                # Read target file for comparison
                try:
                    with open(target_file, 'rb') as f:
                        target_data = f.read()

                    # raw_to_json(response_data)
                   
                    if response_data == target_data:
                        print(f"✓ Response matches target file {target_file.name}")
                    else:
                        print(f"✗ Response does NOT match target file {target_file.name}")
                        print(f"  Expected {len(target_data)} bytes, got {len(response_data)} bytes")
                        
                except Exception as e:
                    print(f"Error reading target file '{target_file}': {e}")
                
            except Exception as e:
                print(f"Error reading response: {e}")
                break
    
    finally:
        sock.close()
        print("Connection closed")


if __name__ == '__main__':
    main()
