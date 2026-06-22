## Demo Video Script — AVS Gateway v0.3.4

**Duration:** 35 seconds  
**Format:** Terminal recording (asciinema or terminal GIF)  
**Voice:** Calm, authoritative. No hype.  
**Background:** Subtle ambient electronic, or silence. No music during narration.

---

### [00:00-00:05] Open

**Visual:** Black terminal. `avs version` typed and executed.

```
$ avs version
AVS Gateway v0.3.4
Runtime Permission Layer for AI Agents
```

**Narrator:** *"AVS Gateway. Every agent action gets a receipt."*

---

### [00:05-00:18] The Demo

**Visual:** `avs demo` command executes. Terminal shows 3 tool calls being intercepted and evaluated in sequence.

```
$ avs demo

[CALL] read_file("/home/user/report.pdf")
[DECISION] ALLOW
[RECEIPT] sig: Ed25519:9f2a...b4e1, hash: SHA-256:a7c3...d2f8

[CALL] delete_file("/etc/passwd")
[DECISION] DENY — violates rule: protected_path
[RECEIPT] sig: Ed25519:3c8b...e7d2, hash: SHA-256:f1e9...a4b3

[CALL] send_email(to="ceo@company.com", body="You're fired")
[DECISION] REQUIRE_APPROVAL — risk_score: 0.87
[RECEIPT] sig: Ed25519:7d4f...c1a9, hash: SHA-256:8e2b...f5c7
```

**Narrator:** *"Three tool calls. Three decisions. Every one intercepted, evaluated, and logged with a cryptographic receipt. The delete was blocked. The email was flagged for human approval."*

---

### [00:18-00:28] The Code

**Visual:** Terminal clears. Simple Python file shown with `@governed_tool` decorator.

```python
from avs_gateway import governed_tool

@governed_tool(policy_rules="rules.yaml")
def delete_database(name: str):
    ...

# Agent calls it. AVS decides. Receipt proves what happened.
```

**Narrator:** *"One decorator. Zero rewrites. Works with any Python function, any framework."*

---

### [00:28-00:35] Close

**Visual:** Terminal returns to the AVS logo/ascii art and tagline.

```
$ avs version
AVS Gateway v0.3.4

Every agent action gets a receipt.
https://github.com/avs-gateway/avs-gateway
```

**Narrator:** *"AVS Gateway. Apache 2.0. Four hundred seventy tests. Zero failures."*

**Text on screen:**
```
pip install avs-gateway
```

---

## Technical Notes for Recording

- Use `asciinema rec` or `terminalizer` for clean terminal capture
- Terminal theme: dark background, green/white text for normal output, red for DENY, yellow for REQUIRE_APPROVAL
- Font: monospace, at least 16px for readability
- No window chrome, no OS UI elements visible
- Cursor blinks during typing, stops after output appears
- Receipt hashes truncated to 8 chars for display (full hash in actual output)
- Speed: commands execute at natural speed, no artificial delays
- Total file size target: under 5MB for HN embed, under 10MB for GitHub

## Alternative: GIF Version

If producing a GIF instead of video:
- Loop the `avs demo` section (00:05-00:18) infinitely
- Overlay the tagline "Every agent action gets a receipt." as static text at bottom
- File size target: under 3MB
