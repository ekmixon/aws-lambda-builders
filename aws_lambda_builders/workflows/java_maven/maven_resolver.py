"""
Maven executable resolution
"""

from .utils import OSUtils


class MavenResolver(object):
    def __init__(self, executable_search_paths=None, os_utils=None):
        self.binary = "mvn"
        self.executables = [self.binary]
        self.executable_search_paths = executable_search_paths
        self.os_utils = os_utils or OSUtils()

    @property
    def exec_paths(self):
        if paths := self.os_utils.which(
            "mvn", executable_search_paths=self.executable_search_paths
        ):
            return paths
        else:
            raise ValueError("No Maven executable found!")
