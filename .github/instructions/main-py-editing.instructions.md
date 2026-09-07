---
name: main-py-editing
description: 'Editing source_code/main.py (entry point). Use when: modifying the main application window, adding event handlers, importing new controllers/services, changing UI layout orchestration.'
applyTo: 'source_code/main.py'
---

# Editing Main Application Entry Point

## File Role

`source_code/main.py` is the application entry point and central orchestrator:
- Instantiates all controllers, services, and UI components
- Manages main window lifecycle and event dispatch
- Holds compatibility mappings in `KaraokeApp` class
- Handles page navigation and task completion callbacks

**Coupling level: HIGH** — Changes here often ripple to controllers, services, and UI modules.

---

## Before Editing

1. **Check dependencies**: Read [`documentation/FILE_DEPENDENCIES.md`](../../documentation/FILE_DEPENDENCIES.md) section 4 (UI Refactoring)
   - New UI component? Must add to `setup_ui()` and import
   - New service? Must instantiate and store as instance variable
   - New controller? Must instantiate and wire event handlers

2. **Understand current structure**:
   - `__init__` → Initializes window, state, services, controllers, UI
   - `setup_ui()` → Assembles all UI pages and components
   - Page constants: `PAGE_MEDIA_LOADER = 0`, `PAGE_PLAYBACK = 1`, etc.
   - Event handlers named `handle_*` and connected via `.connect()`

---

## Common Editing Patterns

### Adding a New Service

**Do this:**
1. Import service at top: `from services.new_service import NewService`
2. Instantiate in `__init__`: `self.new_service = NewService()`
3. Pass to controllers/UI that need it: `self.controller = Controller(self.new_service)`
4. Update `build_system/KaraokeStudioPro.spec` hiddenimports: `'source_code.services.new_service'`
5. Update all 5 docs (see FILE_DEPENDENCIES.md)

**Example:**
```python
from services.new_service import NewService  # Import at top

class KaraokeApp(QMainWindow):
    def __init__(self):
        # ... existing setup ...
        self.new_service = NewService()  # Add here
        self.playback_controller = PlaybackController(
            self.player_service, self.new_service  # Pass to controller
        )
```

### Adding a New UI Page

**Do this:**
1. Create file in `source_code/ui/new_page.py`
2. Import in main.py: `from ui.new_page import NewPage`
3. Add page constant: `PAGE_NEW = 5`  (next available index)
4. Instantiate in `setup_ui()`: `self.new_page = NewPage()`
5. Add to `self.pages` list: `self.pages = [self.media_loader_page, ..., self.new_page]`
6. Add navigation handler if needed
7. Update `build_system/KaraokeStudioPro.spec` hiddenimports: `'source_code.ui.new_page'`
8. Update all 5 docs with new page index

**Critical:** Keep page indices in sync across main.py and FILE_DEPENDENCIES.md

### Adding an Event Handler

**Do this:**
1. Define handler method: `def handle_new_action(self):`
2. Connect in appropriate setup method (usually in controller setup)
3. Prefix handler names with `handle_` for clarity
4. Follow existing patterns for slot signatures

**Example:**
```python
def handle_new_action(self):
    """Handle new action from controller."""
    # Implementation
    pass

# In controller setup:
self.some_controller.action_signal.connect(self.handle_new_action)
```

### Modifying Page Navigation

**Be careful:**
- Page constants (0, 1, 2, ...) must match UI page list index
- `self.stacked_widget.setCurrentIndex()` uses these indices
- Sidebar navigation sends index — must match actual page order
- FILE_DEPENDENCIES.md section 4 documents the current mapping

**Verify after changes:**
```python
# Confirm order matches FILE_DEPENDENCIES.md:
self.pages = [
    self.media_loader_page,    # INDEX 0
    self.pitch_page,           # INDEX 1
    self.audio_studio_page,    # INDEX 2
    self.video_tools_page,     # INDEX 3
    self.convert_export_page   # INDEX 4
]
```

---

## Critical Sections NOT to Modify Without Understanding

| Section | Why | Before Modifying |
|---------|-----|------------------|
| `__init__` initialization order | Services must exist before controllers | Trace all dependencies |
| Page index constants | Must match sidebar order | Check FILE_DEPENDENCIES.md |
| `app_state` instantiation | Central state container | Understand all state fields |
| Controller initialization | Event connections depend on order | Test page navigation |

---

## After Editing

1. **Syntax check:**
   ```powershell
   python -m py_compile source_code\main.py
   ```

2. **Test window launch:**
   ```powershell
   python source_code\main.py
   ```
   Verify window opens and all pages accessible.

3. **Update related files:**
   - Did you add a service? Update `build_system/KaraokeStudioPro.spec`
   - Did you add a page? Update page index constants in FILE_DEPENDENCIES.md
   - Did you modify page order? Verify sidebar navigation still works

4. **Update documentation:**
   - FILE_DEPENDENCIES.md
   - ARCHITECTURE.md (if structural changes)
   - DEVELOPMENT.md (if adding new patterns)
   - IMPLEMENTATION_LOG.md

---

## Common Mistakes

- ❌ Add service but forget to update build spec → .exe won't include module
- ❌ Change page index but not update constants → Pages don't load correctly
- ❌ Add UI component but don't import it → ImportError on startup
- ❌ Forget to pass service to controller that needs it → AttributeError at runtime
- ❌ Import from wrong package path → "No module named" error

---

## Key Variables & Methods to Know

```python
self.app_state          # Central runtime state container
self.pages              # List of all UI page widgets in order
self.stacked_widget     # QStackedWidget managing visible page
self.video_frame        # VLC video display widget
self.audio_meter        # Real-time audio visualization
self.playback_bar       # Play/pause/seek controls

# Controllers (orchestration)
self.playback_controller
self.media_controller
self.processing_controller
self.navigation_controller

# Services (features)
self.player_service
self.download_service
self.audio_service
self.file_loading_service
```

See [ARCHITECTURE.md](../../documentation/ARCHITECTURE.md) for full module descriptions.
