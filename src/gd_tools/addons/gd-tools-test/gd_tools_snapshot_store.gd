class_name GdToolsSnapshotStore
extends RefCounted

## File-system storage for snapshot assertions.
##
## Snapshots live under ``<base_dir>/<suite>/<test>/<name>.snap`` in a
## human-readable, versioned format with LF line endings so files are stable
## across platforms and reviewable in diffs. Read results are dictionaries
## that either succeed (``ok: true`` plus ``value`` and ``path``) or fail
## closed (``ok: false`` plus ``error`` of ``not_found``/``malformed``/``io``
## and a diagnostic ``message``).

const SNAPSHOT_FORMAT_VERSION := 1

const _MARKER_FORMAT := "# gd-tools snapshot v%d"


## Resolve the absolute snapshot file path for one assertion.
static func snapshot_path(
	base_dir: String, suite_name: String, test_name: String, snapshot_name: String
) -> String:
	return (
		base_dir
		.path_join(suite_name)
		.path_join(test_name)
		.path_join(snapshot_name + ".snap")
	)


## Write one snapshot file, creating intermediate directories as needed.
static func write(
	base_dir: String,
	suite_name: String,
	test_name: String,
	snapshot_name: String,
	value_text: String,
) -> Dictionary:
	var path := snapshot_path(base_dir, suite_name, test_name, snapshot_name)
	var mkdir_error := DirAccess.make_dir_recursive_absolute(
		base_dir.path_join(suite_name).path_join(test_name)
	)
	if mkdir_error != OK:
		return _io_error(path, "cannot create directory %s (error %d)" % [base_dir, mkdir_error])
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return _io_error(path, "cannot write %s (error %d)" % [path, FileAccess.get_open_error()])
	var header := "%s\n# suite: %s\n# test: %s\n# name: %s\n" % [
		_MARKER_FORMAT % SNAPSHOT_FORMAT_VERSION,
		suite_name,
		test_name,
		snapshot_name,
	]
	file.store_string(header + value_text + "\n")
	file.close()
	return {"ok": true, "path": path}


## Read one snapshot file, parsing and validating its versioned header.
static func read(
	base_dir: String, suite_name: String, test_name: String, snapshot_name: String
) -> Dictionary:
	var path := snapshot_path(base_dir, suite_name, test_name, snapshot_name)
	if not FileAccess.file_exists(path):
		return {
			"ok": false,
			"error": "not_found",
			"message": "Snapshot does not exist yet: %s" % path,
			"path": path,
		}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return _io_error(path, "cannot read %s (error %d)" % [path, FileAccess.get_open_error()])
	var content := file.get_as_text()
	file.close()
	return _parse(path, content, suite_name, test_name, snapshot_name)


static func _parse(
	path: String, content: String, suite_name: String, test_name: String, snapshot_name: String
) -> Dictionary:
	var lines := content.split("\n")
	var expected_marker := _MARKER_FORMAT % SNAPSHOT_FORMAT_VERSION
	if lines.is_empty() or lines[0] != expected_marker:
		var got := lines[0] if not lines.is_empty() else ""
		return _malformed(
			path,
			"expected first line %s, got %s" % [expected_marker, got],
		)
	var fields := {}
	var body_start := lines.size()
	for index in range(1, lines.size()):
		var line := lines[index]
		if not line.begins_with("# "):
			body_start = index
			break
		var separator := line.find(": ")
		if separator == -1:
			return _malformed(path, "malformed header line \"%s\"" % line)
		fields[line.substr(2, separator - 2)] = line.substr(separator + 2)
	for key in ["suite", "test", "name"]:
		if not fields.has(key):
			return _malformed(path, "missing header field \"%s\"" % key)
	if fields["suite"] != suite_name or fields["test"] != test_name or fields["name"] != snapshot_name:
		return _malformed(
			path,
			"header identifies %s/%s/%s but was read as %s/%s/%s"
			% [
				suite_name,
				test_name,
				snapshot_name,
				fields["suite"],
				fields["test"],
				fields["name"],
			],
		)
	var body := "\n".join(PackedStringArray(lines.slice(body_start)))
	if body.ends_with("\n"):
		body = body.substr(0, body.length() - 1)
	return {"ok": true, "value": body, "path": path}


static func _io_error(path: String, message: String) -> Dictionary:
	return {"ok": false, "error": "io", "message": message, "path": path}


static func _malformed(path: String, message: String) -> Dictionary:
	return {
		"ok": false,
		"error": "malformed",
		"message": "Malformed snapshot %s: %s" % [path, message],
		"path": path,
	}
