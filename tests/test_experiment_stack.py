import pytest


aws_cdk = pytest.importorskip("aws_cdk")


def test_orchestrator_version_is_retained(monkeypatch: pytest.MonkeyPatch) -> None:
    from aws_cdk import Environment
    from aws_cdk import aws_lambda as lambda_
    from aws_cdk.assertions import Template

    from infra.stacks.experiment_stack import ExperimentStack

    def fake_from_asset(*_args, **_kwargs):
        return lambda_.Code.from_inline("def handler(event, context):\n    return {}\n")

    monkeypatch.setattr(lambda_.Code, "from_asset", staticmethod(fake_from_asset))

    app = aws_cdk.App()
    stack = ExperimentStack(app, "ExperimentStack", env=Environment(region="ap-southeast-2"))
    template = Template.from_stack(stack).to_json()

    version_resources = [
        resource
        for logical_id, resource in template["Resources"].items()
        if logical_id.startswith("OrchestratorFnCurrentVersion")
    ]

    assert len(version_resources) == 1
    assert version_resources[0]["DeletionPolicy"] == "Retain"
    assert version_resources[0]["UpdateReplacePolicy"] == "Retain"


def test_repair_route_is_defined(monkeypatch: pytest.MonkeyPatch) -> None:
    from aws_cdk import Environment
    from aws_cdk import aws_lambda as lambda_
    from aws_cdk.assertions import Template

    from infra.stacks.experiment_stack import ExperimentStack

    def fake_from_asset(*_args, **_kwargs):
        return lambda_.Code.from_inline("def handler(event, context):\n    return {}\n")

    monkeypatch.setattr(lambda_.Code, "from_asset", staticmethod(fake_from_asset))

    app = aws_cdk.App()
    stack = ExperimentStack(app, "ExperimentStackRepair", env=Environment(region="ap-southeast-2"))
    template = Template.from_stack(stack).to_json()

    route_keys = {
        resource["Properties"]["RouteKey"]
        for resource in template["Resources"].values()
        if resource["Type"] == "AWS::ApiGatewayV2::Route"
    }

    assert "POST /runs/{run_id}/repairs" in route_keys


def test_orchestrator_role_allows_direct_bedrock_invoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aws_cdk import Environment
    from aws_cdk import aws_lambda as lambda_
    from aws_cdk.assertions import Template

    from infra.stacks.experiment_stack import ExperimentStack

    def fake_from_asset(*_args, **_kwargs):
        return lambda_.Code.from_inline("def handler(event, context):\n    return {}\n")

    monkeypatch.setattr(lambda_.Code, "from_asset", staticmethod(fake_from_asset))

    app = aws_cdk.App()
    stack = ExperimentStack(app, "ExperimentStackInvoke", env=Environment(region="ap-southeast-2"))
    template = Template.from_stack(stack).to_json()

    orchestrator_policy = next(
        resource["Properties"]["PolicyDocument"]
        for logical_id, resource in template["Resources"].items()
        if logical_id.startswith("OrchestratorFnServiceRoleDefaultPolicy")
    )

    statements = orchestrator_policy["Statement"]
    action_sets = [
        statement["Action"] if isinstance(statement["Action"], list) else [statement["Action"]]
        for statement in statements
    ]

    assert any("bedrock:InvokeModel" in actions for actions in action_sets)
    assert any("bedrock:InvokeModelWithResponseStream" in actions for actions in action_sets)


def test_repair_run_function_has_extended_timeout_for_direct_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aws_cdk import Environment
    from aws_cdk import aws_lambda as lambda_
    from aws_cdk.assertions import Template

    from infra.stacks.experiment_stack import ExperimentStack

    def fake_from_asset(*_args, **_kwargs):
        return lambda_.Code.from_inline("def handler(event, context):\n    return {}\n")

    monkeypatch.setattr(lambda_.Code, "from_asset", staticmethod(fake_from_asset))

    app = aws_cdk.App()
    stack = ExperimentStack(app, "ExperimentStackRepairSizing", env=Environment(region="ap-southeast-2"))
    template = Template.from_stack(stack).to_json()

    repair_fn = next(
        resource["Properties"]
        for resource in template["Resources"].values()
        if resource["Type"] == "AWS::Lambda::Function"
        and resource["Properties"].get("FunctionName") == "repair_run_fn"
    )

    assert repair_fn["Timeout"] == 900
    assert repair_fn["MemorySize"] == 1024
