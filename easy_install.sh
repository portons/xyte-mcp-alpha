#!/bin/bash
# Easy installer for Xyte MCP

echo "🚀 Setting up Xyte MCP for Claude Desktop..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 uv package manager not found. Installing..."
    
    # Check if homebrew is available (preferred method)
    if command -v brew &> /dev/null; then
        echo "🍺 Installing uv via Homebrew..."
        brew install uv
    else
        echo "📥 Installing uv via installer script..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add uv to PATH for this script
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi

# Get the full path to uv
UV_PATH=$(which uv)

# Install dependencies
echo "📚 Installing dependencies..."
uv sync

# Get current directory
CURRENT_DIR=$(pwd)

# Check if API key is provided as argument, otherwise prompt
if [ -z "$1" ]; then
    echo ""
    echo "🔑 Enter your Xyte API key:"
    read -r API_KEY
    if [ -z "$API_KEY" ]; then
        echo "❌ API key is required. Please run again and provide your API key."
        exit 1
    fi
else
    API_KEY="$1"
fi

# Create Claude config
echo "⚙️  Configuring Claude Desktop..."
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
mkdir -p "$CLAUDE_CONFIG_DIR"

cat > "$CLAUDE_CONFIG_DIR/claude_desktop_config.json" << EOF
{
  "mcpServers": {
    "xyte": {
      "command": "$UV_PATH",
      "args": [
        "--directory",
        "$CURRENT_DIR",
        "run",
        "xyte-mcp"
      ],
      "env": {
        "XYTE_API_KEY": "$API_KEY"
      }
    }
  }
}
EOF

echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Restart Claude Desktop"
echo "2. In Claude, type: 'List all my Xyte devices'"
echo ""
echo "🔐 Your API key has been securely saved to Claude's config"
echo "🎉 That's it! You're ready to use Xyte with Claude."