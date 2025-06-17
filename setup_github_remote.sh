#!/bin/bash
# GitHub Remote Setup Commands for PLEX Dynamic Staking Manager

echo "🔗 Setting up GitHub remote connection..."

# Replace YOUR_USERNAME with your actual GitHub username
GITHUB_USERNAME="YOUR_USERNAME"
REPO_NAME="PLEX-Dynamic-Staking-Manager"

echo "📝 Repository URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"

# Add remote origin
echo "Adding remote origin..."
git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin main

echo "✅ Repository successfully uploaded to GitHub!"
echo "🌐 Repository URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
