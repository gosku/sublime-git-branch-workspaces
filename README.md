# Sublime Git Branch Workspaces

### Features

* Track open files in sublime under each git branch for projects that match a git repository.
* The plugin stores the state for each branch, including open files, scroll of each file and window layout.
* Restore the window that sublime was showing the last time the git repository was in the current branch.

### Install

##### ST3 on Mac

In Terminal.app, run:

    cd ~/Library/Application\ Support/Sublime\ Text\ 3/Packages
    git clone https://github.com/gosku/sublime-git-branch-workspaces

Then restart ST3.

##### ST3 on Linux

Clone the project in your `Packages` directory:

    cd ~/.config/Sublime\ Text\ 3/Packages
    git clone https://github.com/gosku/sublime-git-branch-workspaces

Then restart ST3.

**Notes:**
* No configuration; works as-is. Behavior may not be perfect for everybody, but it has worked well enough for me.
* Switching branches **WILL** erase any unsaved modifications or new files in the buffer--without confirmation. Swapping workspace closes your previous branch's workspace then opens the newly checked-out branch's workspace.
* For the plugin swap workspaces, you must unfocus then refocus the cursor in the editor after checking out a different branch.
* This repo is a fork of https://github.com/Xaelias/ST_Plugins with some bug fixes and improvements.
