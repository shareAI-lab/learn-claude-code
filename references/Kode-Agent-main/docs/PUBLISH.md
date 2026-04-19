# Publishing Kode to NPM

## Architecture Overview

This package uses an elegant hybrid approach:
- **Bun** for development and building
- **Direct source execution** without bundling (avoiding complex build issues)
- **Automatic runtime detection** (bun > tsx > npx tsx)
- **Full TypeScript/JSX support** out of the box

## Build System

The build process (`scripts/build.ts`) creates:
1. `cli.js` - Smart wrapper that detects and uses the best available runtime
2. `.npmrc` - Ensures proper dependency resolution

## Pre-publish Checklist

1. **Update version** in package.json
2. **Run build**: `bun run build`
3. **Test locally**: `./cli.js --help`
4. **Run checks**: `node scripts/prepublish-check.js`

## Publishing Steps

```bash
# 1. Clean and build
bun run clean
bun run build

# 2. Test the CLI
./cli.js --help

# 3. Publish to npm
npm publish --access public
```

## Post-publish Verification

```bash
# Install globally
npm install -g @shareai-lab/kode

# Test
kode --help
```

## Key Features

- ✅ No complex bundling - runs TypeScript directly
- ✅ Works with both Bun and Node.js environments
- ✅ Minimal dependencies bundled
- ✅ Fast startup time
- ✅ Source maps for debugging