# JAM Conformance Testing Protocol

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

## Protocol

The fuzzer communicates with target implementations using a synchronous
**request-response** protocol over Unix domain sockets.

### Protocol Messages

Schema file: [fuzz-v1](./fuzz-v1.asn)

**Note**: The `Header` included in the `Initialize` message may be eventually
used - via its hash - to reference the associated state. It is conceptually
similar to the genesis header: like the genesis header, its contents do not
fully determine the state. In other words, the state must be accepted and
stored exactly as provided, regardless of the header's content.

### Messages Codec

All messages are encoded according to the **JAM codec** format. Prior to
transmission, each encoded message is prefixed with its length, represented as a
32-bit little-endian integer.

#### Encoding Examples

Here are a couple of encoding examples.  
For a complete set of examples from an actual session, see the [examples](./examples) directory.

**PeerInfo**

```json
{
  "peer_info": {
      "fuzz_version": 1,
      "fuzz_features": 2,
      "jam_version": {
        "major": 0,
        "minor": 7,
        "patch": 0
      },
      "app_version": {
        "major": 0,
        "minor": 1,
        "patch": 25
      },
      "app_name": "fuzzer"
    }
  }
}
```

Encoded:

```
0x0001020000000007000001190666757a7a6572
```

- `00`: message variant discriminant (`peer_info`)
- `01`: fuzzer version
- `02000000`: fuzzer features
- `000700`: jam version
- `000119`: application version
- `06`: application name length
- `66757a7a6572`: application name

**StateRoot**

```json
{
  "state_root": "0x4559342d3a32a8cbc3c46399a80753abff8bf785aa9d6f623e0de045ba6701fe"
}
```

Encoded:
```
0x024559342d3a32a8cbc3c46399a80753abff8bf785aa9d6f623e0de045ba6701fe
```

- `02`: message variant discriminant (`state_root`)
- `45..fe`: state root

**Error**

```json
{
    "error": "Chain error: block execution failure: preimages error: preimage not required"
}
```

Encoded:
```
0xff4c436861696e206572726f723a20626c6f636b20657865637574696f6e206661696c7572653a20707265696d61676573206572726f723a20707265696d616765206e6f74207265717569726564
```

- `ff`: message variant discriminant (`error`)
- `4c`: message length
- `43..64`: message

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
| `Initialize`   | `StateRoot`  | Initialize or reset target state |
| `ImportBlock`  | `StateRoot`  | Import block and return resulting state root |
| `GetState`     | `State`      | Retrieve posterior state associated to given header hash |

The only exception is the `Error` message, which the target may return for
certain requests when a protocol-defined error condition occurs.
Any error condition not specified by the JAM protocol (e.g., out-of-consensus
internal errors) **must not** be signaled with an `Error` message.

The `Error` message may convey some extra information for debugging purposes.

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
- **Import failure**. On failure, the target must return an `Error` message
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
             |   |       Initialize        |   |
             |   | ----------------------> |   | Initialize target
             |   |        StateRoot        |   |
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

## Features

Supported features are negotiated during the initial handshake via the `PeerInfo` message.

Session features are determined by the intersection (bitwise-and) of the features
listed in the `PeerInfo` message. If a party considers a specific feature mandatory
but finds it missing, it may choose to immediately terminate the session.

**Note:** During official M1 conformance testing, support for certain features is **mandatory**.  
Mandatory features are marked with the `[M1]` tag.

### Ancestry [M1]

When `feature-ancestry` is enabled, the fuzzer includes in the `Initialize`
message the list of ancestors for the block contained in the first step
(i.e., the first block sent via `ImportBlock`).

This feature is required to support a **GP-mandated check**:  
the lookup anchor of each report in the guarantees extrinsic ($G_A$)  
must be included within the last $L$ imported headers in the chain  
([GP reference](https://graypaper.fluffylabs.dev/#/1c979cb/150203150203?v=0.7.1)).

According to the GP specification, $L = 14400$.
Assuming 6-second slots with no skipped slots, this corresponds to **24 hours**.  

However, when fuzzing with _tiny_ specs, we prefer a much smaller **L**.  
Using the same full/tiny ratio as the one used for preimage expunge period  
($19,200 / 32 = 600$), we scale $L$ accordingly: $L = 14,400 / 600 = 24$.

In short, for the `tiny` spec, the maximum ancestry length **A** is set to **24**.

**When this feature is disabled, the check described in the GP reference should
also be skipped.**

### Forking [M1]

When `feature-forks` is enabled, the fuzzer may generate simple forks.  

#### Typical Workflow

1. The fuzzer produces a new block and prepares several mutations.
2. Each mutation is sent to the target using one `ImportBlock` message per mutation.
3. Some mutations may be invalid and therefore ignored.  
   Valid mutations that get imported result in a fork.

Importantly, the fuzzer does **not** require full arbitrary forking support.  
The chain is always extended from the **original block** — i.e.
mutations are never used as parents for subsequent blocks.

#### Example Session

1. Let $i = 0$  
2. Increment $i$ and construct block $B_i$ with parent $B_{i-1}$  
3. Mutate $B_i$ into several variants: $B_{i1}$, $B_{i2}$, $B_{i3}$  
4. Import these variants in order: $B_{i1}$, $B_{i2}$, $B_{i3}$, and finally the original $B_i$  
5. Repeat from step 2  
