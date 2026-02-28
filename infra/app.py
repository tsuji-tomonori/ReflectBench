#!/usr/bin/env python3

import aws_cdk as cdk
from stacks.experiment_stack import ExperimentStack

app = cdk.App()

ExperimentStack(
    app,
    "ExperimentStack",
    env=cdk.Environment(region="ap-southeast-2"),
)

app.synth()
