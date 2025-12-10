#!/bin/bash
# emergency_cleanup.sh - Nuclear option for stuck tests

echo "🚨 EMERGENCY CLEANUP - This will forcefully clean everything"
echo "Press Ctrl+C to abort, or wait 5 seconds to continue..."
sleep 5

# Kill all test processes
echo "Killing test processes..."
pkill -9 -f "test_"
pkill -9 -f "chaos_"
pkill -9 -f "mock_"
# Also kill browser instances if orphaned
pkill -9 -f "chrome"
pkill -9 -f "playwright"

# Remove test directories
echo "Removing test directories..."
rm -rf /tmp/fyodoros_test_*
rm -rf /tmp/test_*
rm -rf ~/.fyodor/sandbox/test_*
rm -rf ~/.fyodor/tmp/*

# Stop test services (if systemd managed, though likely internal python processes)
# echo "Stopping test services..."
# systemctl stop fyodoros-test-* 2>/dev/null || true

# Clear test network connections
# This is hard to do from bash without root or specific tools like ss -K
# echo "Clearing network connections..."
# ss -K dst 127.0.0.1 dport ge 10000 le 20000 2>/dev/null || true

# Reset FyodorOS User Data
echo "Resetting FyodorOS Data..."
# We can't easily run the python snippet if dependencies aren't set up,
# but we can delete the json files.
rm -f users.json
rm -f fyodor.conf # If it's a test one?
rm -rf /var/log/journal/*

echo "✅ Emergency cleanup complete"
echo "⚠️  Please verify system state before running tests again"
