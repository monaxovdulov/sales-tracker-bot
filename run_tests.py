#!/usr/bin/env python3
"""
Simple test runner for the Telegram bot unit tests
"""

import sys
import os
import unittest

# Add the bot directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

if __name__ == '__main__':
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1) 