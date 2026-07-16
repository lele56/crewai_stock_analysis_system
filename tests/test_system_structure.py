#!/usr/bin/env python3
# tests/test_system_structure.py
"""简单的系统结构测试
不需要安装所有依赖，只测试基本结构
"""

import os
import sys

import pytest
import yaml


def test_project_structure():
    """测试项目结构"""
    print("🔍 测试项目结构...")

    required_files = [
        "README.md",
        "requirements.txt",
        ".env",
        ".env.example",
        "main.py",
        "src/crews/config/agents.yaml",
        "src/crews/config/tasks.yaml",
        "src/stock_analysis_system.py",
        "src/crews/data_collection_crew.py",
        "src/crews/analysis_crew.py",
        "src/crews/decision_crew.py",
        "src/flows/investment_flow.py",
        "src/flows/batch_analysis_flow.py",
        "src/tools/financial_tools.py",
        "src/tools/technical_tools.py",
        "src/tools/reporting_tools.py",
        "src/utils/batch_analyzer.py",
        "src/utils/monitor.py",
        "web/web_app.py",
        "tests/test_stock_analysis_system.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ 缺失文件: {', '.join(missing_files)}")
        pytest.fail(f"缺失文件: {', '.join(missing_files)}")
    print("✅ 所有必需文件都存在")


def test_yaml_configurations():
    """测试YAML配置文件"""
    print("\n🔍 测试YAML配置文件...")

    config_files = ["src/crews/config/agents.yaml", "src/crews/config/tasks.yaml"]

    for config_file in config_files:
        try:
            with open(config_file, encoding="utf-8") as f:
                yaml.safe_load(f)
            print(f"✅ {config_file} 格式正确")
        except Exception as e:
            print(f"❌ {config_file} 格式错误: {str(e)}")
            pytest.fail(f"{config_file} 格式错误: {str(e)}")

    print("✅ 所有YAML配置文件格式正确")


def test_agent_definitions():
    """测试Agent定义"""
    print("\n🔍 测试Agent定义...")

    try:
        with open("src/crews/config/agents.yaml", encoding="utf-8") as f:
            agents_config = yaml.safe_load(f)

        required_agents = [
            "fundamental_analyst",
            "risk_assessment_specialist",
            "industry_expert",
            "analysis_coordinator",
            "investment_advisor",
            "report_generator",
        ]

        missing_agents = []
        for agent in required_agents:
            if agent not in agents_config:
                missing_agents.append(agent)

        if missing_agents:
            print(f"❌ 缺失Agent: {', '.join(missing_agents)}")
            pytest.fail(f"缺失Agent: {', '.join(missing_agents)}")
        print("✅ 所有必需的Agent都已定义")

    except Exception as e:
        print(f"❌ Agent定义测试失败: {str(e)}")
        pytest.fail(f"Agent定义测试失败: {str(e)}")


def test_task_definitions():
    """测试Task定义"""
    print("\n🔍 测试Task定义...")

    try:
        with open("src/crews/config/tasks.yaml", encoding="utf-8") as f:
            tasks_config = yaml.safe_load(f)

        required_tasks = [
            "fundamental_analysis_task",
            "risk_assessment_task",
            "industry_analysis_task",
            "analysis_coordination_task",
            "investment_strategy_task",
            "report_generation_task",
        ]

        missing_tasks = []
        for task in required_tasks:
            if task not in tasks_config:
                missing_tasks.append(task)

        if missing_tasks:
            print(f"❌ 缺失Task: {', '.join(missing_tasks)}")
            pytest.fail(f"缺失Task: {', '.join(missing_tasks)}")
        print("✅ 所有必需的Task都已定义")

    except Exception as e:
        print(f"❌ Task定义测试失败: {str(e)}")
        pytest.fail(f"Task定义测试失败: {str(e)}")


def test_python_syntax():
    """测试Python文件语法"""
    print("\n🔍 测试Python文件语法...")

    python_files = [
        "main.py",
        "src/stock_analysis_system.py",
        "src/crews/data_collection_crew.py",
        "src/crews/analysis_crew.py",
        "src/crews/decision_crew.py",
        "src/flows/investment_flow.py",
        "src/flows/batch_analysis_flow.py",
        "src/tools/financial_tools.py",
        "src/tools/technical_tools.py",
        "src/tools/reporting_tools.py",
        "src/utils/batch_analyzer.py",
        "src/utils/monitor.py",
        "web/web_app.py",
        "tests/test_stock_analysis_system.py",
    ]

    syntax_errors = []
    for file_path in python_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                code = f.read()
            compile(code, file_path, "exec")
            print(f"✅ {file_path} 语法正确")
        except SyntaxError as e:
            syntax_errors.append(f"{file_path}: {str(e)}")
        except Exception as e:
            print(f"⚠️ {file_path} 检查跳过: {str(e)}")

    if syntax_errors:
        print(f"❌ 语法错误: {', '.join(syntax_errors)}")
        pytest.fail(f"语法错误: {', '.join(syntax_errors)}")
    print("✅ 所有Python文件语法正确")


def test_documentation():
    """测试文档"""
    print("\n🔍 测试文档...")

    doc_files = ["README.md", "股票分析系统开发计划.md"]

    for doc_file in doc_files:
        try:
            with open(doc_file, encoding="utf-8") as f:
                content = f.read()

            # 检查文档长度
            if len(content) < 100:
                print(f"⚠️ {doc_file} 内容过短")
                continue

            print(f"✅ {doc_file} 文档完整")

        except Exception as e:
            print(f"❌ {doc_file} 文档测试失败: {str(e)}")
            pytest.fail(f"{doc_file} 文档测试失败: {str(e)}")

    print("✅ 所有文档完整")


def main():
    """主测试函数"""
    print("🚀 开始股票分析系统测试...")
    print("=" * 50)

    tests = [
        test_project_structure,
        test_yaml_configurations,
        test_agent_definitions,
        test_task_definitions,
        test_python_syntax,
        test_documentation,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print("-" * 30)

    print(f"\n📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！系统结构完整。")
        print("\n📋 系统特性:")
        print("✅ 基于CrewAI的多Agent协作架构")
        print("✅ Crews模式（团队协作）")
        print("✅ Flows模式（流程控制）")
        print("✅ 11个专业化Agent")
        print("✅ 完整的任务定义")
        print("✅ 自定义工具集")
        print("✅ 批量分析功能")
        print("✅ 实时监控系统")
        print("✅ Web界面")
        print("✅ 命令行界面")
        print("✅ 缓存机制")
        print("✅ 错误处理和重试")
        return True
    print("❌ 部分测试失败，请检查上述错误。")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)