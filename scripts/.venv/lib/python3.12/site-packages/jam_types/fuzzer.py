#==========================================
#============ Fuzzer Protocol =============
#==========================================

from jam_types import TimeSlot, Struct, Header, Block, OpaqueHash, ByteArray, ByteSequence, Vec, String, Enum, Null, Bool, U8, U32, U64, F64
from jam_types import n
 
# Feature flags for fuzzer capabilities
FEATURE_ANCESTRY = 1 << 0
FEATURE_FORKS = 1 << 1
FEATURES_MASK = FEATURE_ANCESTRY | FEATURE_FORKS

class TrieKey(ByteArray):
    """A 31-byte trie key."""
    element_count = 31

class KeyValue(Struct):
    """Key-value pair structure."""
    type_mapping = [
        ('key', n(TrieKey)),
        ('value', n(ByteSequence))
    ]

class KeyValues(Vec):
    """Vector of key-value pairs."""
    sub_type = n(KeyValue)

class RawState(Struct):
    """Raw blockchain state with root hash and key-value pairs."""
    type_mapping = [
        ('state_root', n(OpaqueHash)),
        ('keyvals', n(KeyValues))
    ]

class Genesis(Struct):
    """Genesis block structure."""
    type_mapping = [
        ('header', n(Header)),
        ('state', n(RawState))
    ]

class TraceStep(Struct):
    """Single step in a fuzzer trace."""
    type_mapping = [
        ('pre_state', n(RawState)),
        ('block', n(Block)),
        ('post_state', n(RawState)),
    ]


class PeerVersion(Struct):
    type_mapping = [
        ('major', n(U8)),
        ('minor', n(U8)),
        ('patch', n(U8)),
    ]

class PeerInfo(Struct):
    type_mapping = [
        ('fuzz_version', n(U8)),
        ('fuzz_features', n(U32)),
        ('jam_version', n(PeerVersion)),
        ('app_version', n(PeerVersion)),
        ('app_name', n(String)),
    ]

class Profile(Enum):
    type_mapping = {
        0: ("empty", n(Null)),
        1: ("storage", n(Null)),
        2: ("preimages", n(Null)),
        3: ("validators_management", n(Null)),
        4: ("storage_and_preimages", n(Null)),
        254: ("fuzzy", n(Null)),
        255: ("full", n(Null)),
    }

class FuzzyProfile(Enum):
    type_mapping = {
        0: ("empty", n(Null)),
        1: ("memcheck", n(Null)),
        2: ("storage", n(Null)),
        3: ("preimages", n(Null)),
        4: ("management", n(Null)),
        5: ("services", n(Null)),
        10: ("misc", n(Null)),
        254: ("rand", n(Null)),
        255: ("full", n(Null)),
    }

class ReportConfig(Struct):
    type_mapping = [
        ('seed', n(String)),
        ('max_steps',  n(U32)),
        ('safrole', n(Bool)),
        ('profile', n(Profile)),
        ('fuzzy_profile', n(FuzzyProfile)),
        ('max_work_items', n(U32)),
        ('mutation_ratio', n(F64)),
        ('max_mutations', n(U32)),
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

class StateDiff(Struct):
    type_mapping = [
        ('roots', n(RootDiff)),
        ('keyvals', n(KeyValueDiffs)),
    ]

class ImportDiff(Struct):
    type_mapping = [
        ('exp', n(String)),
        ('got', n(String)),
    ]

class FuzzerError(Enum):
    type_mapping = {
        0: ("state_diff", n(StateDiff)),
        1: ("import_result_diff", n(ImportDiff)),
        2: ("communication", n(String)),
        3: ("local_fatal", n(String)),
    }

class ReportStatistics(Struct):
    type_mapping = [
	    ('steps', n(U64)),
    	('imported', n(U64)),
    	('import_max_step', n(U64)),
    	('import_min', n(F64)),
    	('import_max', n(F64)),
    	('import_mean', n(F64)),
    	('import_p50', n(F64)),
    	('import_p75', n(F64)),
    	('import_p90', n(F64)),
    	('import_p99', n(F64)),
    	('import_std_dev', n(F64))
    ]

class TargetReport(Struct):
    type_mapping = [
        ('info', n(PeerInfo)),
        ('stats', n(ReportStatistics))
    ]

class FuzzerReport(Struct):
    type_mapping = [
        ('config', n(ReportConfig)),
        ('stats', n(ReportStatistics)),
        ('target', "Option<TargetReport>"),
        ('error', "Option<FuzzerError>"),
    ]

class AncestryItem(Struct):
    type_mapping = [
        ('slot', n(TimeSlot)),
        ('header_hash', n(OpaqueHash))
    ]
    
class Ancestry(Vec):
    sub_type = n(AncestryItem)  

class Initialize(Struct):
    type_mapping = [
        ('header', n(Header)),
        ('state', n(KeyValues)),
        ('ancestry', n(Ancestry))
    ]

class FuzzerMessage(Enum):
    type_mapping = {
        0: ("peer_info", n(PeerInfo)),
        1: ("initialize", n(Initialize)),
        2: ("state_root", n(OpaqueHash)),
        3: ("import_block", n(Block)),
        4: ("get_state", n(OpaqueHash)),
        5: ("state", n(KeyValues)),
        255: ("error", n(String))
    }   

class FuzzerWireMessage(Struct):
    type_mapping = [
        ('length', n(U32)),
        ('message', n(FuzzerMessage))
    ]
