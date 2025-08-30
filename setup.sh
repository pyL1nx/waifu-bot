#!/bin/bash

echo "🌸 Setting up Waifu Bot..."

# Install dependencies
pip install -r requirements.txt

# Create environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Please edit .env file with your API keys"
fi

echo "✅ Setup complete!"
echo "🚀 Run with: python waifu_bot.py"
