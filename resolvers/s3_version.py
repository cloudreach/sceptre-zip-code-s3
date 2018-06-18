from sceptre.resolvers import Resolver


class S3Version(Resolver):
    NAME = "s3_version"

    def __init__(self, *args, **kwargs):
        super(S3Version, self).__init__(*args, **kwargs)

    def resolve(self):
        if self.argument:
            s3_bucket, s3_key = self.argument.split("/", 1)
            self.logger.debug(
                "[{}] S3 bucket/key parsed from the argument".format(self.NAME)
            )
        elif "sceptre_user_data" in self.stack_config:
            code = self.stack_config.get("sceptre_user_data").get("Code", {})
            s3_bucket, s3_key = [code.get("S3Bucket"), code.get("S3Key")]
            self.logger.debug(
                "[{}] S3 bucket/key parsed from sceptre_user_data['Code']".format(
                    self.NAME
                )
            )
        else:
            raise Exception(
                "S3 bucket/key could not be parsed nor from the argument, neither from sceptre_user_data['Code']"
            )

        result = self.connection_manager.call(
            service="s3",
            command="head_object",
            kwargs={"Bucket": s3_bucket, "Key": s3_key},
        )

        version_id = result.get("VersionId")

        self.logger.debug(
            "[{}] object s3://{}/{} latest version: {}".format(
                self.NAME, s3_bucket, s3_key, version_id
            )
        )

        return version_id
