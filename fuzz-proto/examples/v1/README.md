# Pre-computed fuzzer protocol v1 session messages

# WARNING

We simulate a buggy target.

**The state root sent back by the target at step 29 is intentionally wrong**

This is to solicit the fuzzer to send a `GetState` request, and thus include this message
kind in the examples as well.

As per fuzzer protocol -- the fuzzer sends a GetState message only when
the target reports an unexpected root, as this usually indicates a state
inconsistency.

The target then returns its state -- which is expected not to match the correcly
computed state.

