# SageMaker Studio Run-on-Start Lambda

In this example, we show a way to **automatically install** the [Auto-shutdown extension](https://github.com/aws-samples/sagemaker-studio-auto-shutdown-extension) for SageMaker Studio - each time a user re/starts their JupyterServer app: Similarly to how an on-start [lifecycle configuration script](https://docs.aws.amazon.com/sagemaker/latest/dg/notebook-lifecycle-config.html) can perform setup actions in a SageMaker classic Notebook Instance.

The stack template deploys:

- A Python Lambda function to log in and run the commands as the user through terminal
- A new CloudTrail and associated EventBridge rules to monitor `CreateApp` events for app type `JupyterServer`, and trigger the Lambda appropriately


## Caveats and limitations

While this is hopefully a useful example, it's worth noting that:

- We deliberately hard-coded the command script in the Lambda... If you want to support arbitrary code via function parameters, make sure you have strong controls on what sources have permissions to invoke the function!
- The function is only triggered when the `CreateApp` call is logged - meaning that:
  - Commands will typically run **concurrently with the user** logging in... Unlike a lifecycle configuration script which would complete **before** the user gets access to Jupyter.
  - The Lambda must **wait for the JupyterServer app to become ready**... So the amount of runtime available before the 15 minute Lambda timeout terminates execution is variable - unlike the static 5 minute limit on lifecycle configuration scripts.
- The function runs the commands **via a terminal** - meaning that:
  - There is no built-in concept of "success" or "failure" of the commands... The function just sees what a human user would see through the console, and needs to analyse the responses accordingly if this is important
  - You might want to package your commands in a script file and run them as one transaction through the terminal?
- As written, the function **logs all terminal output to CloudWatch** - so particularly verbose scripts (like the install we demonstrate) may have high log volume.


## Setup

You'll need:

- Sufficient access to your AWS account to deploy the stack, configured through the [AWS CLI](https://aws.amazon.com/cli/)
- Installed [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) and [Docker](https://www.docker.com/products/docker-desktop) (which we use below to [build a Lambda bundle with dependencies](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html), rather than manual installation & archiving)

Once you have those, you're ready to:

- Build the Lambda bundle:

```
sam build --use-container --template template.sam.yaml
```

- Stage the assets to an S3 bucket:

```
export DEPLOYMENT_BUCKET_NAME=YOUR_BUCKET_NAME
export DEPLOYMENT_BUCKET_PREFIX=IF_YOU_WANT_ONE

sam package --s3-bucket $DEPLOYMENT_BUCKET_NAME --s3-prefix $DEPLOYMENT_BUCKET_PREFIX --output-template-file template.tmp.yaml
```

- Deploy the compiled CloudFormation template using the assets:

```
sam deploy --template-file template.tmp.yaml --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset --stack-name smstudio-lambda
```
