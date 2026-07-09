# Agent Rules for HospitalAI

## Git Push Constraint
- **CRITICAL**: The agent must NEVER run `git push` or push code to the remote repository without receiving explicit user approval beforehand.

## Command Execution
- All shell and process commands should be executed automatically and directly without waiting for manual user submission or individual approvals (with the exception of `git push` which requires explicit confirmation).
