# Runbook: <service> — <symptom>

| | |
|---|---|
| Alert / trigger | <alert name, link to policy> |
| Severity | <SEV level and paging policy> |
| Owner | <team, escalation channel> |
| Last tested | YYYY-MM-DD |

## Summary
<One paragraph: what is broken for whom, and the usual cause.>

## Impact check (read-only, 5 minutes)
1. <Dashboard link and what "bad" looks like>
2. ```bash
   kubectl --context <context> -n <namespace> get pods -l app=<app>
   ```
   Expected: <healthy output>.
3. ```bash
   gcloud logging read '<filter>' --project <project-id> --freshness=30m --limit=50 --format='value(timestamp,jsonPayload.message)'
   ```

## Diagnose
| Observation | Likely cause | Go to |
|---|---|---|
| <symptom> | <cause> | [Fix A](#fix-a) |

## Fix A: <name>
1. <Mutating step, with the exact command>
   - **Rollback:** <exact command>
2. Verify: <command + expected output>

## Escalate when
- <condition> → <team/channel>, include <data to attach>

## Follow-ups
- [ ] <ticket for the permanent fix>

## References
- <architecture doc, ADR, dashboards, past incidents>
