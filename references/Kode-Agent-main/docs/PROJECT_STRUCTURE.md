# Kode Project Structure

## Overview
Clean, modern TypeScript CLI project using Bun for development and building.

## Build System
- **Runtime**: Bun (preferred) with Node.js fallback
- **Build Tool**: Custom build.ts using Bun
- **Package Manager**: Bun (with npm publish compatibility)
- **TypeScript Execution**: Direct source execution (no bundling)

## Key Files
```
.
├── cli.js                 # Smart CLI wrapper (generated)
├── build.ts              # Build script
├── package.json          # Package configuration
├── tsconfig.json         # TypeScript configuration
├── yoga.wasm            # Required WASM file for Ink
├── .npmrc               # NPM configuration (generated)
├── .gitignore           # Git ignore rules
├── .prettierrc          # Code formatting config
│
├── src/                 # Source code
│   ├── entrypoints/
│   │   ├── cli.tsx      # Main CLI entry point
│   │   └── mcp.ts       # MCP server entry
│   ├── commands/        # Command implementations
│   ├── components/      # React/Ink components
│   ├── tools/           # AI tool implementations
│   ├── services/        # Core services
│   ├── hooks/           # React hooks
│   │   └── useUnifiedCompletion.ts  # Advanced completion system
│   ├── utils/           # Utility functions
│   │   ├── advancedFuzzyMatcher.ts  # 7+ algorithm fuzzy matcher
│   │   ├── fuzzyMatcher.ts          # Matcher integration layer
│   │   ├── commonUnixCommands.ts    # 500+ command database
│   │   └── agentLoader.ts           # Agent configuration loader
│   └── constants/       # Constants and configurations
│
├── docs/                # Documentation
│   └── custom-commands.md
│
├── scripts/             # Build and utility scripts
│   └── prepublish-check.js
│
├── test/                # Test files
│   └── customCommands.test.ts
│
├── README.md            # English documentation
├── README.zh-CN.md      # Chinese documentation
├── PUBLISH.md           # Publishing guide
├── AGENTS.md           # Project context (generated)
└── system-design.md     # System architecture doc (Chinese)
```

## Build & Run

### Development
```bash
bun run dev
```

### Build
```bash
bun run build
```

### Test CLI
```bash
./cli.js --help
```

### Publish
```bash
npm publish --access public
```

## Clean Architecture
- No build artifacts in source control
- Single lock file (bun.lock)
- Generated files properly ignored
- Clear separation of concerns
- Minimal dependencies bundled