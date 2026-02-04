from scalecodec import (
    U8,
    U32,
    BoundedVec,
    Enum,
    FixedLengthArray,
    Struct,
    Vec,
)

from .spec import (
    avail_bitfield_bytes,
    core_count,
    epoch_length,
    validators_count,
    validators_super_majority,
    spec_metaclass,
)
from .simple import *
from .simple import OpaqueHash, TimeSlot, ServiceId, ByteArray, Gas, n
from .work import WorkReport

#
# Disputes
# 

class Disputes(Struct):
    type_mapping = [
        # Good verdicts sequence
        ('good', 'Vec<WorkReportHash>'),
        # Bad verdicts sequence
        ('bad', 'Vec<WorkReportHash>'),
        # Wonky verdicts sequence
        ('wonky', 'Vec<WorkReportHash>'),
        # Offenders sequence
        ('offenders', 'Vec<WorkReportHash>')
    ]

##
# Validator Data
##
 
class ValidatorMetadata(ByteArray):
    element_count = 128

class ValidatorData(Struct):
    type_mapping = [
        ("bandersnatch", 'BandersnatchPublic'),
        ("ed25519", 'Ed25519Public'),
        ("bls", 'BlsPublic'),
        ("metadata", 'ValidatorMetadata')
    ]

class ValidatorsData(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = n(ValidatorData)
    element_count = validators_count
    _spec_attributes = {'element_count': 'validators_count'}

#
# Availability Assigments
# 

class AvailabilityAssignment(Struct):
    type_mapping = [
        ('report', n(WorkReport)),
        ('timeout', n(TimeSlot))
    ]

class AvailabilityAssignments(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = 'Option<AvailabilityAssignment>'
    element_count = core_count
    _spec_attributes = {'element_count': 'core_count'}

#
# Statistics
#

class ValidatorActivityRecord(Struct):
    type_mapping = [
        ("blocks", n(U32)),
        ("tickets", n(U32)),
        ("pre_images", n(U32)),
        ("pre_images_size", n(U32)),
        ("guarantees", n(U32)),
        ("assurances", n(U32)),
    ]

class ValidatorsStatistics(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = n(ValidatorActivityRecord)
    element_count = validators_count
    _spec_attributes = {'element_count': 'validators_count'}

class CoreActivityRecord(Struct):
    type_mapping = [
    	# Amount of bytes which are placed into either Audits or Segments DA.
    	# This includes the work-bundle (including all extrinsics and imports) as well as all
    	# (exported) segments.
    	('da_load', 'Compact<U32>'),
    	# Number of validators which formed super-majority for assurance.
    	('popularity', 'Compact<U16>'),
    	# Number of segments imported from DA made by core for reported work.
    	('imports', 'Compact<U16>'),
    	# Total number of extrinsics used by core for reported work.
    	('extrinsic_count', 'Compact<U16>'),
    	# Total size of extrinsics used by core for reported work.
    	('extrinsic_size', 'Compact<U32>'),
    	# Number of segments exported into DA made by core for reported work.
    	('exports', 'Compact<U16>'),
    	# The work-bundle size. This is the size of data being placed into Audits DA by the core.
    	('bundle_size', 'Compact<U32>'),
        # Total gas consumed by core for reported work. Includes all refinement and authorizations.
    	('gas_used', 'Compact<Gas>'),
	]
    
class CoresStatistics(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = n(CoreActivityRecord)
    element_count = core_count
    _spec_attributes = {'element_count': 'core_count'}

class ServiceActivityRecord(Struct):
    type_mapping = [
    	# Number of preimages provided to this service.
    	('provided_count', 'Compact<u16>'),
    	# Total size of preimages provided to this service.
    	('provided_size', 'Compact<u32>'),
    	# Number of work-items refined by service for reported work.
    	('refinement_count', 'Compact<u32>'),
    	# Amount of gas used for refinement by service for reported work.
    	('refinement_gas_used', 'Compact<Gas>'),
    	# Number of segments imported from the DL by service for reported work.
    	('imports', 'Compact<u32>'),
    	# Total number of extrinsics used by service for reported work.
    	('extrinsic_count', 'Compact<u32>'),
    	# Total size of extrinsics used by service for reported work.
    	('extrinsic_size', 'Compact<u32>'),
    	# Number of segments exported into the DL by service for reported work.
    	('exports', 'Compact<u32>'),
    	# Number of work-items accumulated by service.
    	('accumulate_count', 'Compact<u32>'),
    	# Amount of gas used for accumulation by service.
    	('accumulate_gas_used', 'Compact<Gas>')
    ]

class ServicesStatisticsMapEntry(Struct):
    type_mapping = [
        ("id", n(ServiceId)),
        ("record", n(ServiceActivityRecord))
    ]

class ServicesStatistics(Vec):
    sub_type = n(ServicesStatisticsMapEntry)

class Statistics(Struct):
    type_mapping = [
        ("vals_curr", n(ValidatorsStatistics)),
        ("vals_last", n(ValidatorsStatistics)),
    	("cores", n(CoresStatistics)),
    	("services", n(ServicesStatistics))
    ]

#
# Misc
# 

class AvailabilityBitfield(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = n(U8)
    element_count = avail_bitfield_bytes
    _spec_attributes = {'element_count': 'avail_bitfield_bytes'}

class AvailAssurance(Struct):
    type_mapping = [
        ("anchor", "OpaqueHash"),
        ("bitfield", n(AvailabilityBitfield)),
        ("validator_index", "U16"),
        ("signature", "Ed25519Signature")
    ]

class Preimage(Struct):
    type_mapping = [
        ("requester", "ServiceId"),
        ("blob", "ByteSequence")
    ]

class Culprit(Struct):
    type_mapping = [
        ("target", "WorkReportHash"),
        ("key", "Ed25519Public"),
        ("signature", "Ed25519Signature")
    ]

class Fault(Struct):
    type_mapping = [
        ("target", "WorkReportHash"),
        ("vote", "Bool"),
        ("key", "Ed25519Public"),
        ("signature", "Ed25519Signature")
    ]

class Judgement(Struct):
    type_mapping = [
        ("vote", "Bool"),
        ("index", "ValidatorIndex"),
        ("signature", "Ed25519Signature")
    ]

class Judgements(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = 'Judgement'
    element_count = validators_super_majority
    _spec_attributes = {'element_count': 'validators_super_majority'}
    
class Verdict(Struct):
    type_mapping = [
        ("target", "WorkReportHash"),
        ("age", "EpochIndex"),
        ("votes", "Judgements")
    ]

#
# Tickets
#
 
class TicketId(OpaqueHash):
    pass

class TicketAttempt(U8):
    pass

class TicketBody(Struct):
    type_mapping = [
        ('id', 'TicketId'),
        ('attempt', 'TicketAttempt')
    ]

class TicketEnvelope(Struct):
    type_mapping = [
        ("attempt", "TicketAttempt"),
        ("signature", "BandersnatchRingVrfSignature")
    ]

class TicketsBodies(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = n(TicketBody)
    element_count = epoch_length
    _spec_attributes = {'element_count': 'epoch_length'}

class TicketsAccumulator(BoundedVec, metaclass=spec_metaclass(type(BoundedVec))):
    sub_type = n(TicketBody)
    max_elements = epoch_length
    _spec_attributes = {'max_elements': 'epoch_length'}

class EpochKeys(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = 'BandersnatchPublic'
    element_count = epoch_length
    _spec_attributes = {'element_count': 'epoch_length'}

class TicketsOrKeys(Enum):
    type_mapping = {
        0: ('tickets', n(TicketsBodies)),
        1: ('keys', n(EpochKeys))
    }

#
# Guarantees
#

class GuaranteeSignature(Struct):
    type_mapping = [
        ('validator_index', 'ValidatorIndex'),
        ('signature', 'Ed25519Signature')
    ]

class GuaranteeSignatures(Vec):
    sub_type = 'GuaranteeSignature'

class ReportGuarantee(Struct):
    type_mapping = [
        ('report', 'WorkReport'),
        ('slot', 'TimeSlot'),
        ('signatures', 'GuaranteeSignatures')
    ]

#
# Services
#
 
class ServiceInfo(Struct):
    type_mapping = [
        ('version', n(U8)),
        ('code_hash', 'OpaqueHash'),
        ('balance', 'U64'),
        ('min_item_gas', 'Gas'),
        ('min_memo_gas', 'Gas'),
        ('bytes', 'U64'),
        ('deposit_offset', 'U64'),
        ('items', n(U32)),
        ('creation_slot', n(TimeSlot)),
        ('last_accumulation_slot', n(TimeSlot)),
        ('parent_service', n(ServiceId))
    ]

class AlwaysAccumulateMapEntry(Struct):
    type_mapping = [
        ('id', n(ServiceId)),
        ('gas', n(Gas)),
    ]

class CoreAssignmentPrivileges(FixedLengthArray, metaclass=spec_metaclass(type(FixedLengthArray))):
    sub_type = n(ServiceId)
    element_count = core_count
    _spec_attributes = {'element_count': 'core_count'}

class Privileges(Struct):
    type_mapping = [
        ('bless', n(ServiceId)),
        ('assign', n(CoreAssignmentPrivileges)),
        ('designate', n(ServiceId)),
        ('register', n(ServiceId)),
        ('always_acc', "Vec<AlwaysAccumulateMapEntry>"),
    ]

class AccumulationOutputItem(Struct):
    type_mapping = [
        ('service_id', n(ServiceId)),
        ('output_hash', n(OpaqueHash))
    ]

class AccumulationOutput(Vec):
    sub_type = n(AccumulationOutputItem)
