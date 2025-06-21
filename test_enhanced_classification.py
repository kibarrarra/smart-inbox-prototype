#!/usr/bin/env python3
"""Test the enhanced 4-tier classification system"""

import sys
import os
sys.path.append('src')

from src.main import score_importance

# Test emails for all four tiers
test_emails = [
    {
        "subject": "MARGIN CALL - Immediate Action Required",
        "snippet": "Your account has fallen below required margin levels. Please deposit $50K within 24 hours or positions will be liquidated.",
        "expected_tier": "Critical (0.8+)"
    },
    {
        "subject": "Client Meeting Request - Tomorrow 2PM",
        "snippet": "Hi, can we meet tomorrow at 2PM to discuss the Q3 portfolio performance? This is regarding the $2M allocation.",
        "expected_tier": "Urgent (0.5+)"
    },
    {
        "subject": "Weekly Market Report - Attached",
        "snippet": "Please find attached the weekly market report with sector analysis and recommendations for your review.",
        "expected_tier": "Medium (0.4+)"
    },
    {
        "subject": "LinkedIn: John Smith wants to connect",
        "snippet": "John Smith would like to add you to their professional network on LinkedIn. View profile and respond.",
        "expected_tier": "Digest (<0.4)"
    },
    {
        "subject": "TRADE EXECUTION FAILED - TSLA Position",
        "snippet": "Your buy order for 1000 shares of TSLA at $180 failed due to insufficient buying power. Please review your account.",
        "expected_tier": "Critical (0.8+)"
    },
    {
        "subject": "Quarterly earnings webinar invitation",
        "snippet": "You're invited to our Q3 earnings webinar next Wednesday at 10 AM. Register now to secure your spot.",
        "expected_tier": "Medium (0.4+)"
    }
]

def get_tier_name(score):
    if score >= 0.8:
        return "Critical", "AI/Critical"
    elif score >= 0.5:
        return "Urgent", "AI/Urgent"
    elif score >= 0.4:
        return "Medium", "AI/Medium"
    else:
        return "Digest", "AI/DigestQueue"

print("Testing Enhanced 4-Tier Email Classification")
print("=" * 60)

correct = 0
total = len(test_emails)

for i, email in enumerate(test_emails, 1):
    print(f"\nTest {i}: {email['subject'][:45]}...")
    print(f"Expected: {email['expected_tier']}")
    
    try:
        score = score_importance(email['subject'], email['snippet'])
        tier_name, label = get_tier_name(score)
        
        print(f"Score: {score:.2f} -> {tier_name} ({label})")
        
        # Check if tier matches expectation (rough match)
        expected_score_range = email['expected_tier'].split('(')[1].split(')')[0]
        if "0.8+" in expected_score_range:
            correct_prediction = score >= 0.8
        elif "0.5+" in expected_score_range:
            correct_prediction = 0.5 <= score < 0.8
        elif "0.4+" in expected_score_range:
            correct_prediction = 0.4 <= score < 0.5
        else:  # "<0.4"
            correct_prediction = score < 0.4
            
        if correct_prediction:
            correct += 1
            print("Result: ✓ CORRECT")
        else:
            print("Result: ✗ INCORRECT")
        
    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 60)
print(f"Enhanced Classification Results: {correct}/{total} correct ({100*correct/total:.1f}%)")
print("Four-tier system provides nuanced email prioritization!")