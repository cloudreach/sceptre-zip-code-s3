import hashlib, os, subprocess, zipfile
from base64 import b64encode
from sceptre.hooks import Hook
from sceptre.resolvers import Resolver
from botocore.exceptions import ClientError
from datetime import datetime
from shutil import rmtree
try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'wb')

try:
    from StringIO import StringIO as BufferIO
except ImportError:
    from io import BytesIO as BufferIO

try:
    import zlib

    compression = zipfile.ZIP_DEFLATED
except ImportError:
    compression = zipfile.ZIP_STORED


class S3Package(Hook):
    NAME = "s3_package"
    TARGET = "dist"
    DELIMITER = "^^"

    def __init__(self, *args, **kwargs):
        super(S3Package, self).__init__(*args, **kwargs)

    def run(self):
        if self.DELIMITER in self.argument:
            fn_root_dir, s3_object = self.argument.split(self.DELIMITER, 1)
            s3_bucket, s3_key = s3_object.split("/", 1)
            self.logger.debug(
                "[{}] S3 bucket/key parsed from the argument".format(self.NAME)
            )
        elif "sceptre_user_data" in self.stack_config:
            code = self.stack_config.get("sceptre_user_data").get("Code", {})
            fn_root_dir, s3_bucket, s3_key = [
                self.argument,
                code.get("S3Bucket"),
                code.get("S3Key"),
            ]
            self.logger.debug(
                "[{}] S3 bucket/key parsed from sceptre_user_data['Code']".format(
                    self.NAME
                )
            )
        else:
            raise Exception(
                "S3 bucket/key could not be parsed nor from the argument, neither from sceptre_user_data['Code']"
            )

        if isinstance(s3_bucket, Resolver):
            s3_bucket = s3_bucket.resolve()
            self.logger.debug("[{}] resolved S3 bucket value to {}".format(self.NAME, s3_bucket))

        if isinstance(s3_key, Resolver):
            s3_key = s3_key.resolve()
            self.logger.debug("[{}] resolved S3 key value to {}".format(self.NAME, s3_key))

        fn_dist_dir = os.path.join(fn_root_dir, self.TARGET)

        command = 'make -C {}'.format(fn_root_dir)

        self.logger.info(
            "Making dependencies with '{}' command, output hidden.".format(command)
        )

        p = subprocess.Popen([command], shell = True, stdout = DEVNULL, stderr = DEVNULL)
        p.wait()

        if p.returncode != 0:
            raise Exception("Failed to make dependencies, debug command manually.")

        self.logger.debug(
            "[{}] reading ALL files from {}/ directory".format(self.NAME, fn_dist_dir)
        )

        files = sorted(
            [
                os.path.join(root[len(fn_dist_dir) + 1 :], file)
                for root, _, files in os.walk(fn_dist_dir)
                for file in files
            ]
        )

        buffer = BufferIO()

        # static timestamp to keep same ZIP checksum on same files
        static_ts = int(datetime(2018, 1, 1).strftime("%s"))

        with zipfile.ZipFile(buffer, mode="w", compression=compression) as f:
            for file in files:
                real_file = os.path.join(fn_dist_dir, file)
                self.logger.debug("[{}] zipping file {}".format(self.NAME, real_file))
                os.utime(real_file, (static_ts, static_ts))
                f.write(real_file, arcname=file)

        rmtree(fn_dist_dir)

        buffer.seek(0)
        content = buffer.read()

        md5 = hashlib.new("md5")
        md5.update(content)

        try:
            self.connection_manager.call(
                service="s3",
                command="head_object",
                kwargs={
                    "Bucket": s3_bucket,
                    "Key": s3_key,
                    "IfMatch": '"{}"'.format(md5.hexdigest()),
                },
            )

            self.logger.info(
                "[{}] skip packaging {} - no changes detected".format(
                    self.NAME, fn_dist_dir
                )
            )
        except ClientError as e:
            if e.response["Error"]["Code"] not in ["404", "412"]:
                raise e

            self.logger.info(
                "[{}] uploading {} to s3://{}/{}".format(
                    self.NAME, fn_dist_dir, s3_bucket, s3_key
                )
            )

            result = self.connection_manager.call(
                service="s3",
                command="put_object",
                kwargs={
                    "Bucket": s3_bucket,
                    "Key": s3_key,
                    "Body": content,
                    "ContentMD5": b64encode(md5.digest()).strip().decode("utf-8"),
                },
            )

            self.logger.debug(
                "[{}] object s3://{}/{} new version: {}".format(
                    self.NAME, s3_bucket, s3_key, result.get("VersionId")
                )
            )
