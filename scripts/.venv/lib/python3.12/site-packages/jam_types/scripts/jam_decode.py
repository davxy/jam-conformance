#!/usr/bin/env python3

from jam_types.fuzzer import Genesis, TraceStep, FuzzerMessage, FuzzerWireMessage, FuzzerReport
from jam_types import spec, ScaleBytes
import jam_types.simple
import jam_types.crypto
import jam_types.types
import jam_types.work
import jam_types.block
import jam_types.history
import jam_types.fuzzer
import json
import argparse
import os
import re
import sys
import inspect

def process_hex_string(hex_string):
    """Process hex string by removing whitespace and optional '0x' prefix"""
    hex_string = hex_string.strip()
    # Remove any whitespace and optional '0x' prefix
    hex_string = hex_string.replace(' ', '').replace('\n', '').replace('\t', '')
    if hex_string.startswith('0x'):
        hex_string = hex_string[2:]
    return bytes.fromhex(hex_string)


def convert_to_json(filename, subsystem_type, is_hex=False, hex_data=None):
    if hex_data:
        # Process hex data directly
        blob = process_hex_string(hex_data)
    elif is_hex:
        with open(filename, 'r') as file:
            hex_string = file.read()
            blob = process_hex_string(hex_string)
    else:
        with open(filename, 'rb') as file:
            blob = file.read()
    
    scale_bytes = ScaleBytes(blob)
    dump = subsystem_type(data=scale_bytes)
    decoded = dump.decode()
    print(json.dumps(decoded, indent=4))


def snake_to_camel(snake_str):
    """Convert snake_case to CamelCase"""
    components = snake_str.split('_')
    return ''.join(word.capitalize() for word in components)


def find_type_in_modules(type_name):
    """Find a type by name in jam_types modules, trying both original and CamelCase versions"""
    modules = [
        jam_types.simple,
        jam_types.crypto,
        jam_types.types,
        jam_types.work,
        jam_types.block,
        jam_types.history,
        jam_types.fuzzer
    ]
    
    # Try original name first
    for module in modules:
        if hasattr(module, type_name):
            attr = getattr(module, type_name)
            if inspect.isclass(attr):
                return attr
    
    # Try CamelCase version
    camel_name = snake_to_camel(type_name)
    for module in modules:
        if hasattr(module, camel_name):
            attr = getattr(module, camel_name)
            if inspect.isclass(attr):
                return attr
    
    return None


def main():
    type_mapping = {
        'genesis': Genesis,
        'trace_step': TraceStep,
        'message': FuzzerMessage,
        'wire_message': FuzzerWireMessage,
        'report': FuzzerReport,
    }
    
    parser = argparse.ArgumentParser(description='Decode binary files to JSON', 
                                   formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-x', '--hex', action='store_true', 
                       help='Treat input file as hex string instead of binary data')
    parser.add_argument('-d', '--data', type=str,
                       help='Hex data to decode directly (alternative to filename)')
    parser.add_argument('-f', '--file', dest='filename', type=str,
                       help='Binary file to decode')
    parser.add_argument('--spec', type=str, default='tiny', choices=['tiny', 'full'],
                       help='Specification to use (default: tiny)')

    type_help = "Type to use for decoding:\n"
    type_help += " * Report: fuzzer report (generally `report.bin`)\n"
    type_help += " * Genesis: trace genesis (generally `genesis.bin`)\n"
    type_help += " * TraceStep: trace step (generally `nnnnnnnn.bin`)\n"
    type_help += " * Message: fuzzer protocol message (with no length prefix)\n"
    type_help += " * WireMessage: fuzzer protocol message (with length prefix)\n"
    type_help += " * Or any type name from jam_types (e.g., 'Block', 'block', 'EntropyBuffer', 'entropy_buffer')\n"
    
    parser.add_argument('-t', '--type', type=str, help=type_help)
    
    args = parser.parse_args()
    
    spec.set_spec(args.spec)
    
    # Validate input arguments
    if not args.data and not args.filename:
        print("Error: Must specify either --file or --data option", file=sys.stderr)
        sys.exit(1)
    
    if args.data and args.filename:
        print("Error: Cannot specify both --file and --data option", file=sys.stderr)
        sys.exit(1)
    
    if args.data and args.hex:
        print("Error: --hex option is not needed when using --data (data is always treated as hex)", file=sys.stderr)
        sys.exit(1)
    
    if not args.type:
        if args.data:
            print("Error: Type must be specified when using --data option", file=sys.stderr)
            sys.exit(1)
        
        filename = os.path.basename(args.filename)
        inferred_type = os.path.splitext(filename)[0]
        if re.match(r'^\d{8}$', inferred_type):
            inferred_type = 'trace_step'
        print(f"No type specified, attempting to decode as '{inferred_type}' based on filename", file=sys.stderr)
        if inferred_type not in type_mapping:
            print(f"Error: Cannot infer type from filename '{filename}'. Please specify a type.", file=sys.stderr)
            sys.exit(1)
        args.type = inferred_type

    # Try predefined types first
    if args.type in type_mapping:
        decode_type = type_mapping[args.type]
    else:
        # Try to find the type dynamically in jam_types modules
        decode_type = find_type_in_modules(args.type)
        if decode_type is None:
            print(f"Error: Unknown type '{args.type}'. Please specify a valid type.", file=sys.stderr)
            sys.exit(1)
   
    convert_to_json(args.filename, decode_type, args.hex, args.data)

if __name__ == '__main__':
    main()
