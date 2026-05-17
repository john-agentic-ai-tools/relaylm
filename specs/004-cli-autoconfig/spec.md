# Feature Specification: CLI Autoconfig

**Feature Branch**: `005-cli-autoconfig`

**Created**: 2026-05-13

**Status**: Draft

**Input**: User description: "Implement the autoconfig feature of the CLI. It should be able to autodiscover the coding agents installed on the machine. If none are found provide feedback and list supported tools which are currently limited to OpenCode and Claude Code. It should back up configs before changing so it can be reverted. It should show what it changed and provide information on what user can do to test."

## User Scenarios & Testing

### User Story 1 - Autodiscover and configure detected agents (Priority: P1)

The user runs the autoconfig command. The CLI scans the machine for installed coding agents, detects one or more supported agents (OpenCode, Claude Code), creates a timestamped backup of the current CLI config, updates the config to register the detected agents, and displays a summary of changes made along with instructions on how to test the new configuration.

**Why this priority**: This is the primary value proposition of the feature — automatic detection and painless setup.

**Independent Test**: Can be fully tested by running the autoconfig command on a machine with one or more supported coding agents installed, then verifying the CLI config was updated and a backup was created.

**Acceptance Scenarios**:

1. **Given** a machine with OpenCode installed and a valid CLI config, **When** the user runs `relaylm autoconfig`, **Then** the CLI detects OpenCode, creates a backup of the existing config, updates the config with OpenCode settings, and displays a summary of changes
2. **Given** a machine with Claude Code installed and a valid CLI config, **When** the user runs `relaylm autoconfig`, **Then** the CLI detects Claude Code, creates a backup, updates the config, and shows changes
3. **Given** a machine with both OpenCode and Claude Code installed, **When** the user runs `relaylm autoconfig`, **Then** both agents are detected and configured

---

### User Story 2 - No supported agents found (Priority: P1)

The user runs the autoconfig command on a machine where none of the supported coding agents are installed. The CLI scans the machine, finds nothing, displays a friendly message indicating no supported agents were detected, and lists OpenCode and Claude Code as the currently supported tools along with guidance on how to install them.

**Why this priority**: Users without any agents need clear, helpful guidance — this is equally important to the success path.

**Independent Test**: Can be tested by running autoconfig on a machine with none of the supported agents installed.

**Acceptance Scenarios**:

1. **Given** a machine with no supported coding agents, **When** the user runs `relaylm autoconfig`, **Then** the CLI reports that no supported agents were found
2. **Given** a machine with no supported coding agents, **When** the user runs `relaylm autoconfig`, **Then** the output lists OpenCode and Claude Code as supported tools
3. **Given** a machine with no supported coding agents, **When** the user runs `relaylm autoconfig`, **Then** no config changes are made and no backup is created

---

### User Story 3 - Revert autoconfig changes from backup (Priority: P2)

After running autoconfig, the user decides to revert the changes. They run a revert command, and the CLI restores the previous config from the backup created during autoconfig, showing which backup was used and confirming the original state was restored.

**Why this priority**: Safe revert capability is essential for user confidence, but secondary to the core autoconfig flow.

**Independent Test**: Can be tested by running autoconfig, verifying config changed, then running revert and verifying original config is restored.

**Acceptance Scenarios**:

1. **Given** autoconfig was previously run and a backup exists, **When** the user runs the revert command, **Then** the CLI restores the config from the most recent backup
2. **Given** no autoconfig has ever been run, **When** the user runs the revert command, **Then** the CLI reports that no backup is available
3. **Given** autoconfig was run and config was modified, **When** the user reverts, **Then** the CLI displays which backup file was used for restoration

---

### Edge Cases

- What happens when the CLI config file does not exist yet when autoconfig is run? A new config is created with detected agent settings; no backup is needed since there was nothing to overwrite.
- What happens when an agent is detected but its config is malformed or missing? The CLI notes the agent was found but reports that its configuration could not be read, and continues with other agents.
- What happens if the backup directory already has a backup with the same timestamp? The CLI appends a suffix (e.g., `_001`, `_002`) to ensure unique filenames.
- What happens when the user has no write permission to the config directory? The CLI reports the error clearly and suggests running with appropriate permissions.
- What happens if the revert command finds multiple backups? The CLI uses the most recent backup by default.

## Requirements

### Functional Requirements

- **FR-001**: CLI MUST scan the system for installed OpenCode and Claude Code agents using standard detection mechanisms (e.g., known install paths, PATH environment variable, common locations for each OS)
- **FR-002**: CLI MUST create a timestamped backup of the existing CLI config file before making any modifications
- **FR-003**: CLI MUST display a summary of all detected agents and all configuration changes made during the autoconfig run
- **FR-004**: CLI MUST provide a revert command that restores the config from the most recent backup
- **FR-005**: If no supported agents are detected, CLI MUST display a message indicating no supported agents were found and MUST list OpenCode and Claude Code as the currently supported tools
- **FR-006**: CLI MUST NOT modify any agent's own configuration files — only the CLI's own config is modified
- **FR-007**: CLI MUST display actionable testing instructions after a successful autoconfig (e.g., "Try running `relaylm chat` to verify OpenCode integration")

### Key Entities

- **CodingAgent**: Represents a detected coding agent instance (OpenCode or Claude Code). Includes detection metadata such as agent name, detected version, and install path.
- **ConfigBackup**: Represents a snapshot of the CLI config file taken before modification. Includes the backup file path, creation timestamp, and original config location.
- **AutoconfigResult**: Represents the overall outcome of an autoconfig run. Includes the list of detected agents, list of config changes made, the backup reference (if any), and any warnings or errors.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can run the autoconfig command and see results (agents found and config changes) within 5 seconds on a standard machine
- **SC-002**: 100% of autoconfig runs that modify config files produce a timestamped backup before any changes are applied
- **SC-003**: Users can restore the pre-autoconfig CLI config from backup with a single command in under 10 seconds
- **SC-004**: Users without any supported agents receive a clear message listing OpenCode and Claude Code as options, with no config changes attempted
- **SC-005**: The autoconfig feature works correctly on Windows, macOS, and Linux for all supported agents

## Assumptions

- Users have typical read/write permissions to their CLI config directory
- OpenCode is detected via its standard config/install locations (e.g., `~/.config/opencode/`, known PATH entries)
- Claude Code is detected via its standard install locations (e.g., `~/.claude/`, `npx` availability)
- The CLI config file uses a standard format (JSON or YAML) that can be programmatically read and written
- Backup files are stored in a dedicated `.backups/` subdirectory within the CLI config directory
- The revert command only restores the CLI's own config — it does not modify agent configs
