# D:\Projects\NextMove\tests\decomposer_test.py

import pprint
from components.analyzer_and_decomposer.query_decomposer import prepare_federated_queries

# -----------------------------
# 🔹 Test Inputs: Invalid SQL Queries
# -----------------------------
test_queries = [
    {
        "original_query": "Find remote entry-level data analyst jobs in Bangalore",
        "sql_query": "SELECT title, company_name, location FROM jobs WHERE location = 'Bangalor'",  # typo 'Bangalor'
        "unstructured_query": "Describe data analyst roles in Bangalore"
    },
    {
        "original_query": "Show all senior marketing jobs in New York with salary > 100k",
        "sql_query": "SELECT title, company_name, location, salary FROM job_posts WHERE loc = 'New Yrk' AND salary > 100000",  # typo 'New Yrk', wrong column 'loc'
        "unstructured_query": "Explain the typical responsibilities of a senior marketing role."
    }
]

# -----------------------------
# 🔹 Run Decomposer for Each Test Query
# -----------------------------
for idx, invalid_analyzer_result in enumerate(test_queries, start=1):
    print(f"\n=== Running Decomposer Test Query #{idx} ===")
    try:
        result = prepare_federated_queries(
            analyzed_result=invalid_analyzer_result,
            max_retries=3,
            use_llm_retry=True,
        )

        print(f"\n=== Decomposer Test Result #{idx} ===")
        pprint.pprint(result)

    except Exception as e:
        print(f"\n❌ Decomposer test failed for Query #{idx}: {e}")
