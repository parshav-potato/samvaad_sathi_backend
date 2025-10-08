#!/bin/bash
# Restart Python Language Server Script

echo "🔄 Restarting Python Language Server..."
echo "======================================"

echo "1. The symbolic links have been created to help IDE detection:"
echo "   - ./venv/bin/python3.13 -> /home/parshav-potato/.venv/bin/python"
echo "   - ./venv/bin/python -> /home/parshav-potato/.venv/bin/python"

echo ""
echo "2. VS Code/Cursor settings updated:"
echo "   - Python interpreter: /home/parshav-potato/.venv/bin/python"
echo "   - Linting tools configured (black, isort, mypy)"
echo "   - Test discovery configured for pytest"

echo ""
echo "3. To restart the Python language server in Cursor/VS Code:"
echo "   - Press Ctrl+Shift+P (or Cmd+Shift+P on Mac)"
echo "   - Type 'Python: Restart Language Server'"
echo "   - Press Enter"

echo ""
echo "4. Alternative: Reload the window:"
echo "   - Press Ctrl+Shift+P (or Cmd+Shift+P on Mac)"
echo "   - Type 'Developer: Reload Window'"
echo "   - Press Enter"

echo ""
echo "5. Verify the setup is working:"
echo "   - Check the bottom status bar for Python version"
echo "   - Try opening a Python file and check for linting"
echo "   - Run tests using the Test Explorer"

echo ""
echo "✅ Setup complete! The IDE should now properly detect the UV virtual environment."
