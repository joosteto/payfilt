#!/usr/bin/env python3
"""payfilt - A commandline tool to filter and analyze payment data from .TAB files.



./payfilt.py ../dagboek/bank/Joost-Prive-TXT261026081154.TAB --merchant 'Public Food' --wlist

"""

import argparse
import csv
import re
import sys
from datetime import datetime
from collections import defaultdict

def parse_tab_file(filepath):
    """Parse a .TAB file and extract payment records."""
    payments = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')

        for row in reader:
            if len(row) < 8:
                continue

            # Extract fields
            account = row[0].strip()
            currency = row[1].strip()
            date_str = row[2].strip()
            amount_str = row[6].strip()
            # The rest of the row (from index 7 onwards) is the description
            description = '\t'.join(row[7:]).strip()

            # Parse date (format: YYYYMMDD or YYYYMMDD_HH:MM)
            try:
                if '_' in date_str:
                    date_part, time_part = date_str.split('_')
                    date_time = datetime.strptime(f"{date_part}_{time_part}", "%Y%m%d_%H:%M")
                else:
                    date_time = datetime.strptime(date_str, "%Y%m%d")
            except ValueError:
                date_time = None

            # For Betaalpas transactions, extract time from NR: field
            # Example: "NR:CT950714, 01.09.25/20:51" -> extract "20:51"
            if 'Betaalpas' in description:
                nr_match = re.search(r'NR:\w*,\s*(\d{2}\.\d{2}\.\d{2})/(\d{2}:\d{2})', description)
                if nr_match:
                    # Parse the date and time from NR field
                    nr_date = datetime.strptime(nr_match.group(1), "%d.%m.%y")
                    time_str = nr_match.group(2)
                    # Combine with the main date (use NR date if it matches, otherwise use main date)
                    if date_time:
                        # Replace time in date_time with the extracted time
                        date_time = datetime.combine(date_time.date(), datetime.strptime(time_str, "%H:%M").time())

            # Parse amount (format: -123.45 or 123,45)
            try:
                amount = float(amount_str.replace(',', '.'))
            except ValueError:
                amount = 0.0

            # Extract transaction type from description
            transaction_type = extract_transaction_type(description)

            # Extract merchant from description
            merchant = extract_merchant(description)

            # Extract town from description (appears at the end)
            town = extract_town(description)

            payments.append({
                'account': account,
                'currency': currency,
                'date': date_time,
                'date_str': date_str,
                'amount': amount,
                'amount_str': amount_str,
                'type': transaction_type,
                'description': description,
                'merchant': merchant,
                'town': town
            })

    return payments

def extract_transaction_type(description):
    """Extract transaction type from description."""
    if description.startswith('SEPA'):
        return 'SEPA Incasso'
    elif 'BEA,' in description or description.startswith('BEA'):
        return 'BEA'
    elif 'Betaalpas' in description:
        return 'Betaalpas'
    return description.split(',')[0].strip()

def extract_merchant(description):
    """Extract merchant name from description."""
    # Pattern 1: "Naam: MERCHANT" - this is the most reliable
    # Match "Naam: " followed by any characters until we hit a known delimiter
    naam_match = re.search(r'Naam:\s*([A-Za-z\s\-]+?)(?:\s+(?:Machtiging:|Omschrijving:|IBAN:|Kenmerk:)|,|$)', description)
    if naam_match:
        merchant = naam_match.group(1).strip()
        merchant = re.sub(r'[,\s]+$', '', merchant)
        return merchant

    # Pattern 2: Look for known merchant names in the description
    merchant_keywords = ['Albert Heijn', 'Public Food', 'hollandsnieuwe', 'INTERTOYS', 'SumUp', 'IK KIES ZELF VAN ASR']
    for keyword in merchant_keywords:
        if keyword in description:
            return keyword

    # Pattern 3: Merchant name after transaction type for Betaalpas
    if 'Betaalpas' in description:
        parts = description.split('Betaalpas')
        if len(parts) > 1:
            rest = parts[1].strip()
            rest = re.sub(r'PAS\d+', '', rest)
            rest = re.sub(r'NR:\w+', '', rest)
            rest = re.sub(r'KAARTNUMMER:\*+\d*', '', rest)
            rest = rest.strip().strip(',')
            if rest:
                merchant_parts = [p.strip() for p in re.split(r'[,\t]', rest) if p.strip()]
                if merchant_parts:
                    merchant = merchant_parts[0]
                    merchant = re.sub(r'[,\s]+$', '', merchant)
                    return merchant

    # Pattern 4: Look for merchant before known delimiters
    delimiters = ['NR:', 'KAARTNUMMER:', 'Machtiging:', 'IBAN:', 'Omschrijving:', 'Kenmerk:']
    for delimiter in delimiters:
        if delimiter in description:
            merchant_part = description.split(delimiter)[0].strip()
            for prefix in ['SEPA Incasso algemeen doorlopend Incassant:', 'SEPA Incasso', 'BEA, Betaalpas', 'BEA', 'Betaalpas']:
                merchant_part = merchant_part.replace(prefix, '').strip()
            merchant_part = merchant_part.strip().strip(',')
            if merchant_part:
                return merchant_part

    return "Unknown"

def extract_town(description):
    """Extract town from description (usually at the end)."""
    known_towns = ['ZAANDAM', 'Rotterdam', "'S-GRAVENHAGE", 'S-GRAVENHAGE', 'Amsterdam', 'Utrecht',
                   'Eindhoven', 'Groningen', 'Tilburg', 'Almere', 'Breda', 'Nijmegen',
                   'Enschede', 'Haarlem', 'Arnhem', 'Leiden', 'Dordrecht', 'Delft',
                   'Ede', 'Apeldoorn', 'Assen', 'Emmen', 'Hengelo', 'Hilversum']

    for town in known_towns:
        if town.lower() in description.lower():
            return town

    return ""

def format_date(payment):
    """Format date as YYYYMMDD or YYYYMMDD_HH:MM."""
    if payment['date']:
        if payment['date'].hour > 0 or payment['date'].minute > 0:
            return payment['date'].strftime("%Y%m%d_%H:%M")
        else:
            return payment['date'].strftime("%Y%m%d")
    return payment['date_str']

def format_date_wlist(payment):
    """Format date with weeknumber and weekday for --wlist option.
    Format: YYYYMMDD(WW.D) or YYYYMMDD(WW.D)_HH:MM
    where WW = ISO week number, D = ISO weekday (1=Monday, 7=Sunday)
    """
    if payment['date']:
        year, week, weekday = payment['date'].isocalendar()
        base_date = payment['date'].strftime("%Y%m%d")
        if payment['date'].hour > 0 or payment['date'].minute > 0:
            return f"{base_date}({week}.{weekday})_{payment['date'].strftime('%H:%M')}"
        else:
            return f"{base_date}({week}.{weekday})"
    return payment['date_str']

def main():
    parser = argparse.ArgumentParser(
        description='Filter and analyze payment data from .TAB files'
    )
    parser.add_argument(
        'file',
        nargs='?',
        default='doc/example.TAB',
        help='Path to .TAB file (default: doc/example.TAB)'
    )
    parser.add_argument(
        '--merchant',
        type=str,
        default=None,
        help='Filter by merchant name(s), separated by | (e.g., "Public Food|Albert Heijn")'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='Show payments in list format'
    )
    parser.add_argument(
        '--wlist',
        action='store_true',
        help='Show payments in list format with weeknumber and weekday'
    )
    parser.add_argument(
        '--daylist',
        action='store_true',
        help='List days where payments were made'
    )
    parser.add_argument(
        '--weekdaycount',
        action='store_true',
        help='Count number of days per week'
    )

    args = parser.parse_args()

    # Parse the file
    try:
        payments = parse_tab_file(args.file)
    except FileNotFoundError:
        print(f"Error: File '{args.file}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # Filter by merchant if specified
    if args.merchant:
        merchant_patterns = args.merchant.split('|')
        filtered_payments = []
        for payment in payments:
            for pattern in merchant_patterns:
                if pattern.strip() in payment['merchant']:
                    filtered_payments.append(payment)
                    break
        payments = filtered_payments

    # Handle output based on options
    if args.list:
        print(f"{'Date_time':<18} {'Town':<12} {'name':<20} {'amount':>10}")
        print("-" * 60)
        for p in payments:
            date = format_date(p)
            town = p['town']
            merchant = p['merchant']
            amount = f"{p['amount']:.2f}"
            print(f"{date:<18} {town:<12} {merchant:<20} {amount:>10}")

    elif args.wlist:
        print(f"{'Date_time':<25} {'Town':<12} {'name':<20} {'amount':>10}")
        print("-" * 65)
        for p in payments:
            date = format_date_wlist(p)
            town = p['town']
            merchant = p['merchant']
            amount = f"{p['amount']:.2f}"
            print(f"{date:<25} {town:<12} {merchant:<20} {amount:>10}")

    elif args.daylist:
        days = set()
        for p in payments:
            if p['date']:
                days.add(p['date'].strftime("%Y%m%d"))
        for day in sorted(days):
            print(day)

    elif args.weekdaycount:
        week_days = defaultdict(set)
        for p in payments:
            if p['date']:
                year, week, _ = p['date'].isocalendar()
                week_key = f"{year}.{week:02d}"
                week_days[week_key].add(p['date'].strftime("%Y%m%d"))
        for week, days in sorted(week_days.items()):
            print(f"{week}, {len(days)}")

    else:
        print(f"Found {len(payments)} payment(s)")
        print(f"{'Date':<12} {'Merchant':<25} {'Town':<12} {'Amount':>10}")
        print("-" * 60)
        for p in payments:
            date = format_date(p)
            merchant = p['merchant']
            town = p['town']
            amount = f"{p['amount']:.2f}"
            print(f"{date:<12} {merchant:<25} {town:<12} {amount:>10}")

if __name__ == '__main__':
    main()
