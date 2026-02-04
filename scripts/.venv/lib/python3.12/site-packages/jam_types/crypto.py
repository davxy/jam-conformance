from .simple import ByteArray

class Ed25519Public(ByteArray):
    element_count = 32

class Ed25519Signature(ByteArray):
    element_count = 64

class BandersnatchPublic(ByteArray):
    element_count = 32

class BandersnatchVrfSignature(ByteArray):
    element_count = 96

class BandersnatchRingVrfSignature(ByteArray):
    element_count = 784

class BandersnatchRingCommitment(ByteArray):
    element_count = 144

class BlsPublic(ByteArray):
    element_count = 144

