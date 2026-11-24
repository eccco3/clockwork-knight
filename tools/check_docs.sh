#!/bin/sh
# Enforces the four documentation rules in DEV.md. Words are whitespace-separated tokens.
set -eu
cd "$(git rev-parse --show-toplevel)"

NOTES_LIMIT=600
SECTION_LIMIT=100
DIR_DOC_LIMIT=300
THIRD_PARTY=tools/downloads

words() { awk '{ n += NF } END { print n + 0 }' "$1"; }

docs() {
	git -c core.quotePath=false ls-files --cached --others --exclude-standard -- \
		':(icase)*.md' ':(icase)*.markdown' ':(icase)*.txt' ':(icase)*.rst' ':(icase)*.adoc' \
		":(exclude)$THIRD_PARTY" |
	while IFS= read -r f; do
		if [ -f "$f" ]; then echo "$f"; fi
	done
}

check_global() {
	for f in CLAUDE.md DEV.md BACKLOG.md; do
		[ -f "$f" ] || echo "$f: missing"
	done
	docs | while IFS= read -r f; do
		case "$f" in
			CLAUDE.md | DEV.md | BACKLOG.md | */*) ;;
			*) echo "$f: the only global documents are CLAUDE.md, DEV.md and BACKLOG.md" ;;
		esac
	done
}

# Claude's notes are all of CLAUDE.md after its first line, which points to DEV.md.
check_notes() {
	awk -v limit="$NOTES_LIMIT" '
		NR > 1 { n += NF }
		END { if (n > limit) printf "CLAUDE.md: Claude'"'"'s notes have %d words (limit %d)\n", n, limit }' CLAUDE.md
}

check_backlog() {
	awk -v limit="$SECTION_LIMIT" '
		function bad(msg) { printf "BACKLOG.md:%d: %s\n", NR, msg }
		function close_section() {
			if (section != "" && count > limit)
				printf "BACKLOG.md: \"%s / %s\" has %d words (limit %d)\n", item, section, count, limit
			section = ""; count = 0
		}
		function close_item() {
			close_section()
			if (item != "" && expect <= 3)
				printf "BACKLOG.md: \"%s\" is missing the section \"%s\"\n", item, want[expect]
		}
		BEGIN { want[1] = "task description"; want[2] = "open questions"; want[3] = "status" }
		{ sub(/\r$/, "") }
		/^```/ { fenced = !fenced }
		!fenced && /^# / {
			if ($0 != "# Backlog" || titled++) bad("only the title \"# Backlog\" may be a level-one heading")
			next
		}
		!fenced && /^## / { close_item(); item = substr($0, 4); expect = 1; next }
		!fenced && /^### / {
			close_section()
			section = tolower(substr($0, 5))
			if (item == "") bad("section outside a backlog item")
			else if (expect > 3 || section != want[expect])
				bad("sections must be exactly: Task description, Open questions, Status")
			else expect++
			next
		}
		!fenced && /^####/ { bad("headings below level three are not allowed"); next }
		NF == 0 { next }
		section == "" { bad("text outside a section"); next }
		{ count += NF }
		END { close_item() }' BACKLOG.md
}

check_directories() {
	docs | awk '
		index($0, "/") {
			dir = $0; sub(/\/[^\/]*$/, "", dir)
			if (first[dir] == "") first[dir] = $0
			else printf "%s: second document in a directory that already has %s\n", $0, first[dir]
		}'
	docs | while IFS= read -r f; do
		case "$f" in
			*/*)
				n=$(words "$f")
				[ "$n" -le "$DIR_DOC_LIMIT" ] || echo "$f: $n words (limit $DIR_DOC_LIMIT)"
				;;
		esac
	done
}

errors=$(check_global; check_notes; check_backlog; check_directories)
if [ -n "$errors" ]; then
	printf '%s\n' "$errors" >&2
	echo "Documentation rules broken; see CLAUDE.md." >&2
	exit 1
fi
