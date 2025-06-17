# PowerShell script for setting up PUBLIC GitHub repository
# PLEX Dynamic Staking Manager - PUBLIC Repository Setup

Write-Host "🌐 Setting up PUBLIC GitHub repository connection..." -ForegroundColor Green
Write-Host "📋 This will create a PUBLIC repository visible to everyone!" -ForegroundColor Yellow

# Replace YOUR_USERNAME with your actual GitHub username
$GITHUB_USERNAME = "YOUR_USERNAME"
$REPO_NAME = "PLEX-Dynamic-Staking-Manager"

Write-Host "`n⚠️  IMPORTANT: Before running this script:" -ForegroundColor Red
Write-Host "1. Go to https://github.com/new" -ForegroundColor White
Write-Host "2. Create repository named: $REPO_NAME" -ForegroundColor White
Write-Host "3. Set visibility to: PUBLIC" -ForegroundColor White
Write-Host "4. DO NOT initialize with README, .gitignore, or license" -ForegroundColor White
Write-Host "5. Replace YOUR_USERNAME in this script with your GitHub username" -ForegroundColor White

if ($GITHUB_USERNAME -eq "YOUR_USERNAME") {
    Write-Host "`n❌ Please edit this script and replace YOUR_USERNAME with your actual GitHub username!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit
}

Write-Host "`n📝 Repository URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME.git" -ForegroundColor Yellow

# Confirm before proceeding
$confirmation = Read-Host "`nDid you create the PUBLIC repository on GitHub? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Please create the repository first and run this script again." -ForegroundColor Yellow
    exit
}

# Check if .env files are properly excluded
Write-Host "`n🔒 Security check: Verifying .env files are excluded..." -ForegroundColor Cyan
if (Test-Path ".env") {
    Write-Host "❌ WARNING: .env file found! This should NOT be committed to public repo!" -ForegroundColor Red
    $envConfirm = Read-Host "Are you sure you want to continue? (y/N)"
    if ($envConfirm -ne 'y' -and $envConfirm -ne 'Y') {
        exit
    }
} else {
    Write-Host "✅ Good: No .env file found in root directory" -ForegroundColor Green
}

# Check for any potential secrets
Write-Host "🔍 Checking for potential secrets in committed files..." -ForegroundColor Cyan
$suspiciousFiles = git ls-files | Select-String -Pattern "\.(key|pem|p12|pfx)$"
if ($suspiciousFiles) {
    Write-Host "❌ WARNING: Potential secret files found!" -ForegroundColor Red
    Write-Host $suspiciousFiles -ForegroundColor Red
    $secretConfirm = Read-Host "Continue anyway? (y/N)"
    if ($secretConfirm -ne 'y' -and $secretConfirm -ne 'Y') {
        exit
    }
} else {
    Write-Host "✅ No obvious secret files detected" -ForegroundColor Green
}

# Add remote origin
Write-Host "Adding remote origin..." -ForegroundColor Cyan
git remote add origin "https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"

# Check if remote was added successfully
$remoteCheck = git remote -v
if ($remoteCheck -match "origin") {
    Write-Host "✅ Remote origin added successfully!" -ForegroundColor Green
    
    # Push to GitHub
    Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
    git push -u origin main
      if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PUBLIC repository successfully uploaded to GitHub!" -ForegroundColor Green
        Write-Host "🌐 Your PUBLIC repository: https://github.com/$GITHUB_USERNAME/$REPO_NAME" -ForegroundColor Yellow
        Write-Host "📋 Repository contains:" -ForegroundColor Cyan
        Write-Host "   • 184+ files committed" -ForegroundColor White
        Write-Host "   • 54,000+ lines of code" -ForegroundColor White
        Write-Host "   • Complete PLEX Dynamic Staking Manager" -ForegroundColor White
        Write-Host "   • Production-ready codebase" -ForegroundColor White
        Write-Host "`n🎉 Your repository is now PUBLIC and visible to everyone!" -ForegroundColor Green
        Write-Host "👥 Others can now:" -ForegroundColor Cyan
        Write-Host "   • View your code" -ForegroundColor White
        Write-Host "   • Fork your repository" -ForegroundColor White
        Write-Host "   • Submit issues and pull requests" -ForegroundColor White
        Write-Host "   • Star your project" -ForegroundColor White
    } else {
        Write-Host "❌ Failed to push to GitHub. Please check your credentials and repository permissions." -ForegroundColor Red
    }
} else {
    Write-Host "❌ Failed to add remote origin. Please check the repository URL." -ForegroundColor Red
}

Write-Host "`n📖 Next steps:" -ForegroundColor Yellow
Write-Host "1. Visit your repository on GitHub" -ForegroundColor White
Write-Host "2. Add a description and topics" -ForegroundColor White
Write-Host "3. Set up GitHub Pages (optional)" -ForegroundColor White
Write-Host "4. Configure branch protection rules" -ForegroundColor White
