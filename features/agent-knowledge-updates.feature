Feature: Agentic knowledge updates and diary traceability
  Authorized agents must use the same domain rules as humans.

  Scenario: Agent publishes a valid update
    Given an authenticated agent with write scope for a knowledge record
    And the agent knows the current record version
    When the agent submits a valid patch with summary and idempotency key
    Then the new OKF version is committed
    And exactly one diary entry summarizes the update
    And the entry links to the canonical original record
    And the entry resolves the exact before and after versions
    And the reader can open the full diff on demand

  Scenario: Retried agent command is idempotent
    Given an agent update was successfully committed
    When the same idempotency key is submitted again
    Then the existing update result is returned
    And no duplicate diary entry is created

  Scenario: Invalid or conflicting update
    Given an agent proposes an invalid OKF patch or stale version
    When the gateway validates the command
    Then the command is rejected
    And no successful diary entry is published

  Scenario: Unauthorized agent cannot read or modify private content
    Given a private record outside the agent's scopes
    When the agent requests its content or proposes an update
    Then access is denied without exposing private content
    And no private summary or diff is exported publicly

  Scenario: Direct Git change cannot bypass the diary
    Given a knowledge-changing commit without a corresponding journal event
    When repository validation runs
    Then the commit is rejected or flagged for mandatory reconciliation
    And the change is not reported as fully journaled

  Scenario: Multiple records change in one logical operation
    Given an authorized agent submits a multi-record change
    When the operation commits successfully
    Then one grouped diary entry is created
    And each changed record has an exact diff and source link
