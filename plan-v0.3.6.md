# AVS Gateway v0.3.6 Build Plan
# ASR-1 Proof-of-Action Foundation

## Mission

v0.3.6 introduces ASR-1: the first structured proof-of-action receipt foundation for AVS Gateway.

The goal is not to change gateway decision behaviour.
The goal is to standardise the evidence object produced after an agent action is proposed, evaluated, decided, executed or blocked, and recorded.

Core doctrine:

Every agent action gets a receipt.

## Scope

v0.3.6 adds:

1. ASR-1 receipt schema
2. ASR-1 receipt model
3. Receipt builder/converter from existing gateway decisions
4. Agent identity model
5. Tool manifest model
6. Receipt verification helpers
7. Tamper detection tests
8. Example ASR-1 receipts
9. Documentation explaining ASR-1 in plain language

## Non-scope

v0.3.6 does not add payments.
v0.3.6 does not add blockchain.
v0.3.6 does not add remote signing services.
v0.3.6 does not change approval loop behaviour.
v0.3.6 does not change policy decisions.
v0.3.6 does not claim to be a formal standard.

## Proposed Files

### New files

schemas/asr_1_receipt.schema.json
avs_gateway/receipts/__init__.py
avs_gateway/receipts/asr1.py
avs_gateway/identity/__init__.py
avs_gateway/identity/agent_identity.py
avs_gateway/tools/tool_manifest.py
examples/receipts/allow_file_read.asr1.json
examples/receipts/deny_file_delete.asr1.json
examples/receipts/require_approval_api_post.asr1.json
examples/receipts/quarantine_payment.asr1.json
docs/ASR_1_RECEIPT_STANDARD.md
docs/ASR_1_EXAMPLES.md
avs_gateway/tests/unit/test_asr1_receipt.py
avs_gateway/tests/unit/test_agent_identity.py
avs_gateway/tests/unit/test_tool_manifest.py
avs_gateway/tests/integration/test_asr1_gateway_bridge.py

### Modified files

pyproject.toml
README.md
avs_gateway/__init__.py
avs_gateway/core/receipt_generator.py
avs_gateway/cli.py

## ASR-1 Receipt Fields

receipt_version
receipt_id
timestamp_utc
gateway_id
agent
tool
action
decision
risk
policy
trust
approval
execution
evidence
hashes
signature

## Required Tests

1. ASR-1 receipt can be created from an allow decision.
2. ASR-1 receipt can be created from a deny decision.
3. ASR-1 receipt can be created from a require_approval decision.
4. ASR-1 receipt can be created from a quarantine decision.
5. Receipt hash changes when receipt content changes.
6. Receipt verification fails after tampering.
7. Agent identity validates required fields.
8. Tool manifest validates required fields.
9. Existing 496 tests still pass.
10. No v0.4 payment code is introduced.

## Demo Goal

A command should generate or display ASR-1 receipts for simulated actions:

avs asr1-demo

Expected demo output:

- allow file read receipt
- deny file delete receipt
- require approval API post receipt
- quarantine high-risk action receipt
- tamper verification example

## Release Gate

v0.3.6 is lockable only when:

- all previous 496 tests pass
- all new ASR-1 tests pass
- examples validate against schema
- hard gate passes
- no payment/blockchain/settlement logic is present
