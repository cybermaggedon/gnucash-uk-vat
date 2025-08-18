# Test Data Generator Specification

## Overview

This specification defines a Python-based test data generator for GnuCash files using piecash. The generator creates realistic UK business transactions over multi-year periods (typically 3+ years) for comprehensive testing of VAT reporting, accounting scenarios, and business lifecycle events.

## Input Sources

### Base Account Structure
- Uses existing account structure from `accounts/accounts2.gnucash`
- Preserves the UK-specific VAT account hierarchy
- Maintains GBP currency for all transactions

### Transaction Templates
The generator supports realistic business transactions across multiple categories:

#### 1. Revenue Transactions
- **UK Sales (Standard Rate)**: 20% VAT on domestic B2B services
  - Software licenses, consultancy, training
  - Professional services, design work
  - Digital products and SaaS subscriptions
- **UK Sales (Zero Rate)**: 0% VAT on qualifying goods
  - Books, publications, educational materials
  - Exports to non-EU countries
- **EU B2B Sales**: 0% VAT (reverse charge)
  - Cross-border services to VAT-registered businesses
  - Digital services under reverse charge rules
- **International Sales**: 0% VAT exports
  - Software exports to US, Asia-Pacific
  - Consultancy services to non-EU clients
  - Place of supply outside UK/EU

#### 2. Operating Expenses
- **Office & Facilities** (20% VAT):
  - Office rent, utilities, cleaning services
  - Office supplies, furniture, equipment
  - Security, insurance premiums
- **Professional Services** (20% VAT):
  - Accountancy fees, legal services
  - Audit fees, tax advisory
  - Marketing, PR, and consultancy
- **Technology & Software** (20% VAT):
  - Software licenses and subscriptions
  - Cloud hosting, domain registration
  - IT support and maintenance
- **Travel & Subsistence** (Mixed VAT):
  - Domestic travel (20% VAT)
  - International travel (0% VAT on flights)
  - Hotels, meals, conferences
- **Telecoms** (20% VAT):
  - Mobile phones, broadband
  - Landline rental and calls

#### 3. Capital Asset Transactions
- **Equipment Purchases** (20% VAT):
  - Computer hardware, servers
  - Office furniture and fittings
  - Motor vehicles (partial VAT recovery)
- **Intangible Assets** (20% VAT):
  - Software licenses (capitalized)
  - Intellectual property acquisitions
- **EU Reverse VAT Purchases** (20% VAT):
  - Equipment from EU suppliers
  - Simultaneous input and output VAT

#### 4. Depreciation & Amortization
- **Computer Equipment**: 3-year straight line
- **Office Furniture**: 5-year straight line
- **Motor Vehicles**: 4-year straight line
- **Software Licenses**: Over license period
- **Monthly depreciation postings** (no VAT)

#### 5. Employment Costs
- **Director's Fees**: 
  - Gross fees with 20% income tax
  - Class 1 NICs (employee and employer)
  - No VAT implications
- **Employee Salaries**:
  - Gross pay with PAYE deductions
  - Employee and employer NICs
  - Stakeholder pension contributions
- **Employment Benefits**:
  - Private health insurance (exempt from VAT)
  - Training courses (20% VAT or exempt)

#### 6. Equity & Financing
- **Share Issuance**:
  - Director share purchases
  - External investor funding rounds
  - Share premium allocation
- **Dividend Payments**:
  - Interim and final dividends
  - Tax credit calculations
  - Distribution to shareholders
- **Director's Loans**:
  - Loans to/from directors
  - Interest calculations (if applicable)
  - S455 tax implications

#### 7. Tax & Compliance
- **Corporation Tax**:
  - Quarterly installment payments
  - Final balancing payments
  - Overpayments and refunds
- **VAT Returns**:
  - Quarterly VAT settlements
  - Monthly payments (if large)
  - VAT refunds for zero-rated exports
- **PAYE/NICs**:
  - Monthly RTI submissions
  - Annual P11D filings

#### 8. Banking & Finance
- **Bank Transactions**:
  - Current account operations
  - Reserve account transfers
  - Bank interest (no VAT)
  - Bank charges and fees (exempt)
- **Foreign Exchange**:
  - Currency conversion transactions
  - FX gains/losses on international sales
- **Loan Transactions**:
  - Business loan drawdowns
  - Interest payments (exempt from VAT)
  - Capital repayments

## Configuration Options

### Multi-Year Time Periods
- `start_year`: Beginning year (e.g., 2021)
- `end_year`: Final year (e.g., 2023)
- `financial_year_end`: Company year-end date (default: 31 March)
- `vat_quarter_starts`: VAT return periods (default: Jan/Apr/Jul/Oct)
- `generate_full_years`: Complete financial years only

### Business Growth Modeling
- `annual_growth_rate`: Revenue growth percentage (default: 15%)
- `seasonal_variations`: Monthly scaling factors
- `business_maturity`: Startup, growth, or established patterns
- `staff_growth_schedule`: Employee hiring timeline

### Revenue Configuration
- `monthly_revenue_base`: Starting monthly revenue (£10K-£100K)
- `revenue_mix`: Percentage split (UK/EU/International)
- `contract_sizes`: (£500-£50K for services, £100-£5K for products)
- `recurring_revenue`: Percentage of revenue from subscriptions

### Operating Expense Patterns
- `fixed_costs_monthly`: Rent, insurance, licenses (£2K-£20K)
- `variable_cost_percentage`: As percentage of revenue (10-30%)
- `expense_categories`: Professional, travel, marketing, IT
- `annual_expense_events`: Conference attendance, equipment purchases

### Capital Investment Schedule
- `equipment_refresh_cycle`: Major purchases every N years
- `initial_setup_costs`: Year 1 capital expenditure
- `annual_capex_budget`: Ongoing capital investments
- `depreciation_policies`: Asset class depreciation rates

### Employment & Payroll
- `director_salary_annual`: £8,788 (optimal for NICs)
- `director_dividend_policy`: Remainder as dividends
- `employee_salary_ranges`: By role/seniority
- `payroll_growth_schedule`: New hires by quarter
- `bonus_payment_months`: Quarterly or annual bonuses

### Tax & Compliance Timing
- `corporation_tax_quarters`: Payment schedule
- `vat_return_frequency`: Monthly or quarterly
- `dividend_payment_schedule`: Interim and final
- `year_end_adjustments`: Accruals, prepayments, provisions

### VAT Configuration
- `standard_rate`: 20% (can vary by year for historical rates)
- `reverse_charge_threshold`: EU transaction limits
- `export_documentation`: Realistic export evidence
- `vat_registration_threshold`: £85K (2021-2023)

### Realistic Data Parameters
- `customer_concentration`: Major vs. small customer mix
- `supplier_loyalty`: Repeat vs. one-off suppliers
- `payment_terms`: 30/60/90 day payment cycles
- `bad_debt_rate`: Percentage of sales written off
- `fx_volatility`: Exchange rate fluctuation ranges

## Output Specifications

### Transaction Structure
Each generated transaction includes:
- Unique description with realistic company/supplier names
- Appropriate posting date within specified range
- Currency set to GBP
- Proper double-entry splits

### VAT Handling
- Automatic calculation of VAT amounts
- Proper allocation to VAT Input/Output accounts
- Support for reverse VAT scenarios
- Zero-rate and exempt transaction handling

### Account Mapping
Transactions are mapped to the existing account structure:
- **Revenue** → Income/Sales (UK/EU/World sub-accounts)
- **Operating Expenses** → Expenses/VAT Purchases (by category)
- **Capital Assets** → Assets/Capital Equipment (by type)
- **Depreciation** → Expenses/Depreciation (by asset class)
- **Payroll** → Expenses/Emoluments (directors/employees)
- **Tax Liabilities** → Liabilities (Corporation Tax, VAT, PAYE)
- **Equity Transactions** → Equity (shares, dividends, retained earnings)
- **VAT** → VAT Input/Output (by transaction type)
- **Banking** → Bank Accounts (current/reserve)

## Data Quality Features

### Realistic Business Scenarios
- **Customer Base**: Mix of large clients (£10K+ monthly) and smaller projects
- **Supplier Relationships**: Regular monthly suppliers vs. one-off purchases
- **Seasonal Patterns**: Q4 sales boost, Q1 expense heavy (conferences/training)
- **Growth Trajectory**: Organic revenue growth with occasional large contract wins
- **Market Events**: Economic impacts (COVID-2020, Brexit effects 2021)
- **Business Lifecycle**: Startup cash flow challenges, growth investments, maturity

### Validation Rules
- All transactions balance to zero
- VAT calculations are mathematically correct
- Account types match transaction types
- No negative amounts in inappropriate accounts

### Error Prevention
- Duplicate transaction detection
- Account existence validation
- Currency consistency checks
- Date range validation

## Usage Examples

### Multi-Year Business Generation
```python
# Generate 3-year business lifecycle
generator = TestDataGenerator('accounts/accounts2.gnucash')
generator.generate_business_period(
    start_year=2021,
    end_year=2023,
    business_type='software_consultancy'
)
```

### Custom Growth Scenario
```python
config = {
    'start_year': 2021,
    'end_year': 2023,
    'monthly_revenue_base': 25000,  # £25K starting revenue
    'annual_growth_rate': 20,       # 20% YoY growth
    'international_percentage': 40,  # 40% international sales
    'initial_staff': 2,             # 2 founders
    'final_staff': 8,               # Growth to 8 people
    'major_asset_purchases': {
        '2021-Q2': {'office_equipment': 15000},
        '2022-Q1': {'company_car': 25000},
        '2023-Q3': {'server_infrastructure': 8000}
    }
}
generator = TestDataGenerator('accounts/accounts2.gnucash', config)
generator.generate_realistic_business()
```

### Specific Test Scenarios
```python
# VAT edge cases and compliance testing
generator.generate_vat_test_scenarios()

# Year-end closing and dividend scenarios
generator.generate_year_end_procedures()

# International trading scenarios
generator.generate_export_import_scenarios()

# Asset depreciation and disposal
generator.generate_asset_lifecycle_scenarios()
```

## File Output

### Generated Files
- `business_data_YYYY-YYYY.gnucash`: Multi-year GnuCash file
- `transactions_YYYY-YYYY.csv`: Complete transaction export
- `vat_returns_YYYY-YYYY.json`: Quarterly VAT return data
- `financial_summary_YYYY-YYYY.json`: P&L, Balance Sheet summaries
- `asset_register_YYYY-YYYY.csv`: Asset purchases and depreciation
- `payroll_summary_YYYY-YYYY.csv`: Employment cost breakdown

### Backup Strategy
- Original files are never modified
- All generated files include timestamps
- Previous test data files are preserved

## Testing Integration

### Comprehensive Business Testing
- **VAT Compliance**: Realistic VAT returns with known expected values
- **Corporation Tax**: Annual CT600 calculations with supporting data
- **Statutory Accounts**: Companies House filings with proper classifications
- **Payroll Compliance**: RTI submissions, P11Ds, and employment costs
- **Asset Management**: Capital allowances and depreciation calculations
- **International Trade**: Export documentation and place of supply rules

### Edge Case Scenarios
- **Brexit Transition**: VAT rule changes from 2021
- **COVID-19 Impact**: Furlough schemes, grants, and economic disruption
- **Large Transaction Testing**: Above VAT threshold purchases and sales
- **Error Correction**: VAT error corrections and adjustments
- **Bad Debt Relief**: VAT relief on unpaid invoices
- **Asset Disposals**: Capital gains and VAT on asset sales

### Audit Trail Compliance
- **Deterministic Generation**: Reproducible results with fixed seeds
- **Supporting Documentation**: Realistic invoice numbers and references
- **Chronological Integrity**: Proper date sequencing and period boundaries
- **Cross-Reference Validation**: Transaction matching across accounts

## Implementation Notes

### Dependencies
- piecash >= 1.1.0
- python-dateutil for date handling
- decimal for precise currency calculations

### Performance Considerations
- Batch transaction creation for large datasets
- Progress indicators for long-running generation
- Memory-efficient processing for large date ranges

### Error Handling
- Graceful handling of missing accounts
- Rollback capability for failed generations
- Detailed logging of generation process