"""Per-import collection topology builder.

Phase 3 of the Blender 5 modernisation: every GMDL import gets a single root
collection with predictable, prefixed sub-collections so models from different
imports never collide in the Outliner and so users can hide / colour-tag whole
families of objects in one click.

Topology
--------
::

    Scene.collection
    └─ <model>                      color_tag = COLOR_01
       ├─ <armature object>         (linked directly into root, not a sub-coll)
       ├─ <model>.LOD0              color_tag = COLOR_04
       ├─ <model>.LOD1              color_tag = COLOR_04
       ├─ <model>.VEMs              color_tag = COLOR_05  (only if has_vems)
       └─ <model>.Parts             color_tag = COLOR_06  (only if has_parts)
          └─ <PartName> Empties

The armature object continues to live directly under the root collection
(unchanged from earlier phases). LOD / VEM / Parts sub-collections are
created lazily — callers ask for a LOD slot by ``lod_near`` value and receive
a stable, ordered ``LOD<n>`` collection.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import bpy
from bpy.types import Collection

# ---------------------------------------------------------------------------
# Color tag palette
# ---------------------------------------------------------------------------

# Blender 4.1+ uses a string enum for ``Collection.color_tag``. Centralise the
# choices so the palette can be retuned in one place.
COLOR_TAG_ROOT = "COLOR_01"  # red
COLOR_TAG_LOD = "COLOR_04"  # green
COLOR_TAG_VEM = "COLOR_05"  # blue
COLOR_TAG_PARTS = "COLOR_06"  # purple


# ---------------------------------------------------------------------------
# Root collection bundle
# ---------------------------------------------------------------------------


@dataclass
class RootCollections:
    """Tracks every collection associated with a single GMDL import."""

    model_name: str
    root: Collection
    lods: dict[float, Collection] = field(default_factory=dict)
    vems: Collection | None = None
    parts: Collection | None = None

    # ------------------------------------------------------------------
    # LOD slot management
    # ------------------------------------------------------------------
    def get_or_create_lod(self, lod_near: float, ordinal: int) -> Collection:
        """Return the LOD collection for ``lod_near``, creating it if missing.

        ``ordinal`` is the zero-based LOD index used for the visible name
        (``<model>.LOD0``, ``<model>.LOD1``, ...). The caller is responsible
        for assigning consistent ordinals across the import.
        """
        existing = self.lods.get(lod_near)
        if existing is not None:
            return existing

        coll = bpy.data.collections.new(f"{self.model_name}.LOD{ordinal}")
        coll.color_tag = COLOR_TAG_LOD
        self.root.children.link(coll)
        self.lods[lod_near] = coll
        return coll

    # ------------------------------------------------------------------
    # VEM slot
    # ------------------------------------------------------------------
    def ensure_vems(self) -> Collection:
        """Return the (lazily created) VEMs sub-collection."""
        if self.vems is None:
            self.vems = bpy.data.collections.new(f"{self.model_name}.VEMs")
            self.vems.color_tag = COLOR_TAG_VEM
            self.root.children.link(self.vems)
        return self.vems

    # ------------------------------------------------------------------
    # Parts slot
    # ------------------------------------------------------------------
    def ensure_parts(self) -> Collection:
        """Return the (lazily created) Parts sub-collection."""
        if self.parts is None:
            self.parts = bpy.data.collections.new(f"{self.model_name}.Parts")
            self.parts.color_tag = COLOR_TAG_PARTS
            self.root.children.link(self.parts)
        return self.parts

    # ------------------------------------------------------------------
    # Scene linking
    # ------------------------------------------------------------------
    def link_to_scene(self) -> None:
        """Idempotently link the root collection into the active scene."""
        scene_children = bpy.context.scene.collection.children
        if self.root.name not in scene_children:
            scene_children.link(self.root)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def build_root_collections(model_name: str, root: Collection) -> RootCollections:
    """Wrap an existing root ``Collection`` in a ``RootCollections`` bundle.

    ``ImportContext`` already creates the bare root in its ``__init__`` so the
    collection name is committed before the gfxbin is parsed. This helper
    just attaches the colour tag and returns the bundle that the importer
    will populate as it discovers LODs / VEMs / parts.
    """
    root.color_tag = COLOR_TAG_ROOT
    return RootCollections(model_name=model_name, root=root)


# ---------------------------------------------------------------------------
# Parts Empties
# ---------------------------------------------------------------------------


def create_part_empties(
    rc: RootCollections,
    part_names: list[str],
    parent: bpy.types.Object | None = None,
) -> list[bpy.types.Object]:
    """Create one Empty per named part inside ``rc.parts``.

    Returns the created Empties in the same order as ``part_names``. If
    ``parent`` is given (typically the armature object), each Empty is
    parented to it. Empties are placed at the world origin — the source
    GMDL parts data carries no transform information.
    """
    if not part_names:
        return []

    parts_coll = rc.ensure_parts()
    created: list[bpy.types.Object] = []
    for name in part_names:
        empty = bpy.data.objects.new(name=name, object_data=None)
        empty.empty_display_type = "PLAIN_AXES"
        empty.empty_display_size = 0.1
        if parent is not None:
            empty.parent = parent
        parts_coll.objects.link(empty)
        created.append(empty)
    return created
