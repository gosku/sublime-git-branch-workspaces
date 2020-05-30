import os
import re
import subprocess
import time

import sublime
import sublime_plugin


class GitCommand(sublime_plugin.WindowCommand):
    def __init__(self, window):
        self.root_cache = {}
        self.git_path = self.get_git_exec_path()

        return super().__init__(window)

    def run_command(self, command):
        print("running def run_command(" + str(command) + "):")
        command = [arg for arg in re.split(r"\s+", command) if arg]
        if command[0] == "git":
            command[0] = self.git_path
        return subprocess.check_output(command).decode("ascii").strip()

    def getBranch(self):
        print("running def getBranch():")
        os.chdir(sublime.active_window().folders()[0])
        abbrev_ref = self.run_command("git rev-parse --abbrev-ref HEAD")

        # Avoid to return the command when we are checked out on a single commit and not a branch
        if abbrev_ref == "HEAD":
            return None
        return abbrev_ref

    def get_git_folder_path(self, directory):
        print("running def git_root(" + str(directory) + "):")
        retval = None
        leaf_dir = directory

        if leaf_dir in self.root_cache and self.root_cache[leaf_dir]["expires"] > time.time():
            return self.root_cache[leaf_dir]["retval"]

        while directory:
            if os.path.exists(os.path.join(directory, ".git")):
                retval = directory
                break
            parent = os.path.realpath(os.path.join(directory, os.path.pardir))
            if parent == directory:
                retval = None
                break
            directory = parent

        self.root_cache[leaf_dir] = {"retval": retval, "expires": time.time() + 5}

        return retval

    def get_git_exec_path(self):
        print("running def find_git():")
        path = os.environ.get("PATH", "").split(os.pathsep)
        if os.name == "nt":
            git_cmd = "git.exe"
        else:
            git_cmd = "git"

        git_path = self._test_paths_for_executable(path, git_cmd)

        if not git_path:
            # /usr/local/bin:/usr/local/git/bin
            if os.name == "nt":
                extra_paths = (
                    os.path.join(os.environ["ProgramFiles"], "Git", "bin"),
                    os.path.join(os.environ["ProgramFiles(x86)"], "Git", "bin"),
                )
            else:
                extra_paths = ("/usr/local/bin", "/usr/local/git/bin")
            git_path = self._test_paths_for_executable(extra_paths, git_cmd)
        return git_path

    def _test_paths_for_executable(self, paths, test_file):
        print("running def _test_paths_for_executable(paths, test_file):")
        for directory in paths:
            file_path = os.path.join(directory, test_file)
            if os.path.exists(file_path) and os.access(file_path, os.X_OK):
                return file_path
