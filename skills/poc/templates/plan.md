# POC plan: <title>

| | |
|---|---|
| Owner | <name> |
| Timebox | <n> days, ends YYYY-MM-DD |
| Sandbox | <project / cluster / context — from config, never prod> |
| Cost cap | <amount> (set a budget alert) |

## Question
<The one decision this POC informs.>

## Hypothesis
<"If we <do X>, then <measurable outcome>, because <reason>." It must be possible for this to be false.>

## Success criteria
| Criterion | Target | How measured |
|---|---|---|
| <e.g. time to provision an AlloyDB cluster via XR> | <= 20 min | timestamps from `crossplane resource trace` |

## Kill criteria
- <e.g. provider can't express required network config>
- <e.g. reconcile errors not recoverable without manual intervention>

## Scope
- **In:** <the thinnest slice>
- **Out:** <HA, prod IAM, full CI, UI, ...>

## Approach
1. <steps>

## Risks and mitigations
| Risk | Mitigation |
|---|---|

## Teardown
- <exact commands / Git revert / Crossplane deletion order and deletionPolicy notes>
