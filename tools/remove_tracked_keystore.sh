#!/bin/sh
# Helper: remove inzighted-twa/android.keystore from the git repo history
# WARNING: Rewriting history will change commit hashes. Coordinate with your team.

echo "This script shows commands to remove inzighted-twa/android.keystore from all commits."

echo "1) Ensure your working tree is clean and you have a backup."

echo "2) To remove the file from future commits and history using BFG (recommended):"
cat <<'BFG'
# Install BFG: https://rtyley.github.io/bfg-repo-cleaner/
# Create a mirror clone:
git clone --mirror <repo-url> repo.git
cd repo.git
# Use BFG to delete the file path:
java -jar bfg.jar --delete-files inzighted-twa/android.keystore
# Cleanup and push
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push
BFG

echo "3) Or use git filter-branch (slower):"
cat <<'FILTER'
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch inzighted-twa/android.keystore" \
  --prune-empty --tag-name-filter cat -- --all
# Then push forced
git push origin --force --all
FILTER

echo "After history rewrite, rotate any secrets that might have been in the keystore." 
