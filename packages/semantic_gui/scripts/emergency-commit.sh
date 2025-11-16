#!/bin/bash

# Emergency commit script - bypasses quality checks
# Use only in emergency situations!

echo "🚨 EMERGENCY COMMIT MODE"
echo "======================="
echo "⚠️  This will bypass all quality checks!"
echo "⚠️  Use only in emergency situations!"
echo ""

read -p "Are you sure you want to proceed? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "❌ Emergency commit cancelled"
  exit 1
fi

echo ""
echo "📝 Please provide a reason for bypassing quality checks:"
read -p "Reason: " reason

if [ -z "$reason" ]; then
  echo "❌ Reason is required for emergency commits"
  exit 1
fi

echo ""
echo "🚨 Committing with quality checks bypassed..."
echo "📝 Reason: $reason"

# Set environment variable to bypass quality checks
export SKIP_QUALITY_CHECKS=true

# Add emergency commit message prefix
git add .
git commit -m "🚨 EMERGENCY: $reason

[QUALITY_CHECKS_BYPASSED]
This commit bypassed quality checks due to emergency situation.
Please address quality issues in a follow-up commit.

Original reason: $reason"

echo ""
echo "✅ Emergency commit completed"
echo "⚠️  Remember to address quality issues in your next commit!"
echo "⚠️  Run 'npm run quality:dashboard' to see current issues"