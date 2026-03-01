from pathlib import Path

from aws_cdk import BundlingOptions, CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as apigwv2_integrations
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sns as sns
from constructs import Construct


class ExperimentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repo_root = Path(__file__).resolve().parents[2]
        enable_notifications = bool(self.node.try_get_context("enable_notifications"))

        lambda_code = lambda_.Code.from_asset(
            str(repo_root),
            bundling=BundlingOptions(
                image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                command=[
                    "bash",
                    "-lc",
                    "python -m pip install --no-cache-dir pydantic==2.11.9 "
                    "-t /asset-output && cp -r app /asset-output/app",
                ],
            ),
            exclude=[
                "infra/cdk.out",
                ".git",
                ".venv",
                ".mypy_cache",
                ".pytest_cache",
                ".ruff_cache",
                "tests",
                "docs",
                "reports",
                ".opencode",
                ".ai_workspace",
                ".github",
            ],
        )

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

        bedrock_batch_service_role = iam.Role(
            self,
            "BedrockBatchServiceRole",
            role_name="bedrock_batch_service_role",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Service role for Bedrock batch input and output access",
        )
        artifacts_bucket.grant_read_write(bedrock_batch_service_role)
        bedrock_batch_service_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:foundation-model/*",
                    "arn:aws:bedrock:*::inference-profile/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*:*:application-inference-profile/*",
                ],
            )
        )

        orchestrator_fn = lambda_.Function(
            self,
            "OrchestratorFn",
            function_name="orchestrator_fn",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="app.orchestrator.handler.handler",
            code=lambda_code,
            timeout=Duration.minutes(15),
            environment={
                "TABLE_NAME": run_control_table.table_name,
                "ARTIFACTS_BUCKET": artifacts_bucket.bucket_name,
                "BEDROCK_BATCH_ROLE_ARN": bedrock_batch_service_role.role_arn,
                "METRIC_NAMESPACE": "ReflectBench/Runs",
                "BATCH_DRY_RUN": "false",
                "MAX_PHASES_PER_INVOCATION": "1",
                "LEASE_SECONDS": "300",
                "SELF_ARN": "orchestrator_fn",
                "ENABLE_NOTIFICATIONS": "true" if enable_notifications else "false",
            },
        )
        orchestrator_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:CreateModelInvocationJob", "bedrock:GetModelInvocationJob"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:foundation-model/*",
                    "arn:aws:bedrock:*::inference-profile/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*:*:application-inference-profile/*",
                    "arn:aws:bedrock:*:*:model-invocation-job/*",
                ],
            )
        )
        orchestrator_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )
        orchestrator_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[bedrock_batch_service_role.role_arn],
            )
        )
        orchestrator_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[
                    f"arn:aws:lambda:{self.region}:{self.account}:function:orchestrator_fn",
                    f"arn:aws:lambda:{self.region}:{self.account}:function:orchestrator_fn:*",
                ],
            )
        )

        orchestrator_alias = lambda_.Alias(
            self,
            "OrchestratorAlias",
            alias_name="live",
            version=orchestrator_fn.current_version,
        )

        start_run_fn = lambda_.Function(
            self,
            "StartRunFn",
            function_name="start_run_fn",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="app.start_run.handler.handler",
            code=lambda_code,
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": run_control_table.table_name,
                "TABLE_GSI_NAME": "idempotency_key_index",
                "ARTIFACTS_BUCKET": artifacts_bucket.bucket_name,
                "ORCHESTRATOR_ARN": orchestrator_alias.function_arn,
                "METRIC_NAMESPACE": "ReflectBench/Runs",
            },
        )
        start_run_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        status_fn = lambda_.Function(
            self,
            "StatusFn",
            function_name="status_fn",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="app.status.handler.handler",
            code=lambda_code,
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
            handler="app.artifacts.handler.handler",
            code=lambda_code,
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
        orchestrator_alias.grant_invoke(start_run_fn)

        notification_topic = None
        if enable_notifications:
            notification_topic = sns.Topic(
                self,
                "RunNotificationTopic",
                topic_name="run-status-topic",
            )
            notification_topic.grant_publish(orchestrator_fn)
            orchestrator_fn.add_environment("SNS_TOPIC_ARN", notification_topic.topic_arn)

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

        orchestrator_failure_alarm = cloudwatch.Alarm(
            self,
            "OrchestratorFailureAlarm",
            metric=orchestrator_fn.metric_errors(period=Duration.minutes(5), statistic="sum"),
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Orchestrator lambda invocation failures",
        )
        run_duration_alarm = cloudwatch.Alarm(
            self,
            "RunDurationSLOViolation",
            metric=cloudwatch.Metric(
                namespace="ReflectBench/Runs",
                metric_name="RunDurationSec",
                statistic="max",
                period=Duration.minutes(5),
            ),
            threshold=86400,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Run duration exceeded 24 hours",
        )
        batch_failure_alarm = cloudwatch.Alarm(
            self,
            "BatchFailureRateHigh",
            metric=cloudwatch.Metric(
                namespace="ReflectBench/Runs",
                metric_name="BatchFailureRate",
                statistic="avg",
                period=Duration.minutes(5),
            ),
            threshold=2,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Batch failure rate above threshold",
        )
        parse_failure_alarm = cloudwatch.Alarm(
            self,
            "ParseFailureRateHigh",
            metric=cloudwatch.Metric(
                namespace="ReflectBench/Runs",
                metric_name="ParseFailureRate",
                statistic="avg",
                period=Duration.minutes(5),
            ),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Parse failure rate above threshold",
        )

        if notification_topic is not None:
            action = cloudwatch_actions.SnsAction(notification_topic)
            orchestrator_failure_alarm.add_alarm_action(action)
            run_duration_alarm.add_alarm_action(action)
            batch_failure_alarm.add_alarm_action(action)
            parse_failure_alarm.add_alarm_action(action)

        CfnOutput(self, "RunsApiUrl", value=http_api.api_endpoint)
        CfnOutput(self, "ArtifactsBucketName", value=artifacts_bucket.bucket_name)
        CfnOutput(self, "RunControlTableName", value=run_control_table.table_name)
        CfnOutput(self, "OrchestratorAliasArn", value=orchestrator_alias.function_arn)
