# JAM Protocol Conformance Testing

The fuzzer can function as a JAM protocol conformance testing tool,
enabling validation of third-party implementations (the "target") against
expected behaviors.

Through targeted testing, the fuzzer exercises the target implementation,
verifying its conformance with the protocol by comparing key elements
(state root, key-value storage, etc.) against locally computed results.

In this case, the testing approach is strictly **black-box**, with no knowledge
of or access to the internal structure of the system under test.

## Workflow

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

## No Reference Implementation

As there will never be a reference implementation, and the Graypaper is the only
authoritative specification, treating the local fuzzer engine as a reference is
thus inaccurate.

A mismatch between the fuzzer expectation and the target does not automatically
imply an issue with the target. In case of discrepancy, the resulting test
vector should be reviewed, and the expected behavior verified against the
Graypaper to resolve the inconsistency.

## Communication Protocol

The fuzzer communicates with target implementations using a synchronous
**request-response** protocol over Unix domain sockets.

### Protocol Messages

Schema file: [fuzz-v1](./fuzz-v1.asn)

**Note**: The `Header` included in the `SetState` message may be eventually
used - via its hash - to reference the associated state. It is conceptually
similar to the genesis header: like the genesis header, its contents do not
fully determine the state. In other words, the state must be accepted and
stored exactly as provided, regardless of the header's content.

### Messages Codec

All messages are encoded according to the **JAM codec** format. Prior to
transmission, each encoded message is prefixed with its length, represented as a
32-bit little-endian integer.

##### Message Encoding Examples

**PeerInfo**

# TODO FIXME
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

1. **Target Setup**: The target implementation must bind to a named
  `SOCK_STREAM` Unix domain socket and listen for connections
   (e.g., `/tmp/jam_target.sock`).
2. **Fuzzer Connection**: The fuzzer connects to the target's socket to
   establish the communication channel.
3. **Handshake**: Both peers exchange `PeerInfo` messages to identify
   themselves and negotiate protocol versions and supported features.
   The target waits to receive the fuzzer's `PeerInfo` message before
   sending its own.

### Message Types and Expected Responses

| Request        | Response     | Description |
|----------------|--------------|-------------|
| `PeerInfo`     | `PeerInfo`   | Handshake and versioning exchange |
| `SetState`     | `StateRoot`  | Initialize or reset target state |
| `ImportBlock`  | `StateRoot`  | Import block and return resulting state root |
| `GetState`     | `State`      | Retrieve posterior state associated to given header hash |

The only exception is the `Error` message, which the target may return for
certain requests when a protocol-defined error condition occurs.
Any error condition not specified by the JAM protocol (e.g., out-of-consensus
internal errors) **must not** be signaled with an `Error` message.

If such an out-of-protocol error requires terminating the session, either the
fuzzer or the target should simply close the connection without sending an
`Error` message, as outlined in the **General Rules** section.

An `Error` message is only meaningful when the session continues, since it
triggers a specific reaction from the fuzzer.

| Request        | Response | Description |
|----------------|----------|-------------|
| `ImportBlock`  | `Error`  | Import block failure |

### General Rules

The protocol adheres to a strict **request–response** model with the following rules:

- **Request initiation**. Only the fuzzer sends requests; the target never
  initiates communication.
- **Sequential exchange**. The target must reply to each request before the next
  one is sent.
- **Response requirements**. Every response must match the expected message type
  for the corresponding request (or an Error message specified by the protocol).
- **Unexpected errors**. Receiving an unexpected or malformed message results in
  immediate session termination.
- **Timeouts**. The fuzzer may impose time limits on the target's responses.
- **Session termination**. The fuzzing session ends when the fuzzer closes the
  connection; no explicit termination message is exchanged.

### Block Importing

- **Import success**. On success the posterior state root should be returned. 
- **Import failure**. On failure, the target must return a zero hash
  in place of the state root (i.e. a 32 bytes octet string of all zeroes)
  and then wait for the next block from the fuzzer.
- **State verification:** After each block import, state roots are compared by
  the fuzzer to detect inconsistencies.
- **Full state retrieval:** When a state root mismatch is detected the fuzzer
  attempts to fetch the whole state from the target to produce a comprehensive
  fuzz report.

### Protocol Session

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
             |   |   StateRoot (or Error)  |   |
  Check root |   | <---------------------- |   | Return head state root
             +---+-------------------------+---+
                 |                         |
             +---+--- BLOCK PROCESSING ----+---+
             |   |      ImportBlock        |   |
             |   | ----------------------> |   | Process block #1
             |   |   StateRoot (or Error)  |   |
  Check root |   | <---------------------- |   | Return head state root
             |   |          ...            |   |            
             |   |      ImportBlock        |   |
             |   | ----------------------> |   | Process block #n
             |   |   StateRoot (or Error)  |   |
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

