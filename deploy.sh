#!/bin/bash

echo "🚀 FPL Dashboard Deployment Script"
echo "=================================="

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing git repository..."
    git init
fi

# Add all files
echo "📦 Adding files to git..."
git add .

# Commit changes
echo "💾 Committing changes..."
git commit -m "Deploy FPL Dashboard to production"

echo ""
echo "🌐 Choose your deployment platform:"
echo "1) Heroku (Recommended)"
echo "2) Railway"
echo "3) Render"
echo "4) Manual deployment"

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🔧 Heroku Deployment"
        echo "==================="
        echo "1. Install Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli"
        echo "2. Run: heroku login"
        echo "3. Run: heroku create your-app-name"
        echo "4. Run: git push heroku main"
        echo ""
        echo "Your app will be available at: https://your-app-name.herokuapp.com"
        ;;
    2)
        echo ""
        echo "🚂 Railway Deployment"
        echo "==================="
        echo "1. Go to https://railway.app"
        echo "2. Connect your GitHub account"
        echo "3. Push this code to a GitHub repository"
        echo "4. Deploy from GitHub on Railway"
        ;;
    3)
        echo ""
        echo "🎨 Render Deployment"
        echo "==================="
        echo "1. Go to https://render.com"
        echo "2. Create a new Web Service"
        echo "3. Connect your GitHub repository"
        echo "4. Set build command: pip install -r requirements.txt"
        echo "5. Set start command: python fpl_proxy.py"
        ;;
    4)
        echo ""
        echo "📋 Manual Deployment Files Ready"
        echo "==============================="
        echo "Files created for deployment:"
        echo "- requirements.txt"
        echo "- Procfile"
        echo "- Updated fpl_proxy.py"
        echo ""
        echo "Follow the deployment_guide.md for detailed instructions."
        ;;
    *)
        echo "Invalid choice. Please run the script again."
        ;;
esac

echo ""
echo "✅ Deployment preparation complete!"
echo "📖 Check deployment_guide.md for detailed instructions"
