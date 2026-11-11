# Target design: openwiki/design/. Specification only; not proof of implementation.
Feature: Hierarchical records and one atomic writer
  Humans, CLI clients and MCP agents use one record-and-log aggregate.
  The diary is a generated view of committed per-record events.

  Scenario: Create and update a record without source date directories
    Given a trusted authorized writer and a clean expected repository revision
    When a record is created in its subject hierarchy and updated twice
    Then one canonical record and one sibling log exist
    And the log contains three distinct sequential events
    And the final snapshot equals the canonical record bytes
    And the diary contains three changes and one distinct record
    And no independently authored diary document is created

  Scenario: Retry after a successful commit response is lost
    Given a command has committed its record and log atomically
    When the identical command and idempotency key are submitted again
    Then the original event and operation identifiers are returned
    And no new event or commit is created

  Scenario: An idempotency key is reused with different input
    Given a command has already committed
    When its key is submitted with a different request digest
    Then IDEMPOTENCY_CONFLICT is returned
    And the repository does not change

  Scenario: Concurrent clones compete for one expected head
    Given two writers use the same expected repository head
    When both attempt to publish different transactions
    Then exactly one compare-and-swap succeeds
    And the other returns CONFLICT without a partial record or log write

  Scenario: Historical content cannot be rewritten by an ordinary change
    Given committed log entries at the trusted base revision
    When a proposed commit changes an old snapshot and recomputes its hash
    Then baseline-prefix validation rejects the commit

  Scenario: A record is moved and current relative links require repair
    Given all affected records are authorized and their histories are consistent
    When the move transaction commits
    Then the record and sibling log move together with the same record identifier
    And current links and structural indexes are updated atomically
    And every changed record has one event sharing the operation identifier
    And the diary displays one row per record event
    And historical snapshots remain unchanged

  Scenario: Current status does not rewrite historical status
    Given a draft revision followed by a completed revision
    When the reader opens the first event
    Then Draft is shown for that revision
    And Open current record shows Completed

  Scenario: A public current record does not authorize private history
    Given an update changes visibility from private to public
    When a public generation is built
    Then its private-before transition is not exported as an event or diff
    And no private identifiers or counts appear in the public payload

  Scenario: A direct Git edit bypasses the writer
    Given a canonical record change without a corresponding appended event
    When required validation runs
    Then validation fails
    And publication is blocked without automatic reconciliation

  Scenario: Native history works without Git history
    Given valid migrated records and sibling logs in a source copy without Git metadata
    When the projection builder runs
    Then current records and diary revisions and diffs are generated from source files

  Scenario: Calendar navigation remains separate from activity
    Given an important date with no recorded changes on that date
    When the reader selects that calendar day
    Then the reminder and its record link remain visible
    And View changes on this day opens the empty Day diary view

  Scenario: A failed build preserves the current publication
    Given a live immutable generation
    When a new source generation fails validation
    Then the live manifest still points to the previous complete generation

  Scenario: Legacy duplicate diary entries are migrated deterministically
    Given a reviewed mapping of a legacy update journal to a native event
    When migration runs twice from the same base and fixed manifest
    Then both output source trees are identical
    And unique legacy content is preserved or explicitly archived
    And the diary contains no duplicate bare journal copy
