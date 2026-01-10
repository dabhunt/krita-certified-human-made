#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Script to create a new bug report file with automatic numbering
 * First checks recent bugs to help avoid duplicates
 * Usage: node scripts/create-bug-report.js
 */

const BUGS_DIR = path.join(__dirname, '..', 'bugs');
const SOLVED_DIR = path.join(BUGS_DIR, 'solved');
const TEMPLATE_FILE = path.join(BUGS_DIR, 'bug-template.md');

// First, show recent bugs to help avoid duplicates
console.log('📋 Checking recent bugs to help avoid duplicates...\n');
try {
  execSync('node scripts/check-recent-bugs.js', { stdio: 'inherit' });
} catch (error) {
  console.warn('⚠️  Could not check recent bugs:', error.message);
}

console.log('\n🔍 Finding highest bug number...');

// Get all bug files from both directories
// Handles both Bug#XXX.md and BUG#XXX-DESCRIPTION.md formats
function getBugFiles(directory) {
  try {
    return fs.readdirSync(directory)
      .filter(file => /[Bb][Uu][Gg]#\d+/.test(file) && file.endsWith('.md'))
      .map(file => {
        // Match Bug# or BUG# followed by digits, with any text before .md
        const match = file.match(/[Bb][Uu][Gg]#(\d+)/);
        return match ? parseInt(match[1]) : 0;
      })
      .filter(num => num > 0);
  } catch (error) {
    console.warn(`Warning: Could not read directory ${directory}:`, error.message);
    return [];
  }
}

const mainBugNumbers = getBugFiles(BUGS_DIR);
const solvedBugNumbers = getBugFiles(SOLVED_DIR);
const allBugNumbers = [...mainBugNumbers, ...solvedBugNumbers];

if (allBugNumbers.length === 0) {
  console.error('❌ No existing bug files found!');
  process.exit(1);
}

const highestNumber = Math.max(...allBugNumbers);
const nextNumber = highestNumber + 1;
const nextBugId = nextNumber.toString().padStart(3, '0');
const newFileName = `Bug#${nextBugId}.md`;
const newFilePath = path.join(BUGS_DIR, newFileName);

console.log(`📊 Highest existing bug number: ${highestNumber.toString().padStart(3, '0')}`);
console.log(`➕ Next bug number: ${nextBugId}`);

// Check if template exists
if (!fs.existsSync(TEMPLATE_FILE)) {
  console.error(`❌ Template file not found: ${TEMPLATE_FILE}`);
  process.exit(1);
}

// Check if bug file already exists
if (fs.existsSync(newFilePath)) {
  console.error(`❌ Bug file already exists: ${newFilePath}`);
  process.exit(1);
}

// Read template and replace placeholder
let templateContent = fs.readFileSync(TEMPLATE_FILE, 'utf8');
const newContent = templateContent.replace(/#XXX/g, `#${nextBugId}`);

try {
  // Write new bug file
  fs.writeFileSync(newFilePath, newContent, 'utf8');
  console.log(`✅ Created new bug report: ${newFilePath}`);
  console.log(`📝 You can now edit the file to fill in the bug details.`);
} catch (error) {
  console.error(`❌ Failed to create bug file:`, error.message);
  process.exit(1);
}
