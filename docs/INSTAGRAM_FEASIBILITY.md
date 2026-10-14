# Instagram saved-content feasibility gate

**Status:** not started — no synchronization code is present.

Before any implementation, evaluate an opt-in method against these gates:

1. It does not extract passwords, cookies, or private API calls.
2. It has a documented permission and export story.
3. It can fail without losing existing source records.
4. It supports deleting imported content locally.
5. It remains maintainable if Instagram changes its web interface.

If any gate fails, keep the supported alternatives: paste individual public links or import a user-created CSV of links.
