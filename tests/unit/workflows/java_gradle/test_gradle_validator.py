from unittest import TestCase

from mock import patch, Mock
from parameterized import parameterized
from aws_lambda_builders.workflows.java_gradle.gradle_validator import GradleValidator
from aws_lambda_builders.exceptions import UnsupportedRuntimeError, UnsupportedArchitectureError


class FakePopen(object):
    def __init__(self, stdout=None, stderr=None, returncode=0):
        self._stdout = stdout
        self._stderr = stderr
        self._returncode = returncode

    def communicate(self):
        return self._stdout, self._stderr

    @property
    def returncode(self):
        return self._returncode


class TestGradleBinaryValidator(TestCase):
    @patch("aws_lambda_builders.workflows.java_gradle.utils.OSUtils")
    def setUp(self, MockOSUtils):
        self.mock_os_utils = MockOSUtils.return_value
        self.mock_log = Mock()
        self.runtime_path = "/path/to/gradle"
        self.runtime = "java8"
        self.architecture = "x86_64"

    @parameterized.expand(["1.7.0", "1.8.9", "11.0.0", "12 (Fluff)", "12"])
    def test_accepts_any_jvm_mv(self, version):
        version_string = ("JVM:          %s" % version).encode()
        self.mock_os_utils.popen.side_effect = [FakePopen(stdout=version_string)]
        validator = GradleValidator(runtime=self.runtime, architecture=self.architecture, os_utils=self.mock_os_utils)
        self.assertTrue(validator.validate(runtime_path=self.runtime_path))
        self.assertEqual(validator.validated_binary_path, self.runtime_path)

    def test_emits_warning_when_jvm_mv_greater_than_8(self):
        version_string = "JVM:          9.0.0".encode()
        self.mock_os_utils.popen.side_effect = [FakePopen(stdout=version_string)]
        validator = GradleValidator(
            runtime=self.runtime, architecture=self.architecture, os_utils=self.mock_os_utils, log=self.mock_log
        )
        self.assertTrue(validator.validate(runtime_path=self.runtime_path))
        self.assertEqual(validator.validated_binary_path, self.runtime_path)
        self.mock_log.warning.assert_called_with(
            GradleValidator.MAJOR_VERSION_WARNING, self.runtime_path, "9", "8", "8"
        )

    @parameterized.expand(["1.6.0", "1.7.0", "1.8.9"])
    def test_does_not_emit_warning_when_jvm_mv_8_or_less(self, version):
        version_string = ("JVM:          %s" % version).encode()
        self.mock_os_utils.popen.side_effect = [FakePopen(stdout=version_string)]
        validator = GradleValidator(
            runtime=self.runtime, architecture=self.architecture, os_utils=self.mock_os_utils, log=self.mock_log
        )
        self.assertTrue(validator.validate(runtime_path=self.runtime_path))
        self.assertEqual(validator.validated_binary_path, self.runtime_path)
        self.mock_log.warning.assert_not_called()

    def test_emits_warning_when_gradle_excutable_fails(self):
        version_string = "JVM:          9.0.0".encode()
        self.mock_os_utils.popen.side_effect = [FakePopen(stdout=version_string, returncode=1)]
        validator = GradleValidator(
            runtime=self.runtime, architecture=self.architecture, os_utils=self.mock_os_utils, log=self.mock_log
        )
        validator.validate(runtime_path=self.runtime_path)
        self.mock_log.warning.assert_called_with(GradleValidator.VERSION_STRING_WARNING, self.runtime_path)

    def test_emits_warning_when_version_string_not_found(self):
        version_string = "The Java Version:          9.0.0".encode()
        self.mock_os_utils.popen.side_effect = [FakePopen(stdout=version_string, returncode=0)]
        validator = GradleValidator(
            runtime=self.runtime, architecture=self.architecture, os_utils=self.mock_os_utils, log=self.mock_log
        )
        validator.validate(runtime_path=self.runtime_path)
        self.mock_log.warning.assert_called_with(GradleValidator.VERSION_STRING_WARNING, self.runtime_path)

    def test_no_warning_when_jvm_mv_11_and_java11_runtime(self):
        version_string = "JVM:          11.0.0".encode()
        self.mock_os_utils.popen.side_effect = [FakePopen(stdout=version_string)]
        validator = GradleValidator(
            runtime="java11", architecture=self.architecture, os_utils=self.mock_os_utils, log=self.mock_log
        )
        self.assertTrue(validator.validate(runtime_path=self.runtime_path))
        self.assertEqual(validator.validated_binary_path, self.runtime_path)

    def test_runtime_validate_unsupported_language_fail_open(self):
        validator = GradleValidator(runtime="java2.0", architecture="arm64")
        with self.assertRaises(UnsupportedRuntimeError):
            validator.validate(runtime_path="/usr/bin/java2.0")
