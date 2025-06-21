#!/usr/bin/env python3
"""Quick test of the email classification logic"""

import sys
import os
sys.path.append('src')

from src.main import score_importance

# Test emails with different importance levels
test_emails = [
    {
        "subject": "URGENT: Server Down - Production Issue",
        "snippet": "Our main production server is down and customers cannot access the platform. This is affecting revenue and we need immediate action.",
        "expected": "high"
    },
    {
        "subject": "Weekly Newsletter - Market Updates",
        "snippet": "Here's your weekly newsletter with market updates and interesting articles from around the web.",
        "expected": "low"
    },
    {
        "subject": "Trade Execution Failed - $500K Position",
        "snippet": "Your trade execution for AAPL $500K position has failed due to insufficient liquidity. Please review and resubmit.",
        "expected": "high"
    },
    {
        "subject": "LinkedIn connection request",
        "snippet": "John Smith would like to connect with you on LinkedIn. View profile and accept connection.",
        "expected": "low"
    },
    {
        "subject": "Margin Call - Immediate Action Required",
        "snippet": "Your account has fallen below required margin levels. Please deposit funds or close positions within 24 hours.",
        "expected": "high"
    },
    {
        "subject": "Company picnic next Friday",
        "snippet": "Don't forget about our company picnic next Friday at Central Park. Bring your family and enjoy the fun activities.",
        "expected": "low"
    }
]

print("Testing Email Classification System")
print("=" * 50)

for i, email in enumerate(test_emails, 1):
    print(f"\nTest {i}: {email['subject'][:50]}...")
    print(f"Expected: {email['expected']} importance")
    
    try:
        score = score_importance(email['subject'], email['snippet'])
        importance_level = "high" if score >= 0.5 else "low"
        
        print(f"Score: {score:.2f} -> {importance_level} importance")
        
        # Check if prediction matches expectation
        correct = importance_level == email['expected']
        print(f"Result: {'✓ CORRECT' if correct else '✗ INCORRECT'}")
        
    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 50)
print("Classification test complete!")