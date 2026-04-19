# Intelligent Completion System

## Overview

Kode features a state-of-the-art intelligent completion system that revolutionizes terminal interaction with AI agents and commands. The system uses advanced fuzzy matching algorithms inspired by Chinese input methods, modern IDEs, and terminal fuzzy finders.

## Key Features

### 1. Advanced Fuzzy Matching Algorithm

Our custom `advancedFuzzyMatcher` combines multiple matching strategies:

- **Exact Prefix Matching** - Highest priority for exact starts
- **Hyphen-Aware Matching** - Treats hyphens as optional word boundaries
- **Word Boundary Detection** - Matches characters at word starts
- **Abbreviation Matching** - Supports shortcuts like `dq` → `dao-qi`
- **Numeric Suffix Handling** - Intelligently matches `py3` → `python3`
- **Subsequence Matching** - Characters appear in order
- **Fuzzy Segment Matching** - Flexible segment matching

### 2. Smart Context Detection

The system automatically detects context without requiring special prefixes:

```bash
# Type without @, system adds it automatically
gp5      → @ask-gpt-5
daoqi    → @run-agent-dao-qi-harmony-designer
py3      → python3

# Tab key fills the match with appropriate prefix
# Enter key completes and adds space
```

### 3. Unix Command Intelligence

#### Common Commands Database
- 500+ curated common Unix/Linux commands
- Categories: File operations, text processing, development tools, network utilities, etc.
- Smart intersection with system PATH - only shows commands that actually exist

#### Priority Scoring
Commands are ranked by:
1. Match quality score
2. Common usage frequency
3. Position in command database

### 4. Multi-Source Completion

The system seamlessly combines completions from:
- **Slash Commands** (`/help`, `/model`, etc.)
- **Agent Mentions** (`@run-agent-*`)
- **Model Consultations** (`@ask-*`)
- **Unix Commands** (from system PATH)
- **File Paths** (directories and files)

## Architecture

### Core Components

```
src/
├── utils/
│   ├── advancedFuzzyMatcher.ts    # Advanced matching algorithms
│   ├── fuzzyMatcher.ts            # Original matcher (facade)
│   └── commonUnixCommands.ts      # Unix command database
└── hooks/
    └── useUnifiedCompletion.ts     # Main completion hook
```

### Algorithm Details

#### Hyphen-Aware Matching
```typescript
// Handles: dao → dao-qi-harmony-designer
// Split by hyphens and match flexibly
const words = text.split('-')
// Check concatenated version (ignoring hyphens)
const concatenated = words.join('')
```

#### Numeric Suffix Matching
```typescript
// Handles: py3 → python3
const patternMatch = pattern.match(/^(.+?)(\d+)$/)
if (text.endsWith(suffix) && textWithoutSuffix.startsWith(prefix)) {
  // High score for numeric suffix match
}
```

#### Word Boundary Matching
```typescript
// Handles: dq → dao-qi
// Match characters at word boundaries
for (const word of words) {
  if (word[0] === pattern[patternIdx]) {
    score += 50 // Bonus for word boundary
  }
}
```

## Usage Examples

### Basic Fuzzy Matching
```bash
# Abbreviations
nde     → node
np      → npm
dk      → docker

# Partial matches
kub     → kubectl
vim     → vim, nvim

# Numeric patterns
py3     → python3
n18     → node18
```

### Agent/Model Matching
```bash
# Without @ prefix (auto-added on completion)
gp5     → @ask-gpt-5
claude  → @ask-claude-sonnet-4
dao     → @run-agent-dao-qi-harmony-designer
daoqi   → @run-agent-dao-qi-harmony-designer
```

### Smart Prioritization
```bash
# Input: "doc"
1. docker (common command, high priority)
2. document (if exists)
3. doctor (if exists)

# Input: "g"
1. git (most common)
2. grep (common)
3. go (if installed)
```

## Configuration

### Minimum Score Threshold
The system uses a minimum score of 5 (very low) to allow flexible matching while filtering noise.

### Match Ranking
Results are sorted by:
1. Match algorithm score
2. Command priority (for Unix commands)
3. Type priority (agents/models > files > commands)

## Performance

- **Sub-millisecond matching** - Optimized algorithms for instant feedback
- **Lazy loading** - Commands loaded on first use
- **Smart caching** - Results cached per session
- **Efficient filtering** - Early termination for obvious non-matches

## Future Improvements

- [ ] Learning from user selections
- [ ] Project-specific command priorities
- [ ] Custom abbreviation definitions
- [ ] Typo correction with edit distance
- [ ] Context-aware suggestions based on recent commands