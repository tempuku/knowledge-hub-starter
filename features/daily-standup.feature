# Proposed acceptance only: issue #72. No executable application implementation or private data.
Feature: Persistent and private cross-repository in-progress stand-up
  All active records stay visible until an explicit lifecycle change.
  Recency affects attention, not whether an item is active.

  Scenario: An active project has been quiet for ten days
    Given an authorized project record has status "in_progress"
    And its last verified activity was ten days ago
    When the owner opens the morning stand-up
    Then the project is still included among active work
    And the inactivity age is displayed
    And its status remains "in_progress"
    And the reader does not create a new history event

  Scenario: A child issue closes but its parent project remains active
    Given a parent Ivanovo Models project record has status "in_progress"
    And one linked building issue is closed after virtual acceptance
    And other linked building, LED and viewer work remains unfinished
    When the stand-up is generated
    Then the parent is still "in_progress"
    And the closed issue is shown as completed evidence
    And outstanding work is linked without inventing acceptance

  Scenario: Aggregation spans more than the app repository
    Given authorized records link separate Knowledge Hub, Ivanovo Models and Personal Finance repositories
    And each is explicitly "in_progress"
    When the owner requests a project stand-up
    Then active projects from all three repositories appear
    And each project's source links and independently verified latest state are shown
    And no project disappears because it has no activity today

  Scenario: A linked private repository cannot be reached
    Given an "in_progress" project with previously verified source evidence
    When a live refresh fails for its linked repository
    Then the project remains in the stand-up
    And the source state is labelled stale or unavailable
    And no new completion, blocker or acceptance is inferred

  Scenario: Personal and project records share one active view
    Given an authorized private personal record and an authorized project record
    And both are explicitly "in_progress"
    When the owner opens the global In progress view
    Then both records appear under their respective Private and Projects groups
    And each links to exactly one canonical record
    And no diary-only copy is required

  Scenario: Anonymous users never learn that private work exists
    Given private records and private events exist in the production source
    When an unauthorized user requests the public site and its generated data
    Then private record bodies, identifiers, titles, references and counts are absent
    And private read and attachment endpoints deny access
    And public artifacts do not reveal the private hierarchy

  Scenario: Historical inactive status does not replace current state
    Given a project history includes a draft revision followed by an explicit in_progress revision
    When the owner views current project state and the previous revision
    Then current state displays In progress
    And the previous revision still displays Draft
    And source freshness is displayed independently of record status

  Scenario: The same daily stand-up is opened twice
    Given no canonical records were edited between reads
    When the owner views the stand-up twice
    Then no new record log or diary event is created
    And all still-active records remain visible

  Scenario: A verified project state update is retried
    Given an authorized agent has committed a project record update and its sibling log atomically
    When the same update is retried with the same idempotency key
    Then the existing operation is returned
    And no duplicate log event or daily diary entry is added

  Scenario: Activity threshold changes without changing lifecycle
    Given an in_progress project has not changed for fourteen days
    When the owner changes the display's stale-age threshold
    Then the attention hint may change
    But the record status, stored content and history remain unchanged
