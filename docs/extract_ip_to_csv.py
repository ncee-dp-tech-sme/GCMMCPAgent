#!/usr/bin/env python3
"""
Extract ip_str values from JSON lines file and save to CSV.
Created: 2026-06-08
"""

import json
import csv
import sys
from pathlib import Path


def extract_ip_to_csv(input_file: str, output_file: str = "ip_addresses.csv") -> None:
    """
    Extract ip_str values from JSON lines file and save to CSV.
    
    Args:
        input_file: Path to input JSON lines file
        output_file: Path to output CSV file (default: ip_addresses.csv)
    """
    ip_addresses = []
    line_count = 0
    error_count = 0
    
    print(f"Reading from: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                line_count += 1
                try:
                    data = json.loads(line)
                    if 'ip_str' in data:
                        ip_addresses.append(data['ip_str'])
                    else:
                        print(f"Warning: Line {line_num} missing 'ip_str' field")
                        error_count += 1
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
                    error_count += 1
    
    except FileNotFoundError:
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    # Write to CSV
    print(f"\nWriting {len(ip_addresses)} IP addresses to: {output_file}")
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ip_str'])  # Header
            for ip in ip_addresses:
                writer.writerow([ip])
        
        print(f"\nSuccess!")
        print(f"- Total lines processed: {line_count}")
        print(f"- IP addresses extracted: {len(ip_addresses)}")
        print(f"- Errors encountered: {error_count}")
        print(f"- Output file: {output_file}")
        
    except Exception as e:
        print(f"Error writing CSV file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_ip_to_csv.py <input_json_file> [output_csv_file]")
        print("\nExample:")
        print("  python extract_ip_to_csv.py data.json")
        print("  python extract_ip_to_csv.py data.json output.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "ip_addresses.csv"
    
    extract_ip_to_csv(input_file, output_file)

# Made with Bob
