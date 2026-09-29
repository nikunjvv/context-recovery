# Hidden Rerating Rule in a Legacy Billing Application

## Background

The fictional telecom operator Northstar Communications uses a legacy billing application to process postpaid usage records and generate monthly invoices.

Fifteen years ago, Northstar migrated a group of corporate accounts from an older billing platform. During the migration, some usage records arrived after the customers' invoices had already been finalized and exported to the financial ledger.

The normal rerating process reopened these records automatically. For migrated corporate accounts, this occasionally caused previously billed usage to be credited and charged again, creating duplicate financial adjustments.

## Hidden Business Rule

A temporary exception was introduced:

> Do not automatically rerate usage for migrated corporate accounts when the associated invoice has already been finalized. Send the usage record to a  manual-review queue instead.

The rule was intended to remain only during migration stabilization, but it was never removed. Some of the affected accounts remain active today.

## Technical Implementation

The nightly batch script `nightly_rerate.sh` invokes the Pro*C program `rerate_usage.pc`.

The program reads:

- `account_profile`
- `usage_event`
- `invoice`

It evaluates the following conditions:

- `account_profile.account_type = 'CORPORATE'`
- `account_profile.migration_source = 'LEGACY_BILLER'`
- `invoice.status = 'FINALIZED'`

When all three conditions are true, the program does not rerate the usage record. Instead, it inserts an exception into `rerate_exception` with reason code `LEGACY_CORP_FINAL_INVOICE`.

## Context Problem

The current operations runbook states that all rejected usage records are automatically rerated during the nightly batch. It does not describe the corporate-account exception.

An old change record describes the exception as a temporary migration control, but it does not state whether or when the rule should be retired.

The source code contains the complete condition, but the business reason is only partially explained in a code comment.

No single source contains the complete context.

## Modernization Risk

A modernization team replacing the Pro*C program could implement the behavior described in the current runbook and omit the hidden exception.

This could cause:

- Finalized invoices to be modified after financial-ledger export
- Duplicate charges or credits
- Differences between billing and general-ledger balances
- Customer complaints and manual corrections
- Revenue-assurance and audit issues

Blindly preserving the rule also carries risk because the original migration may have ended and the exception may no longer be required.

The modernization team must therefore identify the rule, reconstruct its business purpose, determine which accounts still depend on it, and obtain business approval before preserving or removing it.

## Questions the Context Recovery Engine Must Answer

1. Why are some rejected usage records excluded from automatic rerating?
2. Which accounts are affected by the exception?
3. Where is the rule implemented?
4. Which programs, scripts and tables participate in the flow?
5. Does the current runbook accurately describe the implementation?
6. What could happen if the rule is removed?
7. Is there enough evidence to determine whether the rule is still required?

## Expected Answer Behavior

The system must:

- Cite the specific code, runbook and change-record evidence
- Distinguish documented facts from inferred intent
- Highlight contradictions between documentation and implementation
- Trace the flow from the batch script to the program and database tables
- State when available evidence is insufficient
- Never recommend removing the rule without human validation
