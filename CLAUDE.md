# Slack Reaction Finder - Project Documentation

## Project Purpose

**Slack Reaction Finder** is a CLI tool that searches a Slack workspace for messages with specific emoji reactions and ranks them by reaction count. It helps teams discover the most positively received messages (e.g., messages with :pray:, :thanks:, or :tada: reactions) within a specific time period.

### Main Use Cases
- Find the most appreciated posts in a team workspace
- Extract gratitude or appreciation posts for team morale tracking
- Analyze team sentiment around specific topics during a time period
- Discover popular or well-received announcements

## Architecture & Code Organization

### Project Structure
```
slack_reaction_finder/
├── reaction_finder.py          # Main application (single file CLI tool)
├── test_reaction_finder.py     # Comprehensive unit test suite
├── requirements.txt            # Python dependencies
├── README.md                   # User-facing documentation (Japanese)
├── CLAUDE.md                  # This file
├── .gitignore
└── .git/
```

### Core Components

The application is organized into **functional modules** within a single Python file:

1. **CLI Argument Parsing** (`parse_arguments()`)
   - Handles all command-line options with validation
   - Supports flexible date range specification (--days, --after, --before, --on)
   - Validates conflicting options (e.g., --on cannot be used with --after/--before/--days)

2. **Date Query Builder** (`build_date_query()`)
   - Converts CLI date arguments into Slack Search API query syntax
   - Handles multiple date specification modes:
     - Single day: `--on YYYY-MM-DD`
     - Relative: `--days N` (last N days)
     - Range: `--after YYYY-MM-DD --before YYYY-MM-DD`
     - Reverse range: `--days N --before YYYY-MM-DD`
   - Validates date logic and format

3. **Slack API Integration** (`search_and_analyze()`)
   - Uses Slack SDK's Search API with pagination
   - Fetches up to `--max` results (default 100, max 1000)
   - Handles API's 100-item-per-page limit with pagination
   - Filters results to only include messages with the target emoji

4. **Message Detail Retrieval** (`fetch_message_details()`)
   - Gets full message context via `conversations_history` API
   - Verifies the target emoji exists in the message's reactions
   - Extracts: reaction count, timestamp, channel, user, text preview, permalink
   - Returns None if target emoji not found (filters out false positives from search)

5. **Output Formatting** (`print_results()`)
   - Displays top N results (default 3)
   - Shows formatted message details with channel, author, content preview
   - Provides statistics: total messages analyzed, total reactions, average reactions, date range

6. **Error Handling & Validation**
   - Token validation before API calls
   - Slack API error handling with specific error codes (channel_not_found, rate_limited)
   - Date format validation
   - Graceful degradation (returns user_id if real name lookup fails)

### Data Flow

```
CLI Arguments
    ↓
Parse & Validate Arguments
    ↓
Build Date Query (--days, --after, --before, --on)
    ↓
Validate Token
    ↓
Search API (has::<emoji>: <date_query>)
    ↓
Paginate through results (up to --max items)
    ↓
For each match: Fetch message details & verify emoji
    ↓
Sort by reaction count (descending)
    ↓
Display top N results with formatting
```

## Key Design Patterns & Conventions

### 1. **Single-File Architecture**
- Entire application in one file for easy distribution and deployment
- No external classes; functions organized by responsibility
- Simple, straightforward control flow from main()

### 2. **Configuration via Environment Variables & CLI**
- Primary token: `SLACK_REACTION_FINDER` environment variable
- Fallback: `-t/--token` command-line argument
- Follows pattern of reading env vars with defaults

### 3. **Defensive API Usage**
- Search API call followed by verification via history API
  - Search API returns messages mentioning emoji in text, not necessarily with reactions
  - History API confirms emoji exists in reactions field
  - This two-step process eliminates false positives
- Pagination handling with min() to not exceed max_results
- Error handling distinguishes between recoverable (channel_not_found) and non-recoverable errors

### 4. **Flexible Date Handling**
- Multiple ways to specify date ranges (user-friendly)
- All converted to Slack's `after:` and `before:` query operators
- Validation ensures logical date ranges (after < before)

### 5. **Internationalization (Japanese)**
- All user-facing strings in Japanese (emoji handling, output messages, errors)
- Date formatting includes Japanese-style text ("YYYY年MM月DD日 HH:MM:SS")
- Supports Japanese emoji names and descriptions

## Commands & Operations

### Build/Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Or individual install
pip3 install slack-sdk>=3.27.0

# Set up environment variable (recommended)
export SLACK_REACTION_FINDER_TOKEN="xoxb-your-bot-token"
```

### Running the Application
```bash
# Basic: search for emoji reactions (top 3 by default)
python3 reaction_finder.py <emoji_name>

# With options
python3 reaction_finder.py <emoji_name> [options]
```

### Common Usage Patterns
```bash
# Last 30 days, top 5
python3 reaction_finder.py pray --days 30 -n 5

# Specific date range
python3 reaction_finder.py thanks --after 2024-01-01 --before 2024-03-31 -n 10

# Specific date only
python3 reaction_finder.py tada --on 2024-06-15

# Search up to 200 results
python3 reaction_finder.py pray --max 200

# With explicit token
python3 reaction_finder.py pray -t xoxb-your-token
```

### Testing
```bash
# Run full test suite
python3 -m unittest test_reaction_finder.py

# Run specific test class
python3 -m unittest test_reaction_finder.TestParseArguments

# Run with verbose output
python3 -m unittest test_reaction_finder.py -v
```

## Dependencies & Requirements

### External Dependencies
- **slack-sdk** (>=3.27.0): Official Slack Python SDK
  - Provides WebClient for API calls
  - Handles authentication and error handling
  - Used APIs: search_messages, conversations_history, users_info

### Python Version
- Python 3.6+ (uses type hints, f-strings)

### Required Slack Permissions (Bot Token Scopes)
```
channels:history   - Read public channel history
channels:read      - Read public channel info
groups:history     - Read private channel history
groups:read        - Read private channel info
im:history         - Read DM history
reactions:read     - Read reaction information
search:read        - Search workspace
users:read         - Read user information
```

### Standard Library Dependencies (no external install needed)
- argparse: CLI argument parsing
- sys: System exit and argv access
- os: Environment variable access
- datetime, timedelta: Date/time handling
- typing: Type hints (Dict, List, Optional)

## Testing Architecture

### Test Suite Overview (`test_reaction_finder.py`)
- **Framework**: unittest (Python standard library)
- **Mocking**: unittest.mock (Mock, patch, MagicMock)
- **Coverage**: 5 main test classes covering all functions

### Test Organization

1. **TestParseArguments** (14 tests)
   - Basic argument parsing
   - Date argument combinations
   - --max validation and warnings
   - Environment variable fallback
   - Conflicting option detection (--on with others)

2. **TestValidateToken** (3 tests)
   - None/empty token rejection
   - Valid token acceptance

3. **TestBuildDateQuery** (14 tests)
   - All date specification modes (--on, --after, --before, --days)
   - Date validation and error messages
   - Edge cases (same date, invalid formats, reversed ranges)
   - Pagination: --days with --before

4. **TestFetchMessageDetails** (8 tests)
   - Message extraction with target emoji
   - Multiple reactions handling
   - Missing reactions/emoji cases
   - Empty results handling
   - Default values (user fallback, "(テキストなし)")
   - API error handling (rate_limited vs channel_not_found)

5. **TestSearchAndAnalyze** (9 tests)
   - Single page search
   - Pagination with multiple pages
   - Result limiting to --max
   - Sorting by reaction count (descending)
   - Filtering None results (target emoji not found)
   - Empty search results
   - Exact pagination boundaries

### Testing Best Practices Used
- Mocking external API calls (WebClient)
- Patching datetime for reproducible tests
- Descriptive test names explaining the scenario
- Docstrings explaining what each test validates
- Testing both happy paths and error conditions
- Edge case coverage (empty results, missing fields, etc.)

## Important Implementation Details

### API Search Behavior
- Slack Search API query: `has::<emoji>: <date_query>`
- "has::" operator searches for emoji mentions in message text, NOT reactions
- Must verify reactions separately via history API
- Results sorted by timestamp descending

### Pagination Strategy
```python
API_MAX_PER_PAGE = 100  # Slack API limit
while len(all_matches) < max_results:
    count = min(API_MAX_PER_PAGE, max_results - len(all_matches))
    # fetch page
    page += 1
    if len(matches) < count or len(all_matches) >= max_results:
        break
```

### Message Detail Extraction
```python
# Gets single message via conversations_history
# Verifies target emoji in reactions array
# Returns count field for that specific emoji
# Handles missing reactions key gracefully
```

### Constants & Configuration
```python
DEFAULT_MAX_SEARCH_RESULTS = 100  # Default max results to fetch
MAX_TEXT_PREVIEW_LENGTH = 150     # Truncate preview to this length
SEPARATOR = "=" * 80              # Output formatting
ENV_TOKEN_NAME = 'SLACK_REACTION_FINDER'
DATE_FORMAT = '%Y-%m-%d'          # Input date format
DATETIME_DISPLAY_FORMAT = '%Y年%m月%d日 %H:%M:%S'  # Output format
```

## Potential Improvement Areas (For Future Reference)

1. **Performance**: Add caching for user lookups
2. **Output Formats**: Support JSON/CSV export
3. **Filtering**: Filter by channel or user
4. **Batch Operations**: Search multiple emojis in one run
5. **Configuration Files**: Support config file instead of only CLI args
6. **Concurrency**: Parallel message detail fetching
7. **Error Recovery**: Retry logic for rate limiting

## Troubleshooting Guide for Claude Code

### Common Issues

1. **"not_allowed_token_type" Error**
   - Using User Token instead of Bot Token
   - Bot tokens start with `xoxb-`, user tokens start with `xoxp-`
   - Check token in Slack App > OAuth & Permissions

2. **Zero Results**
   - Emoji name incorrect (use `pray` not `:pray:`)
   - Date range has no messages with that emoji
   - Bot lacks required scopes

3. **Rate Limiting**
   - Searching large date ranges with --max > 500
   - Retry with longer intervals
   - Consider using smaller --max values

4. **Channel Not Found Error**
   - Silently handled in code (bot doesn't have access)
   - Check bot added to channels in workspace settings

## File Locations & References

- Main code: `/Users/danny/Develop/slack_reaction_finder/reaction_finder.py`
- Tests: `/Users/danny/Develop/slack_reaction_finder/test_reaction_finder.py`
- Dependencies: `/Users/danny/Develop/slack_reaction_finder/requirements.txt`
- Docs: `/Users/danny/Develop/slack_reaction_finder/README.md` (Japanese)

