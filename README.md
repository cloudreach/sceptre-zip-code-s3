# Sceptre zip-code-s3

Hook and resolver for [Sceptre](https://sceptre.cloudreach.com/latest/) `v1.3.4+` to package complex Lambda functions on-the-fly and deploy them using S3 bucket.

This solution, fully compatible with **Python 2/3**, works well for **ALL** AWS Lambda runtimes: just tune `Makefile` with your own instructions for concrete runtime.

## Overview

Lambda function may consist of several files or may require custom packages,
which do not exist in AWS runtime and must be installed manually before packaging.

Many developers tend to store packaged Zip archive within Git repository.
That may lead to inconsistent deployment, because
such archive has to be recreate, if any source or dependency file has changed.

This important action usually recalled after hours of debugging and tons of redeployments.
Therefore, such archived artifacts should never be checked in, rather packaged and deployed to on-the-fly.

## Getting Started

### How To install

`NB!` _Sceptre `1.x` does not yet recognize `entry_points` installation option from `pip` setup manifesto._
_Therefore, it's not possible to install it using `pip`_.

* Clone the repository locally:

    ```bash
    $ git clone git@github.com:cloudreach/sceptre-zip-code-s3.git
    ```

* Install required dependencies:

    ```bash
    $ cd sceptre-zip-code-s3
    $ make deps
    ```

* Setup plugins to existing Sceptre project:

    ```bash
    $ make plugins TARGET=<existing_sceptre_project_root>
    ```

To display available commands, run `make` or `make help` command.

### Prepare project

* Update `config/config.yaml` file with preferred values:

    ```bash
    $ cp config/config.yaml.dist config/config.yaml
    $ vi config/config.yaml
    ```

### Create S3 bucket

* Create new `S3` bucket for artifacts deployments:

    ```bash
    $ sceptre launch-env example/storage
    ```

    `NB!` _It's possible to refer existing bucket, with enabled **Versioning** support._

### Deploy Lambdas:

* Deploy whole environment at once:

    ```bash
    $ sceptre launch-env example/serverless
    ```

* Or deploy stacks one by one:

    ```bash
    $ sceptre launch-stack example/serverless lambda-role
    $ sceptre launch-stack example/serverless lambda-py2-deps
    $ sceptre launch-stack example/serverless lambda-py3-deps
    ```

This is what have been done (per function):

- install function required dependencies
- prepare files for distribution
- package and deploy artifact to S3 bucket, if checksum differs
- update CloudFormation stack with `latest` version of S3 file
- remove distribution directory

### Test Lambda function from CLI

Find generated function name and region:

```bash
$ LAMBDA=( $(sceptre describe-stack-outputs example/serverless lambda-py2-deps \
    | grep ':lambda:' \
    | awk -F: '{print $NF, $5}') )
```

And then invoke function with JSON payload and parse result file:

```bash
$ aws lambda invoke \
    --invocation-type RequestResponse \
    --function-name "${LAMBDA[0]}" \
    --region "${LAMBDA[1]}" \
    --payload '{"key1":"value-1", "key2":[21, 42], "key3":[{"name":"value-3"}]}' \
    output.txt

$ cat output.txt | xargs echo -e
```

If everything went well, output would be like that:

```yaml
helper: Hello from Python 2.7.12
key1: value-1
key2: [21, 42]
key3:
- {name: value-3}
```

### Cleanup infrastructure

* Do not forget to cleanup infrastructure after testing:

    ```bash
    $ sceptre delete-env example/serverless
    ```

* If new S3 bucket was created during the test:

    ```bash
    $ sceptre delete-env example/storage
    ```

    If it errors with `You must delete all versions in the bucket`, then:

    ```bash
    $ MY_BUCKET="$(awk '$1 == "artifacts_bucket:" {print $2}' config/config.yaml)"

    $ python -c "import boto3; boto3.resource('s3').Bucket('${MY_BUCKET}').object_versions.delete()"

    $ sceptre delete-env example/storage
    ```

## Under the hood

### Hook definition

`s3_package` hook is template agnostic solution and it has 2 forms of definitions:

* S3 bucket/key auto-discovery:

    This way hook tries to auto-discover `S3Bucket`/`S3Key` values from `sceptre_user_data['Code']` config.

    Template & config must follow [lambda_function.py](./templates/example/lambda_function.py) template convention for `Code` parameter.

    ```yaml
    hooks:
        before_create:
            - !s3_package <path-to-function-root>
        before_update:
            - !s3_package <path-to-function-root>
    ```

* S3 bucket/key passed directly, fallback for custom template:

    ```yaml
    hooks:
        before_create:
            - !s3_package <path-to-function-root>^^<s3_bucket>/<s3_key>
        before_update:
            - !s3_package <path-to-function-root>^^<s3_bucket>/<s3_key>
    ```

### Resolver definition

`Cloudformation` wont detect stack changes, if no `Code.S3ObjectVersion` key is provided and lambda wont be redeployed with updates.

As hook definition, resolver also has **auto-discovery** and **direct** modes.

* S3 bucket/key auto-discovery:

    ```yaml
    sceptre_user_data:
        Code:
            S3Bucket: <s3_bucket>
            S3Key: <s3_key>
            S3ObjectVersion: !s3_version
    ```

* S3 bucket/key passed directly, fallback for custom template:

    ```yaml
    sceptre_user_data:
        BucketName: <s3_bucket>
        ObjectKey: <s3_key>
        ObjectVersion: !s3_version <s3_bucket>/<s3_key>
    ```

* S3 bucket/key names come from another stack:

    ```yaml
    sceptre_user_data:
        Code:
            S3Bucket: !stack_output my-other-stack::BucketName
            S3Key: !stack_output my-other-stack::KeyName
            S3ObjectVersion: !s3_version
    ```

### Function Makefile

Each function has own `Makefile` file inside it's root.

Why `make`, you might ask. Because it's cross-platform tool, proven with years.

**Important!** Instructions and logic in `Makefile` are outside of `s3_package` responsibility.
Hook does not know what and how should be installed, except one rule:

> All files for packaging should be placed into `dist` directory, inside function root.

Sample `Makefile` for `Python 2.7` Lambda with dependencies installed with `pip`:

```make
SHELL := bash
TARGET := dist

# Runtime: Python 2.7
PIP := pip2
SOURCES := $(wildcard *.py)

.PHONY: all
all:
	@ rm -rf $(TARGET) && mkdir -p $(TARGET)

	@ printf '[install]\nprefix=\n' > setup.cfg # OSX hack
	$(PIP) install -U -t $(TARGET) -r requirements.txt | grep -i 'installed'

	/bin/cp -f $(SOURCES) $(TARGET)/

	@ rm -rf setup.cfg $(TARGET)/*.so $(TARGET)/*.dist-info $(TARGET)/*.eggs $(TARGET)/*.egg-info
	@ find $(TARGET) -type f -name "*.py[cod]" -delete

	# Files for distribution:
	@ cd $(TARGET); find . -type f | sort -V | sed -e 's,^\./,  ,'
```

Explanation:

- variable `TARGET := dist` is convention over configuration, which defines distribution directory.

  _It should not be changed, otherwise hook `s3_package` won't find files for packaging._

- re-/create `dist` directory, to avoid distribution pollution
- apply OS X hack to allow `pip` install packages into alternative directory
- install dependencies with `pip` into `dist` directory
- copy all `*.py` source files into `dist` directory
- remove unattended files from `dist` directory

Feel free to adjust `Makefile` as you like, e.g., use `Docker` to build, just pay attention to `/dist/` directory.

#### Caveats

- note that Sceptre `v1.3.4` was tested only and it may misbehave on previous versions.
- when running `Sceptre` from OSX, some packages may contain binary inside, so be sure to upload the proper one.

## How to Contribute

We encourage contribution to our projects, please see our [CONTRIBUTING](CONTRIBUTING.md) guide for details.

## License

**sceptre-zip-code-s3** is licensed under the [Apache Software License 2.0](LICENSE.md).

## Thanks

Keep It Cloudy ([@CloudreachKIC](https://twitter.com/cloudreachkic))
