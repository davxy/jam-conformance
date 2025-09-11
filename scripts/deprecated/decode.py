#!/usr/bin/env python3
 
from jam_types import Struct, Header, OpaqueHash, ByteArray, ByteSequence, Vec, ScaleBytes, Block, String, Enum, Null, Bool, U8, U32, F64, TimeSlot
from jam_types import spec, n
import json
import argparse
import os
import re
import sys

class TrieKey(ByteArray):
    element_count = 31

class KeyValue(Struct):
    type_mapping = [
        ('key', n(TrieKey)),
        ('value', n(ByteSequence))
    ]

class KeyValues(Vec):
    sub_type = n(KeyValue)

class RawState(Struct):
    type_mapping = [
        ('state_root', n(OpaqueHash)),
        ('keyvals', n(KeyValues))
    ]


class Genesis(Struct):
    type_mapping = [
        ('header', n(Header)),
        ('state', n(RawState))
    ]

class TraceStep(Struct):
    type_mapping = [
        ('pre_state', n(RawState)),
        ('block', n(Block)),
        ('post_state', n(RawState)),
    ]

class Version(Struct):
    type_mapping = [
        ('major', n(U8)),
        ('minor', n(U8)),
        ('patch', n(U8)),
    ]

class PeerInfo(Struct):
    type_mapping = [
        ('name', n(String)),
        ('app_version', n(Version)),
        ('jam_version', n(Version)),
    ]

class Profile(Enum):
    type_mapping = {
        0: ("Empty", n(Null)),
        1: ("Storage", n(Null)),
        2: ("Preimages", n(Null)),
        3: ("ValidatorsManagement", n(Null)),
        4: ("ServiceLife", n(Null)),
        5: ("ServiceLife", n(Null)),
        255: ("Full", n(Null)),
    }

class ReportConfig(Struct):
    type_mapping = [
        ('seed', n(String)),
        ('profile', n(Profile)),
        ('safrole', n(Bool)),
        ('max_work_items', n(U32)),
        ('max_service_keys', n(U32)),
        ('mutation_ratio', n(F64)),
        ('max_mutations', n(U32)),
        ('max_steps',  n(U32)),
    ]

class FuzzState(Struct):
    type_mapping = [
        ('step', n(U32)),
        ('slot', n(TimeSlot)),
    ]

class RootDiff(Struct):
    type_mapping = [
        ('exp', n(OpaqueHash)),
        ('got', n(OpaqueHash))
    ]

class ValueDiff(Struct):
    type_mapping = [
        ('exp', n(ByteSequence)),
        ('got', n(ByteSequence)),
    ]

class KeyValueDiff(Struct):
    type_mapping = [
        ('key', n(TrieKey)),
        ('diff', n(ValueDiff)),
    ]

class KeyValueDiffs(Vec):
    sub_type = n(KeyValueDiff)

class Report(Struct):
    type_mapping = [
        ('target', n(PeerInfo)),
        ('config', n(ReportConfig)),
        ('fuzz_state', n(FuzzState)),
        ('roots', n(RootDiff)),
        ('keyvals', n(KeyValueDiffs)),
    ]

class SetState(Struct):
    type_mapping = [
        ('header', n(Header)),
        ('state', n(KeyValues))
    ]

class Message(Enum):
    type_mapping = {
        0: ("PeerInfo", n(PeerInfo)),
        1: ("Block", n(Block)),
        2: ("SetState", n(SetState)),
        3: ("GetState", n(OpaqueHash)),
        4: ("State", n(KeyValues)),
        5: ("StateRoot", n(OpaqueHash))
    }   

class WireMessage(Struct):
    type_mapping = [
        ('length', n(U32)),
        ('message', n(Message))
    ]

def convert_to_json(filename, subsystem_type, spec_name = None):
    with open(filename, 'rb') as file:
        blob = file.read()
        scale_bytes = ScaleBytes(blob)
        dump = subsystem_type(data=scale_bytes)
        decoded = dump.decode()
        print(json.dumps(decoded, indent=4))


def main():
    spec.set_spec("tiny")

    type_mapping = {
        'Genesis': Genesis,
        'TraceStep': TraceStep,
        'Message': Message,
        'WireMessage': WireMessage,
        'Report': Report,
    }
    
    parser = argparse.ArgumentParser(description='Decode binary files to JSON', 
                                   formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('filename', help='Binary file to decode')
    type_help = "Type to use for decoding:\n"
    type_help += " * Report: fuzzer report (generally `report.bin`)\n"
    type_help += " * Genesis: trace genesis (generally `genesis.bin`)\n"
    type_help += " * TraceStep: trace step (generally `nnnnnnnn.bin`)\n"
    type_help += " * Message: fuzzer protocol message (with no length prefix)\n"
    type_help += " * WireMessage: fuzzer protocol message (with length prefix)\n"
    
    parser.add_argument('type', nargs='?', choices=type_mapping.keys(), help=type_help)
    
    args = parser.parse_args()
    
    if not args.type:
        # Infer type from filename
        filename = os.path.basename(args.filename)
        if filename == 'report.bin':
            inferred_type = 'Report'
        elif filename == 'genesis.bin':
            inferred_type = 'Genesis'
        elif re.match(r'^\d{8}\.bin$', filename):
            inferred_type = 'TraceStep'
        else:
            inferred_type = 'Message'
        print(f"Warning: No type specified, attempting to decode as {inferred_type} based on filename", file=sys.stderr)
        args.type = inferred_type

    decode_type = type_mapping[args.type]   
    convert_to_json(args.filename, decode_type)

if __name__ == '__main__':
    main()
