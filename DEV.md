Immutable without dev's permission. If you notice a change, no need to notify the dev — assume they authored it.
In this project you develop a game. The graphics and animation are extremely high quality and extremely detailed. Generic surface scans, environment lighting, anatomy references, motion capture, or base meshes as a starting point for body topology and rigging may be downloaded; all designs and most meshes are original. The animations are extremely fluid and realistic and the meshes have excellent topology and rigging. Animations can also be hand-keyed — be ambitious. The primary tools are Godot and Blender, but you can download anything that is free. The following rules must be enforced deterministically:

1. The only global documentation is the CLAUDE.md, the DEV.md, the DESIGN.md and the BACKLOG.md.
2. Claude's notes in the CLAUDE.md do not exceed 600 words.
3. The backlog only contains a queue of top-level backlog items with the following sections, none of which may exceed a hundred words: task description, open questions, status.
4. There is only one directory-scoped document per first-party directory, and it does not exceed 300 words.

The following is not enforced deterministically, but scripts and application files prefer code over comments.

All tasks that would take more than a minute are processed into backlog items, each sized for one session. After completing a backlog item:

1. Clear the backlog item.
2. Commit and push to the remote without asking.
3. If appropriate, recommend the dev to execute /clear or /compact before the next task.

Never ask the dev whether to commit, merge or push: commit, merge and push whenever work is done. Only regressions are not merged.

The standard workflow runs backlog items as background subagents, each in its own worktree: up to three at once, more when they barely load the GPU. Pick items needing neither each other's results nor the same files or modules. Skip planning items and items with open questions for the dev; ones needing investigation go to the agent.

The hardest work (sculpting, rigging, animation, shaders, lighting, cross-cutting judgement) gets Fable, high, or Opus, max, once Fable's usage runs out; moderate work Opus, high; mechanical work Sonnet, medium.

Don't micromanage: give the agent the dev's verbatim description and the relevant facts, and let it choose its own approach. Tell it to:

- merge `origin/main`, then read CLAUDE.md, DEV.md and its item;
- copy needed gitignored files from the main checkout, writing only inside its worktree;
- leave the code in the shape it should have, reporting collisions with parallel work as follow-ups;
- leave BACKLOG.md alone; commit and push its branch without merging;
- report its branch, commit, results, screenshots and anything unverified.

When one finishes, review its diff and images, squash-merge it onto main, clear its item, add follow-ups, run `tools/check_docs.sh`, push, rebuild or import what it changed, and relay new rules to agents still running.

Claude can use CLAUDE.md as memory.

Tools meant for the dev to use directly are added to the playtest launcher.

You can proactively solve tech debt yourself. If a big refactor is needed, you can add it to the backlog.