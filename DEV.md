<immutable without the dev's blessing>
In this project you develop a game. The graphics and animation are extremely high quality and extremely detailed. Generic surface scans, environment lighting, anatomy references, motion capture, or base meshes as a starting point for body topology and rigging may be downloaded; all designs and most meshes are original. The animations are extremely fluid and realistic and the meshes have excellent topology and rigging. Animations can also be hand-keyed — be ambitious. The primary tools are Godot and Blender, but you can download anything that is free. The following rules must be enforced deterministically:

1. The only global documentation is the CLAUDE.md, the DEV.md and the BACKLOG.md.
2. Claude's notes in the CLAUDE.md do not exceed 600 words.
3. The backlog only contains a queue of top-level backlog items with the following sections, none of which may exceed a hundred words: task description, open questions, status.
4. There is only one directory-scoped document per first-party directory, and it does not exceed 300 words.

The following is not enforced deterministically, but scripts and application files prefer code over comments.

All tasks that would take more than a minute are processed into backlog items, each sized for one session. After completing a backlog item:

1. Clear the backlog item.
2. Commit and push to the remote without asking.
3. If appropriate, recommend the dev to execute /clear or /compact before the next task.

Never ask the dev whether to commit, merge or push: commit, merge and push whenever work is done. Only regressions are not merged.

Claude Code's auto-memory is not used: what Claude needs to remember goes into Claude's notes in the CLAUDE.md.

You can proactively solve tech debt yourself. If a big refactor is needed, you can add it to the backlog.
</immutable without the dev's blessing>
