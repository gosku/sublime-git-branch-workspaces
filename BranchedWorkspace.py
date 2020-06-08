import copy
import os
import pickle
from collections import defaultdict
from pprint import pprint

import sublime
import sublime_plugin

from . import git_command


class BranchedWorkspace(sublime_plugin.EventListener):
    def __init__(self):
        print("Loading BranchedWorkspace plugin:")
        self.git = git_command.GitCommand(sublime.active_window())
        self.window = sublime.active_window()
        self.folders = self.window.folders()
        self.working_dir = None if not self.folders else self.folders[0]
        self.git_folder_path = None
        self.previous_branch = defaultdict(lambda: None)
        self.current_branch = None
        self.stored_branch_sessions = {}
        return super().__init__()

    def on_activated_async(self, view):
        self.refresh_attributes()

        if not self.should_activate():
            return

        print("Current branch is " + self.current_branch)

        # First time running this method since sublime was opened
        if not self.previous_branch[self.working_dir]:
            print("no previous branch")
            self.previous_branch[self.git_folder_path] = self.current_branch
            if self.should_load_branch():
                self.close_all_views(self.git_folder_path)
                self.load_branch(self.window, self.current_branch, self.git_folder_path)
        elif self.previous_branch[self.working_dir] != self.current_branch:
            print("previous_branch: " + self.previous_branch[self.working_dir])
            if self.should_load_branch():
                print(
                    "changing from "
                    + self.previous_branch[self.working_dir]
                    + " to "
                    + self.current_branch
                )
                self.save_previous_branch()
                self.close_all_views(self.git_folder_path)
                self.previous_branch[self.working_dir] = self.current_branch
                self.load_branch(self.window, self.current_branch, self.git_folder_path)

    def refresh_attributes(self):
        self.window = sublime.active_window()
        self.folders = self.window.folders()
        self.working_dir = None if not self.folders else self.folders[0]
        self.git_folder_path = self.git.get_git_folder_path(self.working_dir)
        self.current_branch = self.git.get_branch()
        self.stored_branch_sessions = self.get_all_stored_branch_sessions()

    def should_activate(self):
        if not self.working_dir:
            return False

        if not self.git_folder_path:
            return False

        if self.working_dir != self.git_folder_path:
            return False

        if not self.current_branch:
            return False

        if self.current_branch == self.previous_branch[self.working_dir]:
            print("Branch is " + self.current_branch + ". Branch did not change.")
            return False

        if len(sublime.windows()) > 1:
            return False

        print("should activate")
        return True

    def should_load_branch(self):
        # At the moment, we only load a stored branch when there is one window open,
        # since figuring out the behavior of this plugin would be much harder when several
        # windows are open in a sublime text session.
        if len(sublime.windows()) > 1:
            print("more than one window")
            return False

        # Return False if the stored session for the current branch would be contained in the
        # current set of open files.
        # This check is useful for when we invoke sublime from command line with hot exit enabled
        # and sublime loads the previous open project + the new file passed as an argument
        if self.stored_branch_session_is_subset_of_current_session():
            print("stored branch session is subset of current session")
            return False

        return True

    def stored_branch_session_is_subset_of_current_session(self):
        stored_branch_sessions = self.get_all_stored_branch_sessions()
        if not stored_branch_sessions.get(self.current_branch, None):
            return False
        else:
            stored_session = stored_branch_sessions[self.current_branch]
            current_session = self.serialize_current_session()
            if self.stored_session_is_subset_of_current_session(stored_session, current_session):
                return True
        return False

    def get_all_stored_branch_sessions(self):
        if self.stored_branch_sessions:
            return self.stored_branch_sessions
        else:
            return self.update_stored_branch_sessions()

    def update_stored_branch_sessions(self, branch_sessions_for_storing={}):
        if branch_sessions_for_storing:
            branch_sessions_dict = branch_sessions_for_storing
        else:
            branch_sessions_dict = defaultdict(lambda: defaultdict(list))
            if not self.git_folder_path:
                return {}
            path = self.git_folder_path + "/.git/BranchedProjects.sublime"
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    tmp = pickle.load(f)
                    for o in tmp:
                        branch_sessions_dict[o] = tmp[o]
                    f.close()
        self.stored_branch_sessions = branch_sessions_for_storing
        return self.stored_branch_sessions

    def serialize_current_session(self):
        # Return the current sublime session into a dict that represents the window state:
        # - Layout
        # - Open files and its position in their group and their scrolls
        # - Focused views for each group
        sublime_window = sublime.active_window()
        serialized_window = {}

        # we only care about the same git repository
        if sublime_window.folders() == [] or sublime_window.folders()[0] != self.git_folder_path:
            return serialized_window

        serialized_window["layout"] = sublime_window.get_layout()
        serialized_window["active_views"] = []
        for group in range(0, sublime_window.num_groups()):
            serialized_window["active_views"].append(
                sublime_window.active_view_in_group(group).file_name()
            )
        serialized_window["views"] = []
        for _view in sublime_window.views():
            view = {}
            name = _view.file_name()
            if name is None:
                continue
            view["filename"] = name
            view["view_index"] = sublime_window.get_view_index(_view)
            view["scroll"] = _view.viewport_position()
            serialized_window["views"].append(view)

        return serialized_window

    def stored_session_is_subset_of_current_session(self, stored_session, current_session):
        """
        Return wether the filenames stored for a stored branch session are a subset of the current
        set of open files
        """
        stored_session_views = stored_session["views"]
        current_session_filenames = [v["filename"] for v in current_session["views"]]

        for view in stored_session_views:
            if not view["filename"] in current_session_filenames:
                return False

        return True

    def close_all_views(self, root):
        print("running def close_all_views(self, " + str(root) + "):")
        for win in sublime.windows():
            if win.folders() != [] and win.folders()[0] == root:
                for view in win.views():
                    view.set_scratch(True)
                win.run_command("close_all")

    def save_previous_branch(self):
        print("Running def save_previous_branch")

        print("Saving branch (" + self.previous_branch[self.git_folder_path] + ")")
        serialized_session = self.serialize_current_session()
        # print("Content:")
        # pprint(serialized_session)

        path = self.git_folder_path + "/.git/BranchedProjects.sublime"
        obj = {}
        if os.path.isfile(path):
            with open(path, "rb") as f:
                obj = pickle.load(f)
                f.close()
        obj[self.previous_branch[self.git_folder_path]] = serialized_session
        with open(path, "w+b") as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
            f.close()

        self.update_stored_branch_sessions(branch_sessions_for_storing=obj)

    def load_branch(self, prev_window, branch, root):
        print("running def load_branch(self, " + str(branch) + ", " + str(root) + "):")
        if not root:
            print("load: off of git")
            return

        print("load branch: " + branch)
        path = root + "/.git/BranchedProjects.sublime"
        obj = defaultdict(lambda: defaultdict(list))
        if os.path.isfile(path):
            with open(path, "rb") as f:
                tmp = pickle.load(f)
                for o in tmp:
                    obj[o] = tmp[o]
                f.close()
        stored_serialized_session = obj[branch]
        project_data = prev_window.project_data()
        new_win = sublime.active_window()
        new_win.set_project_data(project_data)
        # print("Stored serialized session for branch (" + branch + ")")
        # pprint(stored_serialized_session)
        new_win.set_layout(stored_serialized_session["layout"])
        focused_views = []
        for serialized_view in stored_serialized_session["views"]:
            if os.path.isfile(serialized_view["filename"]):
                print("loading file " + serialized_view["filename"])
                view = new_win.open_file(serialized_view["filename"])
                sublime.set_timeout_async(
                    lambda view=view, serialized_view=copy.deepcopy(serialized_view):
                        self.load_view(view, new_win, serialized_view, stored_serialized_session),
                    5
                )

            if (
                stored_serialized_session.get("active_views")
                and serialized_view["filename"] in stored_serialized_session["active_views"]
            ):
                focused_views.append(view)

        sublime.set_timeout_async(lambda: self.restore_focus(new_win, focused_views), 50)

    def load_view(self, view, window, serialized_view, stored_serialized_session):
        # print("Running def load_view(): for filename %s" % serialized_view["filename"])
        if view.is_loading():
            sublime.set_timeout_async(
                lambda: self.load_view(view, window, serialized_view, stored_serialized_session),
                5
            )
        else:
            window.set_view_index(view, serialized_view["view_index"][0], serialized_view["view_index"][1])

            print("Set scroll to (%s, %s)" % serialized_view["scroll"])
            sublime.set_timeout(lambda: view.set_viewport_position(serialized_view["scroll"], False), 50)

            print("Loaded view: " + view.file_name())

    def restore_focus(self, window, focused_views):
        if any(v.is_loading() for v in window.views()):
            sublime.set_timeout_async(lambda: self.restore_focus(window, focused_views), 10)
        else:
            for focused_view in focused_views:
                window.focus_view(focused_view)
