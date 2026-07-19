# scripts/check_imports.py
import sys
import traceback

sys.path.insert(0, ".")
sys.path.insert(0, "src")

tests = [
    ("task_dataclasses", "from src.tasks.task_dataclasses import AgentCapability, TaskComplexity, DynamicTask"),
    ("collective_decision", "from src.tasks.collective_decision_maker import get_decision_maker"),
    ("analysis_agents", "from src.crews.analysis_agents import create_fundamental_analyst"),
    ("analysis_tasks", "from src.crews.analysis_tasks import create_fundamental_analysis_task"),
    ("analysis_executor", "from src.crews.analysis_executor import calculate_collaboration_scores"),
    ("data_collection_crew", "from src.crews.data_collection_crew import DataCollectionCrew"),
    ("data_collection_executor", "from src.crews.data_collection_executor import collect_data_direct"),
    ("decision_tasks", "from src.crews.decision_tasks import create_investment_strategy_task"),
    ("decision_executor", "from src.crews.decision_executor import prepare_decision_inputs"),
    ("stock_analysis_system", "from src.stock_analysis_system import StockAnalysisSystem"),
    ("main", "from main import analyze_single_stock"),
]

for name, stmt in tests:
    try:
        exec(stmt)
        print(f"OK  {name}")
    except Exception as e:
        print(f"FAIL {name}: {e}")
        traceback.print_exc()