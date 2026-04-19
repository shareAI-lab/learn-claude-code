#!/usr/bin/env node

const { execSync } = require('child_process');
const { readFileSync, writeFileSync } = require('fs');
const path = require('path');
const readline = require('readline');

/**
 * 发布正式版本到 npm
 * 使用 latest tag，支持语义化版本升级
 * 不涉及 git 操作，专注于 npm 发布
 */
async function publishRelease() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  const question = (query) => new Promise(resolve => rl.question(query, resolve));

  try {
    console.log('🚀 Starting production release process...\n');

    // 1. 读取当前版本
    const packagePath = path.join(process.cwd(), 'package.json');
    const packageJson = JSON.parse(readFileSync(packagePath, 'utf8'));
    const currentVersion = packageJson.version;

    console.log(`📦 Current version: ${currentVersion}`);

    // 2. 选择版本升级类型
    console.log('\n🔢 Version bump options:');
    const versionParts = currentVersion.split('.');
    const major = parseInt(versionParts[0]);
    const minor = parseInt(versionParts[1]);
    const patch = parseInt(versionParts[2]);

    console.log(`  1. patch  → ${major}.${minor}.${patch + 1} (bug fixes)`);
    console.log(`  2. minor  → ${major}.${minor + 1}.0 (new features)`);
    console.log(`  3. major  → ${major + 1}.0.0 (breaking changes)`);
    console.log(`  4. custom → enter custom version`);

    const choice = await question('\nSelect version bump (1-4): ');
    
    let newVersion;
    switch (choice) {
      case '1':
        newVersion = `${major}.${minor}.${patch + 1}`;
        break;
      case '2':
        newVersion = `${major}.${minor + 1}.0`;
        break;
      case '3':
        newVersion = `${major + 1}.0.0`;
        break;
      case '4':
        newVersion = await question('Enter custom version: ');
        break;
      default:
        console.log('❌ Invalid choice');
        process.exit(1);
    }

    // 3. 检查版本是否已存在
    try {
      execSync(`npm view @shareai-lab/kode@${newVersion} version`, { stdio: 'ignore' });
      console.log(`❌ Version ${newVersion} already exists on npm`);
      process.exit(1);
    } catch {
      // 版本不存在，可以继续
    }

    // 4. 确认发布
    console.log(`\n📋 Release Summary:`);
    console.log(`   Current: ${currentVersion}`);
    console.log(`   New:     ${newVersion}`);
    console.log(`   Tag:     latest`);

    const confirm = await question('\n🤔 Proceed with release? (y/N): ');
    if (confirm.toLowerCase() !== 'y') {
      console.log('❌ Cancelled');
      process.exit(0);
    }

    // 5. 更新版本号
    console.log('📝 Updating version...');
    const originalPackageJson = { ...packageJson };
    packageJson.version = newVersion;
    writeFileSync(packagePath, JSON.stringify(packageJson, null, 2));

    // 6. 运行测试
    console.log('🧪 Running tests...');
    try {
      execSync('npm run typecheck', { stdio: 'inherit' });
      execSync('npm test', { stdio: 'inherit' });
    } catch (error) {
      console.log('❌ Tests failed, rolling back version...');
      writeFileSync(packagePath, JSON.stringify(originalPackageJson, null, 2));
      process.exit(1);
    }

    // 7. 构建项目
    console.log('🔨 Building project...');
    execSync('npm run build', { stdio: 'inherit' });

    // 8. 运行预发布检查
    console.log('🔍 Running pre-publish checks...');
    execSync('bun run scripts/prepublish-check.js', { stdio: 'inherit' });

    // 9. 发布到 npm
    console.log('📤 Publishing to npm...');
    execSync('npm publish --access public', { stdio: 'inherit' });

    console.log('\n🎉 Production release published successfully!');
    console.log(`📦 Version: ${newVersion}`);
    console.log(`🔗 Install with: npm install -g @shareai-lab/kode`);
    console.log(`🔗 Or: npm install -g @shareai-lab/kode@${newVersion}`);
    console.log(`📊 View on npm: https://www.npmjs.com/package/@shareai-lab/kode`);
    
    console.log('\n💡 Next steps:');
    console.log('   - Commit the version change to git');
    console.log('   - Create a git tag for this release');
    console.log('   - Push changes to the repository');

  } catch (error) {
    console.error('❌ Production release failed:', error.message);
    
    // 尝试恢复 package.json
    try {
      const packagePath = path.join(process.cwd(), 'package.json');
      const originalContent = readFileSync(packagePath, 'utf8');
      // 如果版本被修改了，尝试恢复（这里简化处理）
      console.log('🔄 Please manually restore package.json if needed');
    } catch {}
    
    process.exit(1);
  } finally {
    rl.close();
  }
}

publishRelease();
