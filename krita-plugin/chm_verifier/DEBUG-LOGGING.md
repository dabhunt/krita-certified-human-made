# CHM Plugin Debug Logging

## Overview

The CHM plugin includes comprehensive debug logging to help diagnose issues, especially with session resumption across different platforms (Mac vs Windows).

## Where to Find Logs

Debug logs are written to:

**macOS/Linux:**
```
~/.local/share/chm/plugin_debug.log
```

**Windows:**
```
%USERPROFILE%\.local\share\chm\plugin_debug.log
```

Or on some Windows systems:
```
C:\Users\YourUsername\.local\share\chm\plugin_debug.log
```

## How to Enable Debug Logging

Debug logging is **enabled by default** in the current version. All operations are logged automatically.

## Binary Search Checkpoints

The plugin includes "BFROS" (Binary search like logging) checkpoints to diagnose session resumption issues. These checkpoints trace the entire flow of data:

### Session Save Flow (Checkpoints A-C)

**Checkpoint A** - Session data snapshot before persist
- Captures: session_id, event_count, drawing_time_secs, stroke_count
- Location: `_persist_session()` in `event_capture.py`
- **Purpose:** Verify session has correct data BEFORE saving

**Checkpoint B** - JSON serialization validation
- Compares: JSON event_count vs session.event_count
- **Purpose:** Detect if serialization loses data

**Checkpoint C** - File write verification
- Reads back saved file and verifies contents
- **Purpose:** Ensure data was actually written to disk correctly

### Session Resume Flow (Checkpoints D-E)

**Checkpoint D** - Parse JSON from disk
- Captures: session_id, event_count, events array length, drawing_time_secs
- **Purpose:** Verify saved data is intact on disk

**Checkpoint E** - Restoration verification
- Compares: Restored session vs saved JSON data
- **Purpose:** Detect if import_session() loses data

### Annotation System (Checkpoint F)

**Checkpoint F** - Document UUID annotation system
- Tests: setAnnotation() and annotation() calls
- **Purpose:** Verify annotations work (may fail on Windows)

### Import Process (Checkpoint G)

**Checkpoint G** - Session import details
- Logs: Each field being restored
- **Purpose:** Trace exactly what happens during import

## How to Report Bugs with Debug Logs

### Step 1: Reproduce the Issue

1. Enable debug logging (already on by default)
2. Create a new document in Krita
3. Draw at least 10 strokes
4. Save the document (`Ctrl+S` / `Cmd+S`)
5. Close the document
6. Reopen the document
7. Check session info (`CHM: View Current Session`)

### Step 2: Locate the Log File

Navigate to the log file location (see above for your OS).

### Step 3: Search for Checkpoints

Look for these patterns in the log:

```
[BFROS-CHECKPOINT-A] ✓ SNAPSHOT BEFORE PERSIST:
[BFROS-CHECKPOINT-B] ✓ JSON DATA VALIDATION:
[BFROS-CHECKPOINT-C] ✓ READ-BACK VERIFICATION:
[BFROS-CHECKPOINT-D] ✓ PARSED FROM DISK:
[BFROS-CHECKPOINT-E] ✓ RESTORATION VERIFICATION:
[BFROS-CHECKPOINT-F] Testing document annotation system:
[BFROS-CHECKPOINT-G] IMPORTING SESSION DATA:
```

### Step 4: Identify Where Data Was Lost

Look for mismatches:

- ❌ `DATA MISMATCH!` - Serialization lost data
- ❌ `EVENT COUNT MISMATCH!` - Import failed
- ❌ `ANNOTATION NOT PERSISTED` - UUID system broken
- ❌ `FILE NOT FOUND` - Disk write failed

### Step 5: Share the Log

When reporting bugs:

1. **Extract relevant section:** Copy from `========== PERSIST SESSION` through `========== RESUME/CREATE SESSION`
2. **Include checkpoint results:** Make sure all checkpoints (A-G) are included
3. **Attach to bug report:** Create a GitHub issue with the log excerpt

## Understanding the Checkpoints

### Expected Flow (Success)

```
[PERSIST-1] ========== PERSIST SESSION (on_save) ==========
[BFROS-CHECKPOINT-A] ✓ SNAPSHOT: event_count=10, drawing_time=45
[BFROS-CHECKPOINT-B] ✓ JSON DATA VALIDATION: event_count=10 (match: True)
[BFROS-CHECKPOINT-C] ✓ FILE EXISTS: 12345 bytes on disk
[BFROS-CHECKPOINT-C] ✓ READ-BACK: event_count=10 (match: True)
[BFROS-CHECKPOINT-C] ✅ VERIFICATION PASSED!

[RESUME-1] ========== RESUME/CREATE SESSION (imageCreated) ==========
[BFROS-CHECKPOINT-D] ✓ PARSED FROM DISK: event_count=10, events array=10
[BFROS-CHECKPOINT-E] ✓ RESTORATION: disk=10, restored=10, match=True
[BFROS-CHECKPOINT-E] ✅ ALL DATA RESTORED CORRECTLY!
```

### Common Failures

#### Failure 1: Annotation System (Windows)

```
[BFROS-CHECKPOINT-F] ❌ ANNOTATION NOT PERSISTED (read back None/empty)
[BFROS-CHECKPOINT-F] → This could be the Windows bug!
```

**What this means:** Document annotations (UUID system) don't persist on Windows.  
**Impact:** Session keys change, can't find saved session on reopen.  
**Fix:** Need to use filepath-based keys on Windows instead of UUID.

#### Failure 2: JSON Serialization

```
[BFROS-CHECKPOINT-B] ❌ DATA MISMATCH! JSON has 0, session has 10
```

**What this means:** to_dict() or JSON.dumps() is losing data.  
**Impact:** Session is saved with empty/incorrect data.  
**Fix:** Bug in session_to_json() method.

#### Failure 3: File System

```
[BFROS-CHECKPOINT-C] ❌ FILE NOT FOUND after save!
```

**What this means:** File write failed or wrong path.  
**Impact:** No session saved to disk at all.  
**Fix:** Check file permissions, disk space.

#### Failure 4: Import Process

```
[BFROS-CHECKPOINT-E] ❌ EVENT COUNT MISMATCH!
```

**What this means:** import_session() didn't restore all fields.  
**Impact:** Session partially restored, missing events/time.  
**Fix:** Bug in import_session() implementation.

## Disabling Debug Logging (Future)

Currently, debug logging is always enabled. To disable in the future, you can set:

```python
DEBUG_LOG = False
```

At the top of:
- `chm_extension.py`
- `event_capture.py`
- `chm_session_manager.py`
- `session_storage.py`

## Log File Management

### Viewing Logs in Real-Time

**macOS/Linux:**
```bash
tail -f ~/.local/share/chm/plugin_debug.log
```

**Windows (PowerShell):**
```powershell
Get-Content "$env:USERPROFILE\.local\share\chm\plugin_debug.log" -Wait
```

### Clearing Old Logs

The log file grows over time. To clear it:

**macOS/Linux:**
```bash
rm ~/.local/share/chm/plugin_debug.log
```

**Windows:**
```powershell
del "$env:USERPROFILE\.local\share\chm\plugin_debug.log"
```

Or simply delete the file through your file explorer.

### Log Rotation

The plugin does NOT automatically rotate logs. For production use, consider:

1. Manually clearing logs periodically
2. Using external log rotation tools
3. Future enhancement: Implement max log size (e.g., 10MB limit)

## Technical Details

### Log Format

```
[YYYY-MM-DD HH:MM:SS] CHM: [MODULE] Message
```

Example:
```
[2026-01-09 14:23:45] CHM: [BFROS-CHECKPOINT-A] ✓ SNAPSHOT BEFORE PERSIST: {...}
```

### Modules

- `[PERSIST-*]` - Session persistence (save to disk)
- `[RESUME-*]` - Session resumption (load from disk)
- `[UUID-*]` - Document annotation system
- `[IMPORT-*]` - Session import process
- `[BFROS-CHECKPOINT-*]` - Binary search diagnostic checkpoints

### Performance Impact

Debug logging has minimal performance impact:
- File I/O is buffered and flushed immediately
- Logging only happens during key events (save, load, draw)
- Typical overhead: <1ms per logged event

For production, consider disabling to reduce log file size.

