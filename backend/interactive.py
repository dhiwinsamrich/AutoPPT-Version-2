#!/usr/bin/env python3
"""
PPT Automation - Interactive Mode Launcher
Simple launcher script for the interactive mode
"""
import sys
import os

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

if __name__ == "__main__":
    from interactive_mode import InteractiveMode
    interactive = InteractiveMode()
    exit(interactive.run())

