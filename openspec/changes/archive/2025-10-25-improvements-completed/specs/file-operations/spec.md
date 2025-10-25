## MODIFIED Requirements
### Requirement: File Locking
The system SHALL provide reliable file locking with reasonable timeout and retry strategy.

#### Scenario: Fast lock acquisition
- **WHEN** attempting to lock a file
- **THEN** the system SHALL timeout after 5 seconds instead of 30 seconds
- **AND** SHALL use exponential backoff for retries

#### Scenario: Stale lock cleanup
- **WHEN** encountering a stale lock file
- **THEN** the system SHALL detect and remove locks older than 30 seconds
- **AND** SHALL proceed with lock acquisition

#### Scenario: Improved error handling
- **WHEN** lock acquisition fails
- **THEN** the system SHALL provide clear timeout error messages
- **AND** SHALL distinguish between temporary and permanent failures