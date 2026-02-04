from .simple import Struct, OpaqueHash, BoundedVec, n
from .spec import recent_blocks_max_size

class Mmr(Struct):
    type_mapping = [
        ('peaks', 'Vec<Option<OpaqueHash>>')
    ]

class ReportedWorkPackage(Struct):
    type_mapping = [
        ('hash', 'OpaqueHash'),
        # Exported segments root
        ('exports_root', 'OpaqueHash')
    ]

class BlockInfo(Struct):
    type_mapping = [
        ('header_hash', n(OpaqueHash)),
        ('beefy_root', n(OpaqueHash)),
        ('state_root', n(OpaqueHash)),
        ('reported', 'Vec<ReportedWorkPackage>')
    ]

class RecentBlocksInfo(BoundedVec):
    sub_type = n(BlockInfo)
    max_elements = recent_blocks_max_size

class RecentBlocks(Struct):
    type_mapping = [
        ('history', n(RecentBlocksInfo)),
        ('mmr', n(Mmr))
    ]
