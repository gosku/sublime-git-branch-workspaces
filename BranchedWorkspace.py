import os
import pickle
from collections import defaultdict
from pprint import pprint

import git_command
import sublime
import sublime_plugin


class BranchedWorkspace(sublime_plugin.EventListener):
    def __init__(self):
        self.git = git_command.GitCommand(sublime.active_window())
        self.previous_branch = defaultdict(lambda: None)
        return super().__init__()

    def on_activated_async(self, view):
        print("running def on_activated(self, view):")
        window = sublime.active_window()
        folders = window.folders()
        print("folders " + str(folders))
        working_dir = None if not folders else folders[0]
        git_root = self.git.get_git_root(working_dir)

        if not git_root:
            return

        # the plugin only activates when the root folder is the git folder
        if working_dir != git_root:
            return

        current_branch = self.git.getBranch()
        if not current_branch:
            return

        print("branch is " + str(current_branch))

        if not self.previous_branch[working_dir]:
            # # we try to load a saved config
            # self.close_all_views(git_root)
            # self.load_branch(window, current_branch, git_root)
            print("no previous branch")
            self.previous_branch[git_root] = current_branch
            return
        elif self.previous_branch[working_dir] != current_branch:

            self.save_previous_branch(self.previous_branch[working_dir], git_root)
            self.previous_branch[git_root] = current_branch
            self.close_all_views(git_root)
            self.load_branch(window, current_branch, git_root)

    def close_all_views(self, root):
        print("running def close_all_views(self, " + str(root) + "):")
        for win in sublime.windows():
            if win.folders() != [] and win.folders()[0] == root:
                for view in win.views():
                    view.set_scratch(True)
                win.run_command("close_all")

    def save_previous_branch(self, branch, git_root):
        print("running def save_previous_branch")

        # we need to save the current state
        # and load the saved state (if any) for the new branch
        windows_to_save = defaultdict(list)
        for win in sublime.windows():
            # we only care about the same git repository
            if win.folders() == [] or win.folders()[0] != git_root:
                continue

            window = {}
            window["layout"] = win.get_layout()
            window["active_views"] = []
            for group in range(0, win.num_groups()):
                window["active_views"].append(win.active_view_in_group(group).file_name())
            window["views"] = []
            for _view in win.views():
                view = {}
                name = _view.file_name()
                if name is None:
                    continue
                print("adding file " + name)
                view["filename"] = name
                view["view_index"] = win.get_view_index(_view)
                view["scroll"] = _view.viewport_position()
                window["views"].append(view)
            windows_to_save[win.id()] = window

        print("saving branch: " + branch)
        print("content:")
        pprint(windows_to_save)
        path = git_root + "/.git/BranchedProjects.sublime"
        obj = {}
        if os.path.isfile(path):
            with open(path, "rb") as f:
                obj = pickle.load(f)
                f.close()
        obj[branch] = windows_to_save
        with open(path, "w+b") as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
            f.close()

    def get_working_dir(self, view):
        print("running def get_working_dir(view):")
        win = view.window()
        folders = [] if win is None else win.folders()
        return folders[0] if folders != [] else None

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
        for win in obj[branch].values():
            # Restore project settings in new window
            project_data = prev_window.project_data()
            new_win = sublime.active_window()
            new_win.set_project_data(project_data)
            pprint(win)
            new_win.set_layout(win["layout"])
            focused_views = []
            for view in win["views"]:
                if os.path.isfile(view["filename"]):
                    print("loading file " + view["filename"])
                    _view = new_win.open_file(view["filename"])
                    new_win.set_view_index(_view, view["view_index"][0], view["view_index"][1])
                    self.set_file_scroll(_view, view["scroll"])
                    if win.get("active_views") and view["filename"] in win["active_views"]:
                        focused_views.append(_view)
            for focused_view in focused_views:
                new_win.focus_view(focused_view)

        no_win = True
        for win in sublime.windows():
            win_root = win.folders()
            win_root = win_root[0] if win_root != [] else None
            if win_root == root:
                no_win = False
                break

        if no_win:
            sublime.run_command("new_window")
            new_win = sublime.active_window()
            new_win.set_project_data(project_data)

    def set_file_scroll(self, view, scroll):
        print("running def set_file_scroll(self, %s, %s):" % (view, scroll))
        if view.is_loading():
            sublime.set_timeout(lambda: self.set_file_scroll(view, scroll), 0)
        else:
            view.set_viewport_position(scroll, False)
