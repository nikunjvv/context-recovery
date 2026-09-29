# Rejected Usage Rerating Operations Runbook

## Document Information

- **Application:** Northstar Postpaid Billing
- **Process:** Nightly Usage Rerating
- **Document Version:** 4.2
- **Last Updated:** March 15, 2021
- **Owner:** Billing Operations
- **Status:** Active

## Purpose

The nightly rerating process reprocesses usage records that could not be rated successfully during their original processing attempt.

Records are commonly rejected because of missing reference data, delayed account updates, unavailable pricing information, or temporary processing failures.

## Schedule

The process runs daily at 1:00 AM after completion of the account-update and reference-data synchronization jobs.

The scheduler invokes:

nightly_rerate.sh


The script validates that prerequisite jobs completed successfully and then starts the `rerate_usage` program.

## Eligibility

All usage records with a processing status of `REJECTED` are eligible for automatic rerating.

The process does not require manual account-level screening. Any underlying data issue should be corrected before the nightly process begins.

## Processing Flow

1. Confirm completion of account and reference-data synchronization.
2. Select usage records with status `REJECTED`.
3. Retrieve the current account, product and pricing information.
4. Apply the current rating rules.
5. Update successfully rated records to `RATED`.
6. Leave unsuccessful records in `REJECTED` status.
7. Record the latest failure reason for operational investigation.
8. Produce the nightly rerating summary.

## Database Tables

The process primarily uses:

- usage_event
- account_profile
- invoice
- rate_plan
- rerate_audit

## Operational Validation

After completion, Billing Operations must confirm:

- The batch job completed successfully.
- The number of selected records is within the normal range.
- Successfully processed records moved to `RATED`.
- Remaining rejected records contain a current failure reason.
- No database or pricing-service errors appear in the batch log.

## Failure Handling

If the batch fails:

1. Do not restart it immediately.
2. Review the log for database, reference-data or pricing errors.
3. Correct the underlying issue.
4. Restart the process from the last successful checkpoint.
5. Notify Billing Operations if the rerating backlog exceeds its normal threshold.

## Notes

The nightly process is the standard mechanism for rerating all rejected postpaid usage records. Account-specific rerating exceptions are not documented for the current implementation.
