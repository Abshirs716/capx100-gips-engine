"""
GIPS Transaction Parser
=======================
Parse Schwab CSV exports for GIPS compliance calculations.

Handles:
- Position data (for current valuations)
- Transaction history (for TWR calculations)
- End-of-period valuations (monthly/quarterly)
"""

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

from .models import (
    Account, Transaction, Valuation, TransactionType, Household
)


@dataclass
class ParseResult:
    """Result of parsing a CSV file."""
    account: Account
    transactions: List[Transaction]
    valuations: List[Valuation]
    positions: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    @property
    def has_transaction_history(self) -> bool:
        return len(self.transactions) > 0

    @property
    def date_range(self) -> Optional[Tuple[date, date]]:
        """Get date range of transactions."""
        if not self.transactions:
            return None
        dates = [t.date for t in self.transactions]
        return (min(dates), max(dates))

    @property
    def summary(self) -> Dict[str, Any]:
        """Summary of parsed data."""
        return {
            'account_id': self.account.account_id,
            'account_name': self.account.account_name,
            'num_transactions': len(self.transactions),
            'num_valuations': len(self.valuations),
            'num_positions': len(self.positions),
            'date_range': self.date_range,
            'errors': len(self.errors),
            'warnings': len(self.warnings),
        }


class GIPSTransactionParser:
    """
    Parse Schwab CSV exports for GIPS calculations.

    CSV Format Expected:
    - Header section with account info
    - === POSITIONS === section
    - === TRANSACTION HISTORY === section
    """

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse_file(self, file_path: str) -> ParseResult:
        """Parse a Schwab CSV export file."""
        self.errors = []
        self.warnings = []

        path = Path(file_path)
        if not path.exists():
            self.errors.append(f"File not found: {file_path}")
            return self._empty_result()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.errors.append(f"Error reading file: {e}")
            return self._empty_result()

        return self._parse_content(content, file_path)

    def parse_content(self, content: str) -> ParseResult:
        """Parse CSV content string."""
        self.errors = []
        self.warnings = []
        return self._parse_content(content, "uploaded_content")

    def _parse_content(self, content: str, source: str) -> ParseResult:
        """Internal parsing logic."""
        lines = content.split('\n')

        # Extract account info from header
        account_info = self._parse_header(lines)

        # Find sections
        positions_start = None
        transactions_start = None

        for i, line in enumerate(lines):
            if '=== POSITIONS ===' in line or line.strip() == 'POSITIONS':
                positions_start = i + 1
            elif '=== TRANSACTION HISTORY ===' in line or 'TRANSACTION HISTORY' in line:
                transactions_start = i + 1

        # Parse positions
        positions = []
        if positions_start is not None:
            positions = self._parse_positions(lines, positions_start, transactions_start)

        # Parse transactions
        transactions = []
        if transactions_start is not None:
            transactions = self._parse_transactions(lines, transactions_start)

        # Generate valuations from End Value transactions and positions
        valuations = self._generate_valuations(transactions, positions, account_info.get('account_id', ''))

        # Create account object
        account = self._create_account(account_info, positions)
        account.transactions = transactions
        account.valuations = valuations

        return ParseResult(
            account=account,
            transactions=transactions,
            valuations=valuations,
            positions=positions,
            errors=self.errors,
            warnings=self.warnings,
        )

    def _parse_header(self, lines: List[str]) -> Dict[str, str]:
        """Extract account info from header section."""
        info = {
            'account_name': 'Unknown Account',
            'account_id': 'UNKNOWN',
        }

        for line in lines[:20]:  # Header is usually in first 20 lines
            if 'Account Name:' in line:
                info['account_name'] = line.split(':', 1)[1].strip()
            elif 'Account Number:' in line:
                info['account_id'] = line.split(':', 1)[1].strip()
            elif 'Report Generated:' in line:
                info['report_date'] = line.split(':', 1)[1].strip()

        return info

    def _parse_positions(
        self,
        lines: List[str],
        start_idx: int,
        end_idx: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Parse positions section."""
        positions = []

        if end_idx is None:
            end_idx = len(lines)

        # Find header row
        header_idx = None
        for i in range(start_idx, min(start_idx + 5, end_idx)):
            if i < len(lines) and 'Symbol' in lines[i] and 'Market Value' in lines[i]:
                header_idx = i
                break

        if header_idx is None:
            self.warnings.append("Could not find position header row")
            return positions

        # Parse header
        header_line = lines[header_idx]
        headers = self._parse_csv_row(header_line)

        # Map header names to indices
        header_map = {h.strip().lower(): i for i, h in enumerate(headers)}

        # Parse data rows
        for i in range(header_idx + 1, end_idx):
            if i >= len(lines):
                break

            line = lines[i].strip()
            if not line or line.startswith('===') or line.startswith('---'):
                break

            try:
                values = self._parse_csv_row(line)
                if len(values) < 5:
                    continue

                position = {
                    'symbol': self._get_field(values, header_map, 'symbol', ''),
                    'description': self._get_field(values, header_map, 'description', ''),
                    'cusip': self._get_field(values, header_map, 'cusip', ''),
                    'quantity': self._parse_decimal(self._get_field(values, header_map, 'quantity', '0')),
                    'price': self._parse_decimal(self._get_field(values, header_map, 'price', '0')),
                    'market_value': self._parse_decimal(self._get_field(values, header_map, 'market value', '0')),
                    'cost_basis': self._parse_decimal(self._get_field(values, header_map, 'cost basis', '0')),
                    'unrealized_gl': self._parse_decimal(self._get_field(values, header_map, 'unrealized g/l', '0')),
                    'asset_class': self._get_field(values, header_map, 'asset class', ''),
                    'sector': self._get_field(values, header_map, 'sector', ''),
                    'duration': self._parse_decimal(self._get_field(values, header_map, 'duration', '')),
                    'convexity': self._parse_decimal(self._get_field(values, header_map, 'convexity', '')),
                }

                if position['symbol']:
                    positions.append(position)

            except Exception as e:
                self.warnings.append(f"Error parsing position row {i}: {e}")

        return positions

    def _parse_transactions(self, lines: List[str], start_idx: int) -> List[Transaction]:
        """Parse transaction history section."""
        transactions = []

        # Find header row
        header_idx = None
        for i in range(start_idx, min(start_idx + 5, len(lines))):
            line = lines[i] if i < len(lines) else ''
            if 'Trade Date' in line or 'Date' in line:
                header_idx = i
                break

        if header_idx is None:
            self.warnings.append("Could not find transaction header row")
            return transactions

        # Parse header
        headers = self._parse_csv_row(lines[header_idx])
        header_map = {h.strip().lower(): i for i, h in enumerate(headers)}

        # Parse data rows
        for i in range(header_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line or line.startswith('===') or line.startswith('---'):
                continue

            # Check if line starts with a date (MM/DD/YYYY)
            if not re.match(r'^\d{2}/\d{2}/\d{4}', line):
                continue

            try:
                values = self._parse_csv_row(line)
                if len(values) < 6:
                    continue

                # Parse date
                date_str = self._get_field(values, header_map, 'trade date', '')
                if not date_str:
                    date_str = values[0] if values else ''

                try:
                    trans_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                except ValueError:
                    self.warnings.append(f"Invalid date format: {date_str}")
                    continue

                # Parse action/type
                action = self._get_field(values, header_map, 'action', '')
                trans_type = TransactionType.from_string(action)

                # Parse amounts
                symbol = self._get_field(values, header_map, 'symbol', '')
                description = self._get_field(values, header_map, 'description', '')
                quantity = self._parse_decimal(self._get_field(values, header_map, 'quantity', '0'))
                price = self._parse_decimal(self._get_field(values, header_map, 'price', '0'))

                # Get net amount (handle both positive and negative)
                net_amount_str = self._get_field(values, header_map, 'net amount', '0')
                net_amount = self._parse_decimal(net_amount_str)

                # Get fees
                commission = self._parse_decimal(self._get_field(values, header_map, 'commission', '0'))
                fees = self._parse_decimal(self._get_field(values, header_map, 'fees', '0'))
                total_fees = commission + fees

                # Account
                account_id = self._get_field(values, header_map, 'account', '')

                transaction = Transaction(
                    date=trans_date,
                    transaction_type=trans_type,
                    symbol=symbol if symbol else None,
                    description=description,
                    quantity=quantity,
                    price=price,
                    amount=net_amount,
                    fees=total_fees,
                    account_id=account_id,
                )
                transactions.append(transaction)

            except Exception as e:
                self.warnings.append(f"Error parsing transaction row {i}: {e}")

        return transactions

    def _generate_valuations(
        self,
        transactions: List[Transaction],
        positions: List[Dict],
        account_id: str
    ) -> List[Valuation]:
        """
        Generate period-end valuations.

        Uses:
        1. End Value transactions from CSV
        2. Current position values
        3. Synthesized month-end from transaction flow
        """
        valuations = []

        # Get End Value transactions
        end_values = [t for t in transactions if t.transaction_type == TransactionType.END_VALUE]

        for ev in end_values:
            valuations.append(Valuation(
                date=ev.date,
                market_value=abs(ev.amount),
                accrued_income=Decimal('0'),
                account_id=account_id,
            ))

        # Add current position value ONLY if we don't have End Value transactions
        # End Value transactions are the proper GIPS-compliant monthly valuations
        # Position values may be from different dates and cause unrealistic jumps
        if positions and not valuations:
            total_value = sum(p.get('market_value', Decimal('0')) for p in positions)
            if total_value > 0:
                # No End Value transactions - use position data as fallback
                trans_dates = [t.date for t in transactions if t.date]
                if trans_dates:
                    last_trans = max(trans_dates)
                    # Use end of that month
                    import calendar
                    last_day = calendar.monthrange(last_trans.year, last_trans.month)[1]
                    position_date = date(last_trans.year, last_trans.month, last_day)
                else:
                    position_date = date.today()  # Fallback only

                valuations.append(Valuation(
                    date=position_date,
                    market_value=total_value,
                    accrued_income=Decimal('0'),
                    account_id=account_id,
                ))

        # If no valuations but have transactions, synthesize month-end values
        if not valuations and transactions:
            valuations = self._synthesize_monthly_valuations(transactions, account_id)

        # Sort by date
        valuations = sorted(valuations, key=lambda v: v.date)

        # Remove duplicates (same date)
        seen_dates = set()
        unique_valuations = []
        for v in valuations:
            if v.date not in seen_dates:
                seen_dates.add(v.date)
                unique_valuations.append(v)

        return unique_valuations

    def _synthesize_monthly_valuations(
        self,
        transactions: List[Transaction],
        account_id: str
    ) -> List[Valuation]:
        """
        Synthesize month-end valuations from transaction flow.

        This is an approximation when explicit valuations aren't available.
        """
        if not transactions:
            return []

        # Sort transactions by date
        sorted_trans = sorted(transactions, key=lambda t: t.date)

        # Get date range
        start_date = sorted_trans[0].date
        end_date = sorted_trans[-1].date

        # Calculate running balance
        valuations = []
        running_value = Decimal('0')

        current_date = date(start_date.year, start_date.month, 1)

        while current_date <= end_date:
            # Get transactions for this month
            month_end = self._get_month_end(current_date)
            month_trans = [t for t in sorted_trans
                          if current_date <= t.date <= month_end]

            # Apply transactions
            for t in month_trans:
                running_value += t.amount

            # Create valuation at month end
            if running_value > 0:
                valuations.append(Valuation(
                    date=month_end,
                    market_value=abs(running_value),
                    accrued_income=Decimal('0'),
                    account_id=account_id,
                ))

            # Move to next month
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)

        return valuations

    def _get_month_end(self, d: date) -> date:
        """Get last day of the month."""
        import calendar
        last_day = calendar.monthrange(d.year, d.month)[1]
        return date(d.year, d.month, last_day)

    def _create_account(
        self,
        account_info: Dict[str, str],
        positions: List[Dict]
    ) -> Account:
        """Create Account object from parsed data."""
        # Calculate total market value
        total_value = sum(p.get('market_value', Decimal('0')) for p in positions)

        # Determine inception date (from oldest transaction or position)
        inception = date.today()  # Default

        return Account(
            account_id=account_info.get('account_id', 'UNKNOWN'),
            account_name=account_info.get('account_name', 'Unknown Account'),
            inception_date=inception,
            is_discretionary=True,
            is_fee_paying=True,
            is_active=True,
            client_name=account_info.get('account_name', ''),
        )

    def _parse_csv_row(self, line: str) -> List[str]:
        """Parse a CSV row handling quoted fields."""
        import io
        reader = csv.reader(io.StringIO(line))
        try:
            return next(reader)
        except StopIteration:
            return []

    def _get_field(
        self,
        values: List[str],
        header_map: Dict[str, int],
        field_name: str,
        default: str = ''
    ) -> str:
        """Get field value by header name."""
        idx = header_map.get(field_name.lower())
        if idx is not None and idx < len(values):
            return values[idx].strip()
        return default

    def _parse_decimal(self, value: str) -> Decimal:
        """Parse a decimal value from string."""
        if not value or value.strip() == '':
            return Decimal('0')

        # Remove currency symbols, commas, quotes
        cleaned = value.replace('$', '').replace(',', '').replace('"', '').strip()

        # Handle parentheses for negative numbers
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]

        # Handle percentage
        if cleaned.endswith('%'):
            cleaned = cleaned[:-1]

        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return Decimal('0')

    def _empty_result(self) -> ParseResult:
        """Return empty result for error cases."""
        return ParseResult(
            account=Account(
                account_id='ERROR',
                account_name='Parse Error',
                inception_date=date.today(),
            ),
            transactions=[],
            valuations=[],
            positions=[],
            errors=self.errors,
            warnings=self.warnings,
        )


def parse_schwab_csv(file_path: str) -> ParseResult:
    """Convenience function to parse Schwab CSV."""
    parser = GIPSTransactionParser()
    return parser.parse_file(file_path)


def get_transaction_summary(transactions: List[Transaction]) -> Dict[str, Any]:
    """Get summary statistics for transactions."""
    if not transactions:
        return {
            'total_count': 0,
            'date_range': None,
            'by_type': {},
        }

    by_type = {}
    for t in transactions:
        type_name = t.transaction_type.value
        if type_name not in by_type:
            by_type[type_name] = {'count': 0, 'total_amount': Decimal('0')}
        by_type[type_name]['count'] += 1
        by_type[type_name]['total_amount'] += abs(t.amount)

    dates = [t.date for t in transactions]

    return {
        'total_count': len(transactions),
        'date_range': (min(dates), max(dates)),
        'by_type': by_type,
        'total_fees': sum(t.fees for t in transactions),
    }
