from pathlib import Path

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_apigatewayv2 as apigwv2,
)
from aws_cdk import (
    aws_apigatewayv2_integrations as apigwv2_integrations,
)
from aws_cdk import (
    aws_dynamodb as dynamodb,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from aws_cdk import (
    aws_s3 as s3,
)
from constructs import Construct


class ExperimentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repo_root = Path(__file__).resolve().parents[2]

        artifacts_bucket = s3.Bucket(
            self,
            "ArtifactsBucket",
            bucket_name="llm-temp-introspection-artifacts",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        run_control_table = dynamodb.Table(
            self,
            "RunControlTable",
            table_name="run_control_table",
            partition_key=dynamodb.Attribute(name="run_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
        )
        run_control_table.add_global_secondary_index(
            index_name="idempotency_key_index",
            partition_key=dynamodb.Attribute(
                name="idempotency_key",
                type=dynamodb.AttributeType.STRING,
            ),
        )

        orchestrator_fn = lambda_.Function(
            self,
            "OrchestratorFn",
            function_name="orchestrator_fn",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(repo_root / "app" / "orchestrator")),
            timeout=Duration.minutes(5),
            environment={
                "TABLE_NAME": run_control_table.table_name,
                "ARTIFACTS_BUCKET": artifacts_bucket.bucket_name,
            },
        )

        start_run_fn = lambda_.Function(
            self,
            "StartRunFn",
            function_name="start_run_fn",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(repo_root / "app" / "start_run")),
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": run_control_table.table_name,
                "TABLE_GSI_NAME": "idempotency_key_index",
                "ARTIFACTS_BUCKET": artifacts_bucket.bucket_name,
                "ORCHESTRATOR_ARN": orchestrator_fn.function_arn,
            },
        )

        status_fn = lambda_.Function(
            self,
            "StatusFn",
            function_name="status_fn",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(repo_root / "app" / "status")),
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": run_control_table.table_name,
            },
        )

        artifacts_fn = lambda_.Function(
            self,
            "ArtifactsFn",
            function_name="artifacts_fn",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(repo_root / "app" / "artifacts")),
            timeout=Duration.seconds(30),
            environment={
                "ARTIFACTS_BUCKET": artifacts_bucket.bucket_name,
            },
        )

        run_control_table.grant_read_write_data(start_run_fn)
        run_control_table.grant_read_write_data(orchestrator_fn)
        run_control_table.grant_read_data(status_fn)
        artifacts_bucket.grant_read_write(start_run_fn)
        artifacts_bucket.grant_read_write(orchestrator_fn)
        artifacts_bucket.grant_read(status_fn)
        artifacts_bucket.grant_read(artifacts_fn)
        orchestrator_fn.grant_invoke(start_run_fn)

        http_api = apigwv2.HttpApi(self, "RunsApi", api_name="runs-api")
        http_api.add_routes(
            path="/runs",
            methods=[apigwv2.HttpMethod.POST],
            integration=apigwv2_integrations.HttpLambdaIntegration(
                "StartRunIntegration", handler=start_run_fn
            ),
        )
        http_api.add_routes(
            path="/runs/{run_id}",
            methods=[apigwv2.HttpMethod.GET],
            integration=apigwv2_integrations.HttpLambdaIntegration(
                "StatusIntegration", handler=status_fn
            ),
        )
        http_api.add_routes(
            path="/runs/{run_id}/artifacts",
            methods=[apigwv2.HttpMethod.GET],
            integration=apigwv2_integrations.HttpLambdaIntegration(
                "ArtifactsIntegration", handler=artifacts_fn
            ),
        )
