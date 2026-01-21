"""
GIPS Performance Report PDF Generator
======================================
Professional client-facing performance reports.

OUTPUT: Institutional-quality PDF that you hand to clients.

Features:
- Executive Summary with key metrics
- Annual Returns table with benchmark comparison
- Performance charts (cumulative, monthly)
- Risk metrics (3-year stats, Sharpe ratio)
- GIPS-required disclosures
- Auto-tier based on AUM

Author: Marcus (AI Agent)
Version: 1.0 - Client Delivery Ready
"""

import io
import os
import tempfile
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether, HRFlowable
)


# =============================================================================
# COLOR PALETTE - Institutional
# =============================================================================
class Colors:
    NAVY = HexColor('#0A2540')
    NAVY_LIGHT = HexColor('#1E3A5F')
    DARK_GREY = HexColor('#1E293B')
    MEDIUM_GREY = HexColor('#475569')
    LIGHT_GREY = HexColor('#F8FAFC')
    BORDER_GREY = HexColor('#E2E8F0')
    WHITE = HexColor('#FFFFFF')
    GREEN = HexColor('#059669')
    GREEN_LIGHT = HexColor('#D1FAE5')
    RED = HexColor('#DC2626')
    RED_LIGHT = HexColor('#FEE2E2')
    GOLD = HexColor('#B8860B')


# =============================================================================
# TIER DETECTION
# =============================================================================
class ClientTier:
    """Auto-detect client tier based on AUM"""
    ESSENTIAL = 'ESSENTIAL'        # < $5M
    PROFESSIONAL = 'PROFESSIONAL'  # $5M - $50M
    INSTITUTIONAL = 'INSTITUTIONAL'  # $50M - $250M
    ENTERPRISE = 'ENTERPRISE'      # $250M+

    @classmethod
    def detect(cls, aum: float) -> str:
        """Detect tier from AUM"""
        if aum < 5_000_000:
            return cls.ESSENTIAL
        elif aum < 50_000_000:
            return cls.PROFESSIONAL
        elif aum < 250_000_000:
            return cls.INSTITUTIONAL
        else:
            return cls.ENTERPRISE

    @classmethod
    def get_features(cls, tier: str) -> Dict[str, bool]:
        """Get features enabled for each tier"""
        features = {
            cls.ESSENTIAL: {
                'annual_returns': True,
                'monthly_returns': False,
                'benchmark_comparison': False,
                'three_year_stats': False,
                'risk_metrics': False,
                'performance_chart': True,
                'full_disclosures': False,
            },
            cls.PROFESSIONAL: {
                'annual_returns': True,
                'monthly_returns': True,
                'benchmark_comparison': True,
                'three_year_stats': False,
                'risk_metrics': True,
                'performance_chart': True,
                'full_disclosures': False,
            },
            cls.INSTITUTIONAL: {
                'annual_returns': True,
                'monthly_returns': True,
                'benchmark_comparison': True,
                'three_year_stats': True,
                'risk_metrics': True,
                'performance_chart': True,
                'full_disclosures': True,
            },
            cls.ENTERPRISE: {
                'annual_returns': True,
                'monthly_returns': True,
                'benchmark_comparison': True,
                'three_year_stats': True,
                'risk_metrics': True,
                'performance_chart': True,
                'full_disclosures': True,
                'composite_details': True,
                'household_aggregation': True,
            },
        }
        return features.get(tier, features[cls.PROFESSIONAL])


# =============================================================================
# CHART GENERATOR - Professional Charts
# =============================================================================
class GIPSChartGenerator:
    """Generate professional performance charts for PDF"""

    def __init__(self):
        self.temp_files = []
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.size': 8,
            'figure.facecolor': 'white',
            'axes.titlesize': 10,
            'axes.labelsize': 8,
        })

    def create_cumulative_chart(
        self,
        periods: List[str],
        portfolio_cumulative: List[float],
        benchmark_cumulative: List[float] = None,
        benchmark_name: str = 'Benchmark'
    ) -> str:
        """Create cumulative performance chart"""
        fig, ax = plt.subplots(figsize=(5, 2.5), dpi=150)

        ax.plot(range(len(periods)), portfolio_cumulative,
                color='#0A2540', linewidth=1.5, label='Portfolio')

        if benchmark_cumulative:
            ax.plot(range(len(periods)), benchmark_cumulative,
                    color='#6B7280', linewidth=1.2, linestyle='--', label=benchmark_name)

        ax.set_ylabel('Cumulative (%)')
        ax.set_title('Cumulative Performance', fontsize=10, fontweight='bold', color='#0A2540')

        step = max(1, len(periods) // 6)
        ax.set_xticks(range(0, len(periods), step))
        ax.set_xticklabels([periods[i] for i in range(0, len(periods), step)], rotation=45, ha='right', fontsize=7)

        ax.axhline(y=0, color='#94A3B8', linewidth=0.5)
        ax.legend(loc='upper left', framealpha=0.9, fontsize=7)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        temp_path = tempfile.mktemp(suffix='.png')
        fig.savefig(temp_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        self.temp_files.append(temp_path)
        return temp_path

    def create_annual_bar_chart(
        self,
        years: List[int],
        portfolio_returns: List[float],
        benchmark_returns: List[float] = None,
        benchmark_name: str = 'Benchmark'
    ) -> str:
        """Create annual returns bar chart"""
        fig, ax = plt.subplots(figsize=(5, 2.5), dpi=150)

        x = np.arange(len(years))
        width = 0.35 if benchmark_returns else 0.5

        colors_list = ['#059669' if r >= 0 else '#DC2626' for r in portfolio_returns]
        ax.bar(x - width/2 if benchmark_returns else x, portfolio_returns,
               width, label='Portfolio', color=colors_list, edgecolor='white')

        if benchmark_returns:
            ax.bar(x + width/2, benchmark_returns, width,
                   label=benchmark_name, color='#94A3B8', edgecolor='white')

        ax.set_ylabel('Return (%)')
        ax.set_title('Annual Returns', fontsize=10, fontweight='bold', color='#0A2540')
        ax.set_xticks(x)
        ax.set_xticklabels(years, fontsize=7)
        ax.axhline(y=0, color='#1E293B', linewidth=0.8)
        ax.legend(loc='upper left', fontsize=7)
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()

        temp_path = tempfile.mktemp(suffix='.png')
        fig.savefig(temp_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        self.temp_files.append(temp_path)
        return temp_path

    def create_drawdown_chart(self, periods: List[str], cumulative: List[float]) -> str:
        """Create drawdown chart showing underwater periods"""
        fig, ax = plt.subplots(figsize=(5, 2), dpi=150)

        # Calculate drawdown from peak
        peak = cumulative[0]
        drawdowns = []
        for c in cumulative:
            if c > peak:
                peak = c
            drawdown = ((c - peak) / (100 + peak)) * 100 if peak > 0 else 0
            drawdowns.append(drawdown)

        ax.fill_between(range(len(periods)), drawdowns, 0, color='#DC2626', alpha=0.3)
        ax.plot(range(len(periods)), drawdowns, color='#DC2626', linewidth=1)

        ax.set_ylabel('Drawdown (%)')
        ax.set_title('Drawdown Analysis', fontsize=10, fontweight='bold', color='#0A2540')
        step = max(1, len(periods) // 6)
        ax.set_xticks(range(0, len(periods), step))
        ax.set_xticklabels([periods[i] for i in range(0, len(periods), step)], rotation=45, ha='right', fontsize=7)
        ax.axhline(y=0, color='#1E293B', linewidth=0.5)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        temp_path = tempfile.mktemp(suffix='.png')
        fig.savefig(temp_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        self.temp_files.append(temp_path)
        return temp_path

    def create_rolling_returns_chart(self, periods: List[str], returns: List[float]) -> str:
        """Create 12-month rolling returns chart"""
        fig, ax = plt.subplots(figsize=(5, 2), dpi=150)

        if len(returns) < 12:
            return None

        # Calculate 12-month rolling returns
        rolling = []
        for i in range(11, len(returns)):
            rolling_ret = 1
            for j in range(12):
                rolling_ret *= (1 + returns[i-11+j]/100)
            rolling.append((rolling_ret - 1) * 100)

        roll_periods = periods[11:]
        colors = ['#059669' if r >= 0 else '#DC2626' for r in rolling]

        ax.bar(range(len(roll_periods)), rolling, color=colors, width=1.0, edgecolor='none')
        ax.set_ylabel('12M Rolling (%)')
        ax.set_title('12-Month Rolling Returns', fontsize=10, fontweight='bold', color='#0A2540')
        step = max(1, len(roll_periods) // 6)
        ax.set_xticks(range(0, len(roll_periods), step))
        ax.set_xticklabels([roll_periods[i] for i in range(0, len(roll_periods), step)], rotation=45, ha='right', fontsize=7)
        ax.axhline(y=0, color='#1E293B', linewidth=0.5)
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()

        temp_path = tempfile.mktemp(suffix='.png')
        fig.savefig(temp_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        self.temp_files.append(temp_path)
        return temp_path

    def cleanup(self):
        """Remove temp files"""
        for f in self.temp_files:
            try:
                os.remove(f)
            except:
                pass


# =============================================================================
# GIPS PDF REPORT GENERATOR
# =============================================================================
class GIPSPDFReport:
    """
    Generate professional GIPS performance report PDF.

    This is what you hand to clients.
    """

    def __init__(self, firm_name: str = "Your Firm Name"):
        self.firm_name = firm_name
        self.chart_gen = GIPSChartGenerator()
        self._setup_styles()

    def _setup_styles(self):
        """Setup PDF styles - GOLDMAN SACHS caliber professional layout"""
        self.styles = getSampleStyleSheet()

        # Title style - elegant, professional
        self.styles.add(ParagraphStyle(
            name='GIPSTitle',
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=Colors.NAVY,
            spaceAfter=6,
            spaceBefore=0,
            leading=26,
            alignment=TA_CENTER,
        ))

        # Subtitle - clean
        self.styles.add(ParagraphStyle(
            name='GIPSSubtitle',
            fontName='Helvetica',
            fontSize=11,
            textColor=Colors.MEDIUM_GREY,
            spaceAfter=15,
            spaceBefore=0,
            leading=14,
            alignment=TA_CENTER,
        ))

        # Section header - CLEAR with breathing room
        self.styles.add(ParagraphStyle(
            name='GIPSSection',
            fontName='Helvetica-Bold',
            fontSize=13,
            textColor=Colors.NAVY,
            spaceBefore=20,  # Good space BEFORE section headers
            spaceAfter=8,    # Space after header before content
            leading=16,
        ))

        # Body text - readable with good line spacing
        self.styles.add(ParagraphStyle(
            name='GIPSBody',
            fontName='Helvetica',
            fontSize=9,
            textColor=Colors.DARK_GREY,
            spaceAfter=10,
            spaceBefore=6,
            leading=14,
        ))

        # Small text (disclosures) - readable
        self.styles.add(ParagraphStyle(
            name='GIPSSmall',
            fontName='Helvetica',
            fontSize=8,
            textColor=Colors.MEDIUM_GREY,
            spaceAfter=5,
            spaceBefore=3,
            leading=12,
        ))

        # Metric value - bold and prominent
        self.styles.add(ParagraphStyle(
            name='GIPSMetric',
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=Colors.NAVY,
            alignment=TA_CENTER,
            leading=24,
        ))

        # Metric label - clear
        self.styles.add(ParagraphStyle(
            name='GIPSMetricLabel',
            fontName='Helvetica',
            fontSize=9,
            textColor=Colors.MEDIUM_GREY,
            alignment=TA_CENTER,
            leading=12,
        ))

    def generate(
        self,
        account_name: str,
        market_value: float,
        returns_data: Dict[str, Any],
        benchmark_name: str = None,
        benchmark_stats: Dict = None,
        output_path: str = None,
    ) -> str:
        """
        Generate GIPS PDF report.

        Args:
            account_name: Client/account name
            market_value: Total market value (for tier detection)
            returns_data: Dict with returns, annual_returns, etc.
            benchmark_name: Benchmark name for comparison
            benchmark_stats: Benchmark statistics
            output_path: Output file path (optional)

        Returns:
            Path to generated PDF
        """
        # Auto-detect tier
        tier = ClientTier.detect(market_value)
        features = ClientTier.get_features(tier)

        # Generate output path
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"GIPS_Performance_Report_{timestamp}.pdf"

        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
        )

        # Build content - CONTINUOUS FLOW like Goldman Sachs reports
        story = []

        # ===== HEADER =====
        story.extend(self._build_cover_page(account_name, market_value, tier))
        story.extend(self._build_executive_summary(returns_data, benchmark_name, benchmark_stats, features))

        # ===== PERFORMANCE CHARTS =====
        if features.get('performance_chart'):
            story.extend(self._build_performance_charts(returns_data, benchmark_name))

        # ===== ANNUAL RETURNS =====
        if features.get('annual_returns'):
            story.extend(self._build_annual_returns_table(returns_data, benchmark_stats, features))

        # ===== RISK METRICS =====
        if features.get('risk_metrics') and returns_data.get('three_yr_std'):
            story.extend(self._build_risk_metrics(returns_data, benchmark_stats))

        # ===== DETAILED ANALYSIS (continuous, no page break) =====
        if features.get('monthly_returns'):
            # TWR Methodology & Statistics
            story.extend(self._build_twr_methodology(returns_data))

            # Gain/Loss Analysis
            story.extend(self._build_gain_loss_analysis(returns_data))

            # Monthly returns grid
            story.extend(self._build_monthly_returns_table(returns_data))

        # ===== GIPS DISCLOSURES =====
        story.extend(self._build_disclosures(tier, features, returns_data))

        # Build PDF
        doc.build(story)

        # Cleanup temp files
        self.chart_gen.cleanup()

        return output_path

    def _build_cover_page(self, account_name: str, market_value: float, tier: str) -> List:
        """Build cover/header section - COMPACT"""
        elements = []

        # Firm name and report title on same line essentially
        elements.append(Paragraph(self.firm_name, self.styles['GIPSTitle']))
        elements.append(Paragraph("Investment Performance Report", self.styles['GIPSSubtitle']))

        # Client info - single row table for compactness
        client_data = [[
            f"Account: {account_name}",
            f"Date: {datetime.now().strftime('%b %d, %Y')}",
            f"Value: ${market_value:,.0f}"
        ]]

        client_table = Table(client_data, colWidths=[2.8*inch, 2*inch, 2.2*inch])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), Colors.DARK_GREY),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), Colors.LIGHT_GREY),
            ('BOX', (0, 0), (-1, -1), 0.5, Colors.BORDER_GREY),
        ]))

        elements.append(client_table)
        elements.append(Spacer(1, 8))

        return elements

    def _build_executive_summary(
        self,
        returns_data: Dict,
        benchmark_name: str,
        benchmark_stats: Dict,
        features: Dict
    ) -> List:
        """Build executive summary with key metrics - COMPACT"""
        elements = []

        elements.append(Paragraph("Executive Summary", self.styles['GIPSSection']))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=Colors.BORDER_GREY))

        # Key metrics cards
        cumulative = returns_data.get('cumulative_return', 0)
        annualized = returns_data.get('annualized_return')
        three_yr_std = returns_data.get('three_yr_std')
        num_periods = returns_data.get('num_periods', 0)
        date_range = returns_data.get('date_range', '')

        # Build metrics row
        metrics = [(f"{cumulative:.1f}%", "Cumulative Return")]

        if annualized is not None:
            metrics.append((f"{annualized:.1f}%", "Annualized Return"))

        if features.get('three_year_stats') and three_yr_std:
            metrics.append((f"{three_yr_std:.1f}%", "3-Yr Volatility"))

        # Jensen's Alpha (proper beta-adjusted alpha from risk_engine)
        # Only show if provided - this is the CORRECT alpha calculation
        jensens_alpha = returns_data.get('jensens_alpha')
        if features.get('benchmark_comparison') and jensens_alpha is not None:
            # Convert from decimal to percentage if needed
            alpha_pct = jensens_alpha * 100 if abs(jensens_alpha) < 1 else jensens_alpha
            metrics.append((f"{alpha_pct:+.1f}%", f"Jensen's Alpha"))

        # Create metrics table - compact
        metric_cells = []
        label_cells = []
        for value, label in metrics:
            metric_cells.append(Paragraph(value, self.styles['GIPSMetric']))
            label_cells.append(Paragraph(label, self.styles['GIPSMetricLabel']))

        col_width = 7 * inch / len(metrics)
        metrics_table = Table(
            [metric_cells, label_cells],
            colWidths=[col_width] * len(metrics),
            rowHeights=[25, 15]
        )
        metrics_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), Colors.LIGHT_GREY),
            ('BOX', (0, 0), (-1, -1), 0.5, Colors.BORDER_GREY),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, Colors.BORDER_GREY),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 6),
        ]))

        elements.append(metrics_table)

        # Period info - inline
        elements.append(Paragraph(
            f"Performance period: {date_range} ({num_periods} months)",
            self.styles['GIPSSmall']
        ))
        elements.append(Spacer(1, 4))

        return elements

    def _build_performance_charts(self, returns_data: Dict, benchmark_name: str) -> List:
        """Build comprehensive performance charts section - PROFESSIONAL layout"""
        elements = []

        elements.append(Paragraph("Performance Analysis", self.styles['GIPSSection']))
        elements.append(HRFlowable(width="100%", thickness=1, color=Colors.NAVY))
        elements.append(Spacer(1, 12))

        monthly_returns = returns_data.get('monthly_returns', [])
        annual_returns = returns_data.get('annual_returns', {})

        if not monthly_returns:
            return elements

        periods = [m['period'] for m in monthly_returns]
        cumulative = [m['cumulative'] for m in monthly_returns]
        returns_list = [m['return'] for m in monthly_returns]

        # Row 1: Cumulative + Annual bar - LARGER charts
        chart_row1 = []
        cum_chart = self.chart_gen.create_cumulative_chart(periods, cumulative, benchmark_name=benchmark_name)
        chart_row1.append(Image(cum_chart, width=3.6*inch, height=1.8*inch))

        if annual_returns:
            years = sorted(annual_returns.keys())
            ann_returns = [annual_returns[y] for y in years]
            ann_chart = self.chart_gen.create_annual_bar_chart(years, ann_returns, benchmark_name=benchmark_name)
            chart_row1.append(Image(ann_chart, width=3.6*inch, height=1.8*inch))

        if len(chart_row1) >= 1:
            table1 = Table([chart_row1], colWidths=[3.7*inch] * len(chart_row1))
            table1.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(table1)

        elements.append(Spacer(1, 15))  # Good space between chart rows

        # Row 2: Drawdown + Rolling Returns
        chart_row2 = []
        dd_chart = self.chart_gen.create_drawdown_chart(periods, cumulative)
        if dd_chart:
            chart_row2.append(Image(dd_chart, width=3.6*inch, height=1.6*inch))

        roll_chart = self.chart_gen.create_rolling_returns_chart(periods, returns_list)
        if roll_chart:
            chart_row2.append(Image(roll_chart, width=3.6*inch, height=1.6*inch))

        if chart_row2:
            table2 = Table([chart_row2], colWidths=[3.7*inch] * len(chart_row2))
            table2.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(table2)

        elements.append(Spacer(1, 20))  # Good space after charts
        return elements

    def _build_annual_returns_table(
        self,
        returns_data: Dict,
        benchmark_stats: Dict,
        features: Dict
    ) -> List:
        """Build annual returns table - PROFESSIONAL"""
        elements = []

        # Use KeepTogether to prevent header from separating from table
        section_content = []
        section_content.append(Paragraph("Annual Performance", self.styles['GIPSSection']))
        section_content.append(HRFlowable(width="100%", thickness=1, color=Colors.NAVY))
        section_content.append(Spacer(1, 12))

        annual_returns = returns_data.get('annual_returns', {})

        if not annual_returns:
            section_content.append(Paragraph("Insufficient data.", self.styles['GIPSBody']))
            elements.append(KeepTogether(section_content))
            return elements

        # Build table - horizontal layout for compactness
        years = sorted(annual_returns.keys(), reverse=True)
        header_row = [''] + [str(y) for y in years]
        data_row = ['Return'] + [f"{annual_returns[y]:.1f}%" for y in years]

        col_width = 7 * inch / len(header_row)
        table = Table([header_row, data_row], colWidths=[col_width] * len(header_row))
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Colors.NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), Colors.WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 1), (-1, -1), Colors.DARK_GREY),
            ('BACKGROUND', (0, 1), (-1, 1), Colors.LIGHT_GREY),
            ('BOX', (0, 0), (-1, -1), 0.5, Colors.BORDER_GREY),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, Colors.BORDER_GREY),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        section_content.append(table)

        # Wrap entire section in KeepTogether to prevent page break between header and table
        elements.append(KeepTogether(section_content))
        elements.append(Spacer(1, 15))

        return elements

    def _build_risk_metrics(self, returns_data: Dict, benchmark_stats: Dict) -> List:
        """Build risk metrics section with GIPS-required stats - PROFESSIONAL"""
        elements = []

        # Use KeepTogether to prevent header from separating from table
        section_content = []
        section_content.append(Paragraph("3-Year Risk Analysis (GIPS Required)", self.styles['GIPSSection']))
        section_content.append(HRFlowable(width="100%", thickness=1, color=Colors.NAVY))
        section_content.append(Spacer(1, 12))

        # Risk comparison table
        port_3yr = returns_data.get('annualized_return', 0) or 0
        bench_3yr = (benchmark_stats.get('3yr_annualized_return', 0) * 100) if benchmark_stats else 0
        port_std = returns_data.get('three_yr_std', 0) or 0
        bench_std = (benchmark_stats.get('3yr_annualized_std', 0) * 100) if benchmark_stats else 0

        # Calculate risk-adjusted metrics
        risk_free = 4.5  # Current approximate risk-free rate
        port_sharpe = (port_3yr - risk_free) / port_std if port_std > 0 else 0
        bench_sharpe = (bench_3yr - risk_free) / bench_std if bench_std > 0 else 0

        # GIPS-required metrics table with proper Jensen's Alpha if available
        header = ['Metric', 'Portfolio', 'Benchmark', 'Difference']
        return_row = ['3-Yr Annualized Return', f"{port_3yr:.2f}%", f"{bench_3yr:.2f}%", f"{port_3yr - bench_3yr:+.2f}%"]
        std_row = ['3-Yr Annualized Std Dev', f"{port_std:.2f}%", f"{bench_std:.2f}%", f"{port_std - bench_std:+.2f}%"]
        sharpe_row = ['Sharpe Ratio (Rf=4.5%)', f"{port_sharpe:.2f}", f"{bench_sharpe:.2f}", f"{port_sharpe - bench_sharpe:+.2f}"]

        # Build table rows
        table_data = [header, return_row, std_row, sharpe_row]

        # Add Jensen's Alpha and Beta if provided (proper CAPM-based calculations)
        jensens_alpha = returns_data.get('jensens_alpha')
        beta = returns_data.get('beta')

        if beta is not None:
            beta_row = ['Beta (vs Benchmark)', f"{beta:.2f}", '1.00', f"{beta - 1:+.2f}"]
            table_data.append(beta_row)

        if jensens_alpha is not None:
            # Convert from decimal to percentage if needed
            alpha_pct = jensens_alpha * 100 if abs(jensens_alpha) < 1 else jensens_alpha
            alpha_row = ["Jensen's Alpha (CAPM)", f"{alpha_pct:+.2f}%", '—', '—']
            table_data.append(alpha_row)

        table = Table(table_data,
                     colWidths=[2.2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Colors.NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), Colors.WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 1), (-1, -1), Colors.DARK_GREY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [Colors.WHITE, Colors.LIGHT_GREY]),
            ('BOX', (0, 0), (-1, -1), 0.5, Colors.BORDER_GREY),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, Colors.BORDER_GREY),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        section_content.append(table)

        # Add note about GIPS requirement and Jensen's Alpha formula
        section_content.append(Spacer(1, 8))
        note_text = "Note: GIPS requires presentation of 3-year annualized standard deviation for both composite and benchmark when 36+ months of data are available."
        if jensens_alpha is not None:
            note_text += " Jensen's Alpha = Portfolio Return - [Rf + β × (Benchmark Return - Rf)], measuring risk-adjusted excess return."
        section_content.append(Paragraph(note_text, self.styles['GIPSSmall']))

        # Wrap entire section in KeepTogether to prevent page break between header and table
        elements.append(KeepTogether(section_content))
        elements.append(Spacer(1, 15))

        return elements

    def _build_twr_methodology(self, returns_data: Dict) -> List:
        """Build TWR methodology explanation section - PROFESSIONAL"""
        elements = []

        # Use KeepTogether to prevent header from separating from table
        section_content = []
        section_content.append(Paragraph("Time-Weighted Return (TWR) Methodology", self.styles['GIPSSection']))
        section_content.append(HRFlowable(width="100%", thickness=1, color=Colors.NAVY))
        section_content.append(Spacer(1, 10))

        # TWR explanation
        section_content.append(Paragraph(
            "Returns are calculated using Time-Weighted Return (TWR) methodology as required by GIPS® standards. "
            "TWR eliminates the impact of external cash flows to provide a pure measure of investment performance.",
            self.styles['GIPSBody']
        ))
        section_content.append(Spacer(1, 12))

        monthly_returns = returns_data.get('monthly_returns', [])
        if not monthly_returns:
            elements.append(KeepTogether(section_content))
            return elements

        # Calculate statistics
        returns_list = [m['return'] for m in monthly_returns]
        positive_months = sum(1 for r in returns_list if r > 0)
        negative_months = sum(1 for r in returns_list if r < 0)
        best_month = max(returns_list) if returns_list else 0
        worst_month = min(returns_list) if returns_list else 0
        avg_monthly = sum(returns_list) / len(returns_list) if returns_list else 0

        # Find best/worst month dates
        best_idx = returns_list.index(best_month) if best_month else 0
        worst_idx = returns_list.index(worst_month) if worst_month else 0
        best_period = monthly_returns[best_idx]['period'] if monthly_returns else ''
        worst_period = monthly_returns[worst_idx]['period'] if monthly_returns else ''

        # Statistics table
        data = [
            ['Statistic', 'Value', 'Statistic', 'Value'],
            ['Positive Months', str(positive_months), 'Negative Months', str(negative_months)],
            ['Best Month', f"{best_month:.2f}% ({best_period})", 'Worst Month', f"{worst_month:.2f}% ({worst_period})"],
            ['Win Rate', f"{positive_months/(positive_months+negative_months)*100:.1f}%", 'Avg Monthly', f"{avg_monthly:.2f}%"],
        ]

        table = Table(data, colWidths=[1.6*inch, 1.9*inch, 1.6*inch, 1.9*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Colors.NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), Colors.WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 1), (2, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR', (0, 1), (-1, -1), Colors.DARK_GREY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [Colors.WHITE, Colors.LIGHT_GREY]),
            ('BOX', (0, 0), (-1, -1), 0.5, Colors.BORDER_GREY),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, Colors.BORDER_GREY),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))

        section_content.append(table)

        # Wrap entire section in KeepTogether to prevent page break between header and table
        elements.append(KeepTogether(section_content))
        elements.append(Spacer(1, 15))
        return elements

    def _build_gain_loss_analysis(self, returns_data: Dict) -> List:
        """Build gain/loss analysis section - PROFESSIONAL"""
        elements = []

        # Use KeepTogether to prevent header from separating from table
        section_content = []
        section_content.append(Paragraph("Gain/Loss Analysis", self.styles['GIPSSection']))
        section_content.append(HRFlowable(width="100%", thickness=1, color=Colors.NAVY))
        section_content.append(Spacer(1, 12))

        annual_returns = returns_data.get('annual_returns', {})
        if not annual_returns:
            elements.append(KeepTogether(section_content))
            return elements

        # Calculate gain/loss statistics by year
        years = sorted(annual_returns.keys())
        gains = [annual_returns[y] for y in years if annual_returns[y] > 0]
        losses = [annual_returns[y] for y in years if annual_returns[y] < 0]

        total_gain = sum(gains) if gains else 0
        total_loss = sum(losses) if losses else 0
        avg_gain = total_gain / len(gains) if gains else 0
        avg_loss = total_loss / len(losses) if losses else 0
        gain_loss_ratio = abs(avg_gain / avg_loss) if avg_loss != 0 else float('inf')

        # Summary metrics
        data = [
            ['Metric', 'Gains', 'Losses'],
            ['Count', f"{len(gains)} years", f"{len(losses)} years"],
            ['Average', f"{avg_gain:.2f}%", f"{avg_loss:.2f}%"],
            ['Total', f"{total_gain:.2f}%", f"{total_loss:.2f}%"],
            ['Gain/Loss Ratio', f"{gain_loss_ratio:.2f}x", '—'],
        ]

        table = Table(data, colWidths=[2*inch, 2.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Colors.NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), Colors.WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR', (1, 1), (1, -1), Colors.GREEN),
            ('TEXTCOLOR', (2, 1), (2, -1), Colors.RED),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [Colors.WHITE, Colors.LIGHT_GREY]),
            ('BOX', (0, 0), (-1, -1), 0.5, Colors.BORDER_GREY),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, Colors.BORDER_GREY),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        section_content.append(table)

        # Wrap entire section in KeepTogether to prevent page break between header and table
        elements.append(KeepTogether(section_content))
        elements.append(Spacer(1, 15))
        return elements

    def _build_monthly_returns_table(self, returns_data: Dict) -> List:
        """Build monthly returns grid - PROFESSIONAL calendar format"""
        elements = []

        # Use KeepTogether to prevent header from separating from table
        section_content = []
        section_content.append(Paragraph("Monthly Returns (%)", self.styles['GIPSSection']))
        section_content.append(HRFlowable(width="100%", thickness=1, color=Colors.NAVY))
        section_content.append(Spacer(1, 12))

        monthly_returns = returns_data.get('monthly_returns', [])
        if not monthly_returns:
            elements.append(KeepTogether(section_content))
            return elements

        # Organize by year and month
        by_year = {}
        for m in monthly_returns:
            period = m.get('period', '')
            if len(period) >= 7:
                year = int(period[:4])
                month = int(period[5:7])
                if year not in by_year:
                    by_year[year] = {}
                by_year[year][month] = m.get('return', 0)

        # Build calendar-style table
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'YTD']
        header = ['Year'] + months

        data = [header]
        for year in sorted(by_year.keys(), reverse=True):
            row = [str(year)]
            ytd = 1.0
            for m in range(1, 13):
                if m in by_year[year]:
                    ret = by_year[year][m]
                    row.append(f"{ret:.1f}")
                    ytd *= (1 + ret/100)
                else:
                    row.append('-')
            row.append(f"{(ytd-1)*100:.1f}")
            data.append(row)

        col_widths = [0.5*inch] + [0.5*inch]*13
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Colors.NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), Colors.WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 1), (-1, -1), Colors.DARK_GREY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [Colors.WHITE, Colors.LIGHT_GREY]),
            ('BOX', (0, 0), (-1, -1), 0.5, Colors.BORDER_GREY),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, Colors.BORDER_GREY),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            # Highlight YTD column
            ('BACKGROUND', (-1, 0), (-1, -1), Colors.NAVY_LIGHT),
            ('TEXTCOLOR', (-1, 0), (-1, -1), Colors.WHITE),
        ]))

        section_content.append(table)

        # Wrap entire section in KeepTogether to prevent page break between header and table
        elements.append(KeepTogether(section_content))
        elements.append(Spacer(1, 15))

        return elements

    def _build_disclosures(self, tier: str, features: Dict, returns_data: Dict = None) -> List:
        """Build GIPS disclosures section - PROFESSIONAL"""
        elements = []

        # Use KeepTogether to prevent header from separating from disclosures
        section_content = []
        section_content.append(Paragraph("Important Disclosures", self.styles['GIPSSection']))
        section_content.append(HRFlowable(width="100%", thickness=1, color=Colors.NAVY))
        section_content.append(Spacer(1, 10))

        # Add GIPS statistics section for institutional tier
        if features.get('full_disclosures') and returns_data:
            firm_assets = returns_data.get('firm_total_assets')
            pct_of_firm = returns_data.get('pct_of_firm')
            num_portfolios = returns_data.get('num_portfolios', 1)
            fee_schedule = returns_data.get('fee_schedule')

            # GIPS Statistics Box
            stats_text = []
            if firm_assets:
                stats_text.append(f"Total Firm Assets: ${firm_assets:,.0f}")
            if pct_of_firm:
                stats_text.append(f"Composite % of Firm: {pct_of_firm:.2f}%")
            stats_text.append(f"Number of Portfolios: {num_portfolios}")
            if fee_schedule:
                stats_text.append(f"Fee Schedule: {fee_schedule}")

            if stats_text:
                section_content.append(Paragraph(" | ".join(stats_text), self.styles['GIPSSmall']))
                section_content.append(Spacer(1, 4))

        if features.get('full_disclosures'):
            # Full GIPS disclosures for institutional tier - in a compact format
            disclosures = [
                f"1. {self.firm_name} claims compliance with the Global Investment Performance Standards (GIPS®).",
                "2. GIPS® is a registered trademark of CFA Institute. CFA Institute does not endorse or promote this organization, nor does it warrant the accuracy or quality of the content contained herein.",
                "3. Returns are calculated using time-weighted methodology (Modified Dietz) with geometric linking of periodic returns as required by GIPS.",
                "4. Returns are presented net of management fees and trading costs. Gross returns are available upon request.",
                "5. All fee-paying discretionary accounts managed in this strategy are included in composite calculations.",
                "6. Valuations are computed using fair market value as of each period end with at least monthly valuation.",
                "7. The 3-year annualized standard deviation is calculated using monthly returns for the 36-month period ending on the report date.",
                "8. Past performance is not indicative of future results. Investment involves risk including possible loss of principal.",
                "9. For a complete list and description of all composites and GIPS verification status, please contact the firm.",
            ]
        else:
            disclosures = [
                "Returns are calculated using time-weighted methodology.",
                "Returns are presented net of management fees.",
                "Past performance is not indicative of future results.",
                "Please contact your advisor for additional information.",
            ]

        for d in disclosures:
            section_content.append(Paragraph(d, self.styles['GIPSSmall']))

        # Wrap first part in KeepTogether (header + first few disclosures)
        elements.append(KeepTogether(section_content))

        # Footer (outside KeepTogether so it can flow naturally at end)
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=Colors.BORDER_GREY))
        elements.append(Paragraph(
            f"Report generated: {datetime.now().strftime('%B %d, %Y at %H:%M')} | Confidential - Prepared exclusively for the named client.",
            self.styles['GIPSSmall']
        ))

        return elements


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================
def generate_gips_pdf(
    account_name: str,
    market_value: float,
    returns: list,
    annual_returns: dict,
    cumulative_return: float,
    annualized_return: float = None,
    three_yr_std: float = None,
    date_range: str = "",
    benchmark_name: str = None,
    benchmark_stats: dict = None,
    firm_name: str = "CapX100 Wealth Management",
    output_path: str = None,
    firm_total_assets: float = None,  # Total firm AUM for GIPS compliance
    num_portfolios: int = 1,  # Number of portfolios in composite
    fee_schedule: str = None,  # Fee schedule description
    jensens_alpha: float = None,  # Proper Jensen's Alpha from risk_engine (beta-adjusted)
    beta: float = None,  # Portfolio beta vs benchmark
) -> str:
    """
    Generate GIPS PDF report - convenience function.

    Returns path to generated PDF.
    """
    # Build returns data dict
    monthly_returns = []
    cumulative = 0
    for r in returns:
        cumulative += r.net_return * 100 if hasattr(r, 'net_return') else r * 100
        monthly_returns.append({
            'period': r.period_end.strftime('%Y-%m') if hasattr(r, 'period_end') else '',
            'return': float(r.net_return * 100) if hasattr(r, 'net_return') else r * 100,
            'cumulative': cumulative,
        })

    returns_data = {
        'monthly_returns': monthly_returns,
        'annual_returns': annual_returns,
        'cumulative_return': cumulative_return,
        'annualized_return': annualized_return,
        'three_yr_std': three_yr_std,
        'num_periods': len(returns),
        'date_range': date_range,
        'firm_total_assets': firm_total_assets,
        'num_portfolios': num_portfolios,
        'fee_schedule': fee_schedule,
        'pct_of_firm': (market_value / firm_total_assets * 100) if firm_total_assets else None,
        'jensens_alpha': jensens_alpha,  # Proper beta-adjusted alpha
        'beta': beta,  # Portfolio beta
    }

    # Generate report
    generator = GIPSPDFReport(firm_name=firm_name)
    return generator.generate(
        account_name=account_name,
        market_value=market_value,
        returns_data=returns_data,
        benchmark_name=benchmark_name,
        benchmark_stats=benchmark_stats,
        output_path=output_path,
    )
