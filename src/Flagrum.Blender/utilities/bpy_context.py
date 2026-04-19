"""Small helpers for safe ``bpy.context`` interactions.

Blender 4.0+ requires ``bpy.context.temp_override(...)`` whenever ``bpy.ops``
is invoked outside of a UI event (background batch jobs, automated tests,
add-on import flows). The legacy implicit-context behaviour is gone in
Blender 5. These helpers centralise the override boilerplate so call sites
stay readable.
"""

from __future__ import annotations

import bpy


def set_object_mode(obj, mode: str) -> None:
    """Switch ``obj`` into ``mode`` using a scoped ``temp_override``.

    Equivalent to ``bpy.ops.object.mode_set(mode=mode)`` but works reliably
    when no active UI context is in scope. ``obj`` is set as the active and
    sole selected object for the duration of the operator call.
    """
    with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
        bpy.ops.object.mode_set(mode=mode)
