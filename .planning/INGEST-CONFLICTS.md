## Conflict Detection Report

### BLOCKERS (0)

### WARNINGS (0)

### INFO (3)

[INFO] Precedence resolution: AGENTS.md establishes authoritative architectural constraints
  Note: AGENTS.md is locked at highest precedence (precedence 0), setting hard boundaries for fake providers, cost guards, and file size limits across all lane prompts.

[INFO] Frozen contracts boundary enforced
  Note: contracts/interfaces.md, contracts/events.schema.json, and contracts/openapi.yaml hold precedence 1; prompt specifications align with these contracts without modifications to contracts/.

[INFO] Default development mode set to fake/cassette offline execution
  Note: All agent prompts and subsystem specifications default to offline fake providers or recorded cassette replays; live API access is restricted to the project owner via smoke.py.
