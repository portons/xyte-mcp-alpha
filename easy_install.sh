#!/bin/bash
# Easy installer for Xyte MCP

echo "🚀 Setting up Xyte MCP for Claude Desktop..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# Install dependencies
echo "📚 Installing dependencies..."
uv sync

# Get current directory
CURRENT_DIR=$(pwd)

# Create Claude config
echo "⚙️  Configuring Claude Desktop..."
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
mkdir -p "$CLAUDE_CONFIG_DIR"

cat > "$CLAUDE_CONFIG_DIR/claude_desktop_config.json" << EOF
{
  "mcpServers": {
    "xyte": {
      "command": "uv",
      "args": [
        "--directory",
        "$CURRENT_DIR",
        "run",
        "xyte-mcp"
      ],
      "env": {
        "XYTE_API_KEY": "XYTE_API_KEY"
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
echo "🎉 That's it! You're ready to use Xyte with Claude."