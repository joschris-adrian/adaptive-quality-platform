import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.analytics.comparison import QualityCostComparator
from services.analytics.reporter   import ComparisonReporter

reporter = ComparisonReporter()

print(reporter.strategy_summary(total_events=10_000))
print()
print(reporter.threshold_table(total_events=10_000))
print()
print(reporter.budget_report(total_events=10_000, budget=5_000.00))