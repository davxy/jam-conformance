# Precomputed Session Messages

We provide the following predefined session message sets:

- **`forks`** - includes mutants, invalid blocks, and forks
- **`no_forks`** - contains no mutants, invalid blocks, or forks
- **`faulty`** - terminates with a target root mismatch (see warning below)

These session messages can be used with the `minifuzz` application to exercise your target
before submission. **WARNING:** pay special attention when using the `faulty` session.

## WARNING: Faulty Session

The `faulty` session set intentionally simulates a buggy target by ending with
an incorrect state root.

Specifically:

**At step 29, the state root returned by the target is deliberately wrong.**

This is meant to trigger the fuzzer to send a `GetState` request, so that this
message type is covered by the examples.

According to the fuzzer protocol, a `GetState` message is sent only when
the target reports an unexpected state root, which usually indicates a state
inconsistency.

In this scenario, the target responds with its current state, which is
**expected not to match** a correctly computed state.

