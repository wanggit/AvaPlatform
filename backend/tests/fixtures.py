"""测试数据夹具：重置平台目录、模型、知识源和岗位模板。"""

from app.schemas import (
    CredentialRead,
    DepartmentRead,
    JobTemplateEvaluationRead,
    JobTemplateVersionRead,
    KnowledgeConnectionRead,
    KnowledgeSourceRead,
    ModelConfigurationRead,
)
from app.services import reset_store, store


def reset_with_catalog() -> None:
    reset_store()
    store.secret_values.update({
        "secret-cred-deepseek": "test-secret",
        "secret-cred-ragflow": "test-ragflow-secret",
    })
    store.credentials.update({
        "cred-deepseek": CredentialRead(
            id="cred-deepseek",
            name="DeepSeek 测试密钥",
            owner_type="platform",
            owner_id="platform",
            owner_name="Platform",
            secret_ref="secret-cred-deepseek",
            secret_mask="te***et",
        ),
        "cred-ragflow": CredentialRead(
            id="cred-ragflow",
            name="RAGFlow 测试密钥",
            owner_type="integration",
            owner_id="ragflow",
            owner_name="RAGFlow",
            secret_ref="secret-cred-ragflow",
            secret_mask="te***et",
        ),
    })
    store.model_configurations["model-deepseek-v4-pro"] = ModelConfigurationRead(
        id="model-deepseek-v4-pro",
        name="DeepSeek V4 Pro",
        model_type="large_language_model",
        provider="deepseek",
        base_url="https://api.deepseek.com",
        api_key="sk-test-deepseek",
        model_name="deepseek-v4-pro",
        context_window=128_000,
        enabled=True,
    )
    store.departments.update({
        "dept-customer-service": DepartmentRead(id="dept-customer-service", name="客服部", description="测试部门"),
        "dept-sales": DepartmentRead(id="dept-sales", name="销售部", description="测试部门"),
        "dept-hr": DepartmentRead(id="dept-hr", name="人力资源部", description="测试部门"),
    })
    store.knowledge_connections["kc-ragflow-dev"] = KnowledgeConnectionRead(
        id="kc-ragflow-dev",
        name="RAGFlow",
        provider="ragflow",
        base_url="http://127.0.0.1:8080",
        credential_id="cred-ragflow",
    )
    store.knowledge_sources.update({
        "ks-faq": KnowledgeSourceRead(
            id="ks-faq",
            connection_id="kc-ragflow-dev",
            external_id="support_faq",
            display_name="FAQ库",
            source_type="dataset",
            authorization_scope=["dept-customer-service"],
        ),
        "ks-refund-policy": KnowledgeSourceRead(
            id="ks-refund-policy",
            connection_id="kc-ragflow-dev",
            external_id="refund_policy",
            display_name="退款政策",
            source_type="dataset",
            authorization_scope=["dept-customer-service"],
        ),
        "ks-sales-playbook": KnowledgeSourceRead(
            id="ks-sales-playbook",
            connection_id="kc-ragflow-dev",
            external_id="sales_playbook",
            display_name="销售作战手册",
            source_type="dataset",
            authorization_scope=["dept-sales"],
        ),
        "ks-hiring-policy": KnowledgeSourceRead(
            id="ks-hiring-policy",
            connection_id="kc-ragflow-dev",
            external_id="hiring_policy",
            display_name="招聘制度",
            source_type="dataset",
            authorization_scope=["dept-hr"],
        ),
    })
    passed_eval = JobTemplateEvaluationRead(
        job_template_version_id="jtv-customer-support-v1",
        status="passed",
        score=91,
        case_count=1,
        passed_case_count=1,
        evaluator="测试",
        summary="测试模板通过。",
        cases=[{
            "title": "客服测试用例",
            "input_payload": {},
            "expected_result": "通过",
            "actual_result": "通过",
            "status": "passed",
        }],
    )
    store.template_versions.update({
        "jtv-customer-support-v1": JobTemplateVersionRead(
            id="jtv-customer-support-v1",
            role="客服工单协调员工",
            version="1.0.0",
            grade="Staff",
            department_id="dept-customer-service",
            model_config_id="model-deepseek-v4-pro",
            description="测试模板",
            system_prompt="你是客服工单协调员工。",
            max_goal_risk_level="L3",
            default_goal_budget_tokens=160_000,
            tools=["knowledge_base"],
            knowledge_sources=["ks-faq", "ks-refund-policy"],
            metric_bindings=[{"name": "投诉一次解决率", "target_value": ">= 85%"}],
            is_pilot=True,
            pilot_scenario="测试场景",
            status="published",
            evaluation=passed_eval,
        ),
        "jtv-sales-draft-v1": JobTemplateVersionRead(
            id="jtv-sales-draft-v1",
            role="销售方案协作员工",
            version="0.1.0",
            grade="Staff",
            department_id="dept-sales",
            model_config_id="model-deepseek-v4-pro",
            description="测试草稿模板",
            system_prompt="你是销售方案协作员工。",
            status="draft",
            evaluation=JobTemplateEvaluationRead(job_template_version_id="jtv-sales-draft-v1", status="failed"),
        ),
        "jtv-sales-pilot-v1": JobTemplateVersionRead(
            id="jtv-sales-pilot-v1",
            role="销售方案协作员工",
            version="1.0.0",
            grade="Staff",
            department_id="dept-sales",
            model_config_id="model-deepseek-v4-pro",
            description="测试模板",
            system_prompt="你是销售方案协作员工。",
            knowledge_sources=["ks-sales-playbook"],
            metric_bindings=[{"name": "方案初稿采纳率", "target_value": ">= 60%"}],
            is_pilot=True,
            pilot_scenario="测试场景",
            status="published",
            evaluation=JobTemplateEvaluationRead(
                job_template_version_id="jtv-sales-pilot-v1",
                status="passed",
                score=88,
                case_count=1,
                passed_case_count=1,
                cases=[{"title": "销售测试用例", "expected_result": "通过", "status": "passed"}],
            ),
        ),
        "jtv-hr-pilot-v1": JobTemplateVersionRead(
            id="jtv-hr-pilot-v1",
            role="招聘初筛协作员工",
            version="1.0.0",
            grade="Staff",
            department_id="dept-hr",
            model_config_id="model-deepseek-v4-pro",
            description="测试模板",
            system_prompt="你是招聘初筛协作员工。",
            knowledge_sources=["ks-hiring-policy"],
            metric_bindings=[{"name": "筛选摘要复核通过率", "target_value": ">= 90%"}],
            is_pilot=True,
            pilot_scenario="测试场景",
            status="published",
            evaluation=JobTemplateEvaluationRead(
                job_template_version_id="jtv-hr-pilot-v1",
                status="passed",
                score=90,
                case_count=1,
                passed_case_count=1,
                cases=[{"title": "招聘测试用例", "expected_result": "通过", "status": "passed"}],
            ),
        ),
    })
