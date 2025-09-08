# JAM Protocol Conformance Testing

The fuzzer can function as a JAM protocol conformance testing tool,
enabling validation of third-party implementations (the "target") against
expected behaviors.

Through targeted testing, the fuzzer exercises the target implementation,
verifying its conformance with the protocol by comparing key elements
(state root, key-value storage, etc.) against locally computed results.

In this case, the testing approach is strictly **black-box**, with no knowledge
of or access to the internal structure of the system under test.

### Workflow

The conformance testing process follows these steps:

1. Select a **run seed** for deterministic and reproducible execution.  
2. Generate a block using the internal authoring engine (or also a precomputed
   trace for a different reference).
3. Optionally mutate the block before processing (e.g. fault injection).
4. Locally import the block.  
5. Forward the block to the target implementation endpoint for processing.  
6. Retrieve the **posterior state root** from the target and compare it with the
   locally computed one: If the roots match, move on to the next iteration (step 2).  
7. Attempt to read the target's full **key/value storage**.
8. Terminate the execution and produce an execution **report** containing:  
   - **Seed**: The used seed value for deterministic reproduction.  
   - **Inputs and Results**: Prior state, block, and the locally computed
     posterior state.
   - **Target Comparison**: If the target's posterior state is available,
     a _diff_ relative to the expected posterior state.  

The resulting report can be used to construct a precise, specialized test
vector designed to immediately reproduce the discrepancy observed in the target
implementation.

### No Reference Implementation

As there will never be a reference implementation, and the Graypaper is the only
authoritative specification, treating the local fuzzer engine as a reference is
thus inaccurate.

A mismatch between the fuzzer expectation and the target does not automatically
imply an issue with the target. In case of discrepancy, the resulting test
vector should be reviewed, and the expected behavior verified against the
Graypaper to resolve the inconsistency.

### Communication Protocol

The fuzzer communicates with target implementations using a synchronous
**request-response** protocol over Unix domain sockets.

#### Protocol Messages

Schema file: [fuzz-v1](./fuzz-v1.asn)

**Note**: The `Header` included in the `SetState` message may be eventually
used - via its hash - to reference the associated state. It is conceptually
similar to the genesis header: like the genesis header, its contents do not
fully determine the state. In other words, the state must be accepted and
stored exactly as provided, regardless of the header's content.

#### Messages Codec

All messages are encoded according to the **JAM codec** format. Prior to
transmission, each encoded message is prefixed with its length, represented as a
32-bit little-endian integer.

##### Message Encoding Examples

**PeerInfo**

```json
{
  "peer_info" {
    "name": "fuzzer",
    "version": {
      "major": 0,
      "minor": 1,
      "patch": 23
    }
    "protocol_version": {
      "major": 0,
      "minor": 6,
      "patch": 6
    }
  }
}
```

Encoded:
```
0x0e000000 0x000666757a7a6572000117000606
^ length   ^ encoded-message
```

**StateRoot**

```json
{
  "state_root": "0x4559342d3a32a8cbc3c46399a80753abff8bf785aa9d6f623e0de045ba6701fe"
}
```

Encoded:
```
0x21000000 0x054559342d3a32a8cbc3c46399a80753abff8bf785aa9d6f623e0de045ba6701fe
^ length   ^ encoded-message
```

#### Connection Setup

1. **Target Setup**: The target implementation binds to and listens on a named
   Unix socket (e.g., `/tmp/jam_target.sock`).
2. **Fuzzer Connection**: The fuzzer connects to the target's socket to
   establish the communication channel.
3. **Handshake**: The two peers exchange `PeerInfo` messages to identify
   themselves and negotiate protocol versions. The target waits to receive the
   fuzzer's `PeerInfo` message first.

#### Message Types and Expected Responses

| Request | Response | Purpose |
|----------------|-------------------|---------|
| `PeerInfo` | `PeerInfo` | Handshake and versioning exchange |
| `SetState` | `StateRoot` | Initialize or reset target state |
| `ImportBlock` | `StateRoot` | Process block and return resulting state root |
| `GetState` | `State` | Retrieve posterior state associated to given header hash |
| `RefineBundle` | `WorkReport` | Compute work report given work package bundle |
| `GetExports` | `Segments` | Return Exported segments for Work Package Hash or Exported Segment Root |

#### Message Flow

The protocol adheres to a strict request–response model with the following rules:

- **Request initiation:** Only the fuzzer sends requests; the target never
  initiates communication.
- **Sequential exchange:** The target must reply to each request before the next
  one is sent.
- **Response requirements:** Every response must match the expected message type
  for the corresponding request.
 **Import failures:** If a block import fails, the target must return a zero
  hash (i.e. a 32 bytes octet string of all zeroes) and then wait for the next
  block from the fuzzer as usual.
- **State verification:** After each block import, state roots are compared to
  detect inconsistencies.
- **Full state retrieval:** The `GetState` request is issued only when a state
  root mismatch is detected.
- **Refinement:** If work package bundle refinement is supported by the target (via `feature-bundle-refinement`), the fuzzer may send a `RefineBundle` and the fuzzer target must send a `WorkReport` in response.  Only refine should be invoked, however; the core `core-index`, authorization gas used `auth-gas-used` and authorization trace `auth-trace` is provided in the `RefineBundle` for inclusion in the `WorkReport` to represent a prior authorization.  The `service` and `code-hash` for each work item may be found in the previously transmitted states referenced by the Work package `context` by `anchor` or `lookup-anchor` (for historical lookup).  For purposes of bounding the number of states, only the last 600 states `SetState` should be considered.  See **Refinement Failures and Dispute Reporting** below for details.
- **Error handling:** Receiving an unexpected or malformed message results in
  immediate session termination.
- **Timeouts:** The fuzzer may impose time limits on the target’s responses.
- **Session termination:** The fuzzing session ends when the fuzzer closes the
  connection; no explicit termination message is exchanged.

**Typical Session Flow:**

```
              Fuzzer                    Target
                 |                         |
             +---+--- HANDSHAKE -----------+---+
             |   |      PeerInfo           |   |
             |   | ----------------------> |   |
             |   |      PeerInfo           |   |
             |   | <---------------------- |   |
             +---+-------------------------+---+
                 |                         |
             +---+--- INITIALIZATION ------+---+
             |   |      SetState           |   |
             |   | ----------------------> |   | Initialize state
             |   |      StateRoot          |   |
  Check root |   | <---------------------- |   | Return head state root
             +---+-------------------------+---+
                 |                         |
             +---+--- BLOCK PROCESSING ----+---+
             |   |      ImportBlock        |   |
             |   | ----------------------> |   | Process block #1
             |   |      StateRoot          |   |
  Check root |   | <---------------------- |   | Return head state root
                 +- REFINE (if supported) -+   |
             |   |       RefineBundle      |   |
             |   | ----------------------> |   | Process bundle 
             |   |      WorkReport         |   |
             |   | <---------------------- |   | Return work report
             |   +- EXPORTS (if supported) -+  |
             |   |       GetExports        |   |
             |   | ----------------------> |   | Request exports by work package hash or segments root 
             |   |        Segments         |   |
             |   | <---------------------- |   | Return exported segments
             |   |          ...            |   |            
             |   |                         |   |
             |   |      ImportBlock        |   |
             |   | ----------------------> |   | Process block #n
             |   |      StateRoot          |   |
             |   | <---------------------- |   | Return head state root
             |   |          ...            |   |
             +---+-------------------------+---+
                 |                         |
             +---+--- ON ROOT MISMATCH ----+---+
             |   |      GetState           |   |
             |   | ----------------------> |   | Request full state
             |   |       State             |   |
  Gen Report |   | <---------------------- |   | Return full state
             +---+-------------------------+---+
                 |                         |
```

## Refinement Failures and Dispute Reporting

If a work package bundle refinement fails, the target must return a work report regardless, and then wait for another block or refine bundle from the target as usual.  If the target supports the retrieval of exported segments (via `feature-exports`), the fuzzer may send a `GetExports` request with either the work package hash or the exported segment root and the target must send `Exports` in response.  The `GetExports` request is issued only when a work report mismatch is detected, and will reference only the most recently refined work package bundle.

Mismatches between fuzzer and target are reported by hashing the `WorkReport`.  For resolving disputes, the fuzzer may generate a report showing differences in `WorkExecResult`, `ExportsRoot`, `ErasureRoot` and other attributes in the work report: 

- For differences in `WorkExecResult`**, indicate mismatched outputs between success `ok` (raw output bytes) or failure categorization (`out-of-gas`, `panic`, `bad-exports`, `bad-code`, `code-oversize`) 
- For differences in `ExportsRoot`, indicate mismatched exports obtained by the fuzzer from `GetExports` message
- For differences in `ErasureRoot`, indicate that exports align but roots differ  

Fuzzers and fuzzer targets may have verbose logging to show erasure coding derivations step by step. 

Because segments are **4104 bytes** and there may be as many as 3,072 per report, it may be impractical to share these reports.  It is more practical for fuzzer binaries and targets to be shared along with reports indicating which seed/payload resulted in a discrepancy instead.
