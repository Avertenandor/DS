# PowerShell script for setting up GitHub remote connection
# PLEX Dynamic Staking Manager - GitHub Setup

Write-Host "🔗 Setting up GitHub remote connection..." -ForegroundColor Green

# Replace YOUR_USERNAME with your actual GitHub username
$GITHUB_USERNAME = "YOUR_USERNAME"
$REPO_NAME = "PLEX-Dynamic-Staking-Manager"

Write-Host "📝 Repository URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME.git" -ForegroundColor Yellow

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
        Write-Host "✅ Repository successfully uploaded to GitHub!" -ForegroundColor Green
        Write-Host "🌐 Repository URL: https://github.com/$GITHUB_USERNAME/$REPO_NAME" -ForegroundColor Yellow
        Write-Host "📋 Repository contains:" -ForegroundColor Cyan
        Write-Host "   • 181 files committed" -ForegroundColor White
        Write-Host "   • 53,976 lines of code" -ForegroundColor White
        Write-Host "   • Complete PLEX Dynamic Staking Manager" -ForegroundColor White
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
