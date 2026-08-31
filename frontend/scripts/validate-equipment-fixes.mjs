#!/usr/bin/env node
/**
 * 验证设备模块修复的正确性
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..');

function checkFile(filePath, checks) {
  const fullPath = join(rootDir, filePath);
  console.log(`\n检查文件: ${filePath}`);
  
  try {
    const content = readFileSync(fullPath, 'utf-8');
    const lines = content.split('\n');
    
    let hasError = false;
    
    for (const [name, checkFn] of Object.entries(checks)) {
      const result = checkFn(content, lines);
      if (!result.passed) {
        console.error(`  ❌ ${name}: ${result.message}`);
        hasError = true;
      } else {
        console.log(`  ✅ ${name}`);
      }
    }
    
    return !hasError;
  } catch (error) {
    console.error(`  ❌ 无法读取文件: ${error.message}`);
    return false;
  }
}

const equipmentChecks = {
  '无合并冲突标记': (content) => {
    const conflictMarkers = content.match(/^<{7}|^>{7}|^={7}/gm);
    if (conflictMarkers) {
      return { passed: false, message: `发现 ${conflictMarkers.length} 个合并冲突标记` };
    }
    return { passed: true };
  },
  '注释分隔符格式正确': (content, lines) => {
    const issues = [];
    lines.forEach((line, index) => {
      if (/\/\/\s*=+\s*\w+/.test(line) && !line.trim().endsWith('=')) {
        const nextChar = line.match(/\/\/\s*=+\s*([a-zA-Z])/);
        if (nextChar && !line.trim().match(/^\/\/\s*=+$/)) {
          issues.push(`Line ${index + 1}: 注释后应有换行符`);
        }
      }
    });
    if (issues.length > 0) {
      return { passed: false, message: issues.join('; ') };
    }
    return { passed: true };
  },
};

const equipmentPageChecks = {
  '无合并冲突标记': (content) => {
    const conflictMarkers = content.match(/^<{7}|^>{7}|^={7}/gm);
    if (conflictMarkers) {
      return { passed: false, message: `发现 ${conflictMarkers.length} 个合并冲突标记` };
    }
    return { passed: true };
  },
  '无重复 import': (content, lines) => {
    const imports = {};
    let hasDuplicate = false;
    lines.forEach((line, index) => {
      const importMatch = line.match(/^import\s+{\s*(.+?)\s*}\s+from\s+'(.+?)'/);
      if (importMatch) {
        const [, names, source] = importMatch;
        const key = `${names.trim()} from '${source}'`;
        if (imports[key]) {
          hasDuplicate = true;
          console.error(`    重复: Line ${imports[key]} 和 Line ${index + 1}: ${key}`);
        } else {
          imports[key] = index + 1;
        }
      }
    });
    if (hasDuplicate) {
      return { passed: false, message: '发现重复的 import 语句' };
    }
    return { passed: true };
  },
};

console.log('=== 设备模块修复验证 ===\n');

let allPassed = true;
allPassed &= checkFile('src/actions/equipment/equipment.ts', equipmentChecks);
allPassed &= checkFile('src/app/(dashboard)/equipment/assets/EquipmentPage.tsx', equipmentPageChecks);

// 额外检查：导入路径规范
console.log('\n=== 导入路径规范检查 ===\n');

const equipmentPagePath = 'src/app/(dashboard)/equipment/assets/EquipmentPage.tsx';
const equipmentPageContent = readFileSync(join(rootDir, equipmentPagePath), 'utf-8');

const relativeComponentImports = equipmentPageContent.match(/from\s+'\.\//g);
if (relativeComponentImports && relativeComponentImports.length > 0) {
  console.error(`  ❌ 发现 ${relativeComponentImports.length} 处相对路径导入组件`);
  console.error('     应使用: from \'@/components/equipment\'');
  allPassed = false;
} else {
  console.log('  ✅ 所有组件导入使用正确的绝对路径 (@/components/equipment)');
}

const directComponentImports = equipmentPageContent.match(/from\s+'@\/components\/equipment\/[A-Z]/g);
if (directComponentImports && directComponentImports.length > 0) {
  console.error(`  ⚠️  发现 ${directComponentImports.length} 处直接导入组件内部文件`);
  console.error('     建议改为: from \'@/components/equipment\' (通过 index.ts 导出)');
  allPassed = false;
} else {
  console.log('  ✅ 组件导入符合模块边界规范（通过 index.ts）');
}

console.log('\n' + '='.repeat(50));
if (allPassed) {
  console.log('✅ 所有检查通过！');
  process.exit(0);
} else {
  console.log('❌ 部分检查失败！');
  process.exit(1);
}
