from unittest import TestCase
from mock import patch, call, Mock
from parameterized import parameterized, param

from aws_lambda_builders.builder import LambdaBuilder
from aws_lambda_builders.workflow import Capability, BaseWorkflow
from aws_lambda_builders.registry import DEFAULT_REGISTRY


class TesetLambdaBuilder_init(TestCase):

    DEFAULT_WORKFLOW_MODULE = "aws_lambda_builders.workflows"

    def setUp(self):
        self.lang = "python"
        self.lang_framework = "pip"
        self.app_framework = "chalice"

    @patch("aws_lambda_builders.builder.importlib")
    @patch("aws_lambda_builders.builder.get_workflow")
    def test_must_load_all_default_workflows(self, get_workflow_mock, importlib_mock):

        # instantiate
        builder = LambdaBuilder(self.lang, self.lang_framework, self.app_framework)

        self.assertEqual(builder.supported_workflows, [self.DEFAULT_WORKFLOW_MODULE])

        # First check if the module was loaded
        importlib_mock.import_module.assert_called_once_with(self.DEFAULT_WORKFLOW_MODULE)

        # then check if we tried to get a workflow for given capability
        get_workflow_mock.assert_called_with(
            Capability(
                language=self.lang, dependency_manager=self.lang_framework, application_framework=self.app_framework
            )
        )

    @patch("aws_lambda_builders.builder.importlib")
    @patch("aws_lambda_builders.builder.get_workflow")
    def test_must_support_loading_custom_workflows(self, get_workflow_mock, importlib_mock):

        modules = ["a.b.c", "c.d", "e.f", "z.k"]

        # instantiate
        builder = LambdaBuilder(self.lang, self.lang_framework, self.app_framework, supported_workflows=modules)

        self.assertEqual(builder.supported_workflows, modules)

        # Make sure the modules are loaded in same order as passed
        importlib_mock.import_module.assert_has_calls([call(m) for m in modules], any_order=False)

    @patch("aws_lambda_builders.builder.importlib")
    @patch("aws_lambda_builders.builder.get_workflow")
    def test_must_not_load_any_workflows(self, get_workflow_mock, importlib_mock):

        modules = []  # Load no modules
        builder = LambdaBuilder(self.lang, self.lang_framework, self.app_framework, supported_workflows=modules)

        self.assertEqual(builder.supported_workflows, [])

        # Make sure the modules are loaded in same order as passed
        importlib_mock.import_module.assert_not_called()

    def test_with_real_workflow_class(self):
        """Define a real workflow class and try to fetch it. This ensures the workflow registration actually works."""

        # Declare my test workflow.
        class MyWorkflow(BaseWorkflow):
            NAME = "MyWorkflow"
            CAPABILITY = Capability(
                language=self.lang, dependency_manager=self.lang_framework, application_framework=self.app_framework
            )

            def __init__(
                self,
                source_dir,
                artifacts_dir,
                scratch_dir,
                manifest_path,
                runtime=None,
                optimizations=None,
                options=None,
                executable_search_paths=None,
                mode=None,
            ):
                super(MyWorkflow, self).__init__(
                    source_dir,
                    artifacts_dir,
                    scratch_dir,
                    manifest_path,
                    runtime=runtime,
                    optimizations=optimizations,
                    options=options,
                    executable_search_paths=executable_search_paths,
                    mode=mode,
                )

        # Don't load any other workflows. The above class declaration will automatically load the workflow into registry
        builder = LambdaBuilder(self.lang, self.lang_framework, self.app_framework, supported_workflows=[])

        # Make sure this workflow is selected
        self.assertEqual(builder.selected_workflow_cls, MyWorkflow)


class TesetLambdaBuilder_build(TestCase):
    def tearDown(self):
        # we don't want test classes lurking around and interfere with other tests
        DEFAULT_REGISTRY.clear()

    def setUp(self):
        self.lang = "python"
        self.lang_framework = "pip"
        self.app_framework = "chalice"

    @parameterized.expand([param(True), param(False)])
    @patch("aws_lambda_builders.builder.os")
    @patch("aws_lambda_builders.builder.importlib")
    @patch("aws_lambda_builders.builder.get_workflow")
    def test_with_mocks(self, scratch_dir_exists, get_workflow_mock, importlib_mock, os_mock):
        workflow_cls = Mock()
        workflow_instance = workflow_cls.return_value = Mock()

        os_mock.path.exists.return_value = scratch_dir_exists

        get_workflow_mock.return_value = workflow_cls

        builder = LambdaBuilder(self.lang, self.lang_framework, self.app_framework, supported_workflows=[])

        builder.build(
            "source_dir",
            "artifacts_dir",
            "scratch_dir",
            "manifest_path",
            architecture="arm64",
            runtime="runtime",
            optimizations="optimizations",
            options="options",
            executable_search_paths="executable_search_paths",
            mode=None,
        )

        workflow_cls.assert_called_with(
            "source_dir",
            "artifacts_dir",
            "scratch_dir",
            "manifest_path",
            architecture="arm64",
            runtime="runtime",
            optimizations="optimizations",
            options="options",
            executable_search_paths="executable_search_paths",
            mode=None,
        )
        workflow_instance.run.assert_called_once()
        os_mock.path.exists.assert_called_once_with("scratch_dir")
        if scratch_dir_exists:
            os_mock.makedirs.not_called()
        else:
            os_mock.makedirs.assert_called_once_with("scratch_dir")
