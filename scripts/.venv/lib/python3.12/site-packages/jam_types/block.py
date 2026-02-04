from scalecodec import BoundedVec, FixedLengthArray, Struct, Vec

from .spec import epoch_length, validators_count, max_tickets_per_block, spec_metaclass
from .types import Preimage, TicketBody, OpaqueHash, AvailAssurance
from .crypto import BandersnatchPublic, Ed25519Public
from .utils import class_name as n

#
# Header
#

class TicketsMark(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = n(TicketBody)
    element_count = epoch_length
    _spec_attributes = {'element_count': 'epoch_length'}

class EpochMarkValidatorKeys(Struct):
    type_mapping = [
        ('bandersnatch', n(BandersnatchPublic)),
        ('ed25519', n(Ed25519Public))
    ]

class EpochMarkValidatorsKeys(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = n(EpochMarkValidatorKeys)
    element_count = validators_count
    _spec_attributes = {'element_count': 'validators_count'}

class EpochMark(Struct):
    type_mapping = [
        ('entropy', n(OpaqueHash)),
        ('tickets_entropy', n(OpaqueHash)),
        ('validators', n(EpochMarkValidatorsKeys))
    ]

class OffendersMark(Struct):
    type_mapping = [
        # Offenders marker (H_o)
        ('offenders_mark', 'Vec<Ed25519Public>')
    ]

class Header(Struct):
    type_mapping = [
        ("parent", "OpaqueHash"),
        ("parent_state_root", "OpaqueHash"),
        ("extrinsic_hash", "OpaqueHash"),
        ("slot", "TimeSlot"),
        ("epoch_mark", "Option<EpochMark>"),
        ("tickets_mark", "Option<TicketsMark>"),
        ("author_index", "U16"),
        ("entropy_source", "BandersnatchVrfSignature"),
        ("offenders_mark", "Vec<Ed25519Public>"),
        ("seal", "BandersnatchVrfSignature")
    ]

#
# Extrinsic
#
 
class TicketsXt(BoundedVec, metaclass=spec_metaclass(type(BoundedVec))):
    sub_type = "TicketEnvelope"
    max_elements = max_tickets_per_block
    _spec_attributes = {'max_elements': 'max_tickets_per_block'}

class DisputesXt(Struct):
    type_mapping = [
        ("verdicts", "Vec<Verdict>"),
        ("culprits", "Vec<Culprit>"),
        ("faults", "Vec<Fault>")
    ]

class PreimagesXt(Vec):
    sub_type = n(Preimage)

class AssurancesXt(Vec):
    sub_type = n(AvailAssurance)

class GuaranteesXt(Vec):
    sub_type = 'ReportGuarantee'

class Extrinsics(Struct):
    type_mapping = [
        ("tickets", n(TicketsXt)),
        ("preimages", n(PreimagesXt)),
        ("guarantees", n(GuaranteesXt)),
        ("assurances", n(AssurancesXt)),
        ("disputes", n(DisputesXt))
    ]

#
# Block
#

class Block(Struct):
    type_mapping = [
        ("header", n(Header)),
        ("extrinsic", n(Extrinsics))
    ]
