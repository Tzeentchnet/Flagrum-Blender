"""Blender 5.x compatibility helpers.

This module centralises the small number of API shapes that changed across
Blender 4.0–5.0 so the importer and panels can stay readable.

Targets Blender 5.0+ exclusively. No version branching is performed here —
older Blender installs are not supported by this addon (see
``blender_manifest.toml``).

Notable changes wrapped:

* Principled BSDF v2 (Blender 4.0+): socket display names changed
  (``Specular`` → ``Specular IOR Level``, ``Transmission`` →
  ``Transmission Weight``, ``Emission`` → ``Emission Color``, etc.).
* ``ShaderNodeSeparateRGB`` / ``ShaderNodeCombineRGB`` removed in favour of
  ``ShaderNodeSeparateColor`` / ``ShaderNodeCombineColor`` with ``mode``.
* ``ShaderNodeMixRGB`` removed in favour of ``ShaderNodeMix`` with
  ``data_type='RGBA'``.
* Node group sockets are managed via ``group.interface.new_socket(...)``;
  the old ``group.inputs.new()`` / ``group.outputs.new()`` are gone.
* ``Material.blend_method`` is replaced by ``Material.surface_render_method``
  in EEVEE Next (4.2+).
* ``Mesh.use_auto_smooth`` was removed in 4.1 — custom split normals set via
  ``normals_split_custom_set_from_vertices`` are honoured automatically when
  faces are marked smooth.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Principled BSDF socket lookup
# ---------------------------------------------------------------------------

# Logical role → socket display name in Principled BSDF v2 (Blender 4.0+).
_PRINCIPLED_SOCKET_NAMES: dict[str, str] = {
    "base_color": "Base Color",
    "metallic": "Metallic",
    "roughness": "Roughness",
    "ior": "IOR",
    "alpha": "Alpha",
    "normal": "Normal",
    "specular": "Specular IOR Level",
    "specular_tint": "Specular Tint",
    "transmission": "Transmission Weight",
    "subsurface": "Subsurface Weight",
    "subsurface_radius": "Subsurface Radius",
    "sheen": "Sheen Weight",
    "sheen_tint": "Sheen Tint",
    "coat": "Coat Weight",
    "emission": "Emission Color",
    "emission_strength": "Emission Strength",
}


def principled_input(bsdf, role: str):
    """Return a Principled BSDF input socket for a logical ``role``.

    Roles are language-stable (e.g. ``'specular'``, ``'emission'``) while the
    underlying Blender display names continue to evolve.
    """
    name = _PRINCIPLED_SOCKET_NAMES[role]
    return bsdf.inputs[name]


def is_principled_socket(socket, role: str) -> bool:
    """Return True if ``socket`` is the Principled BSDF input for ``role``.

    Use this when iterating over node-tree links and comparing to a logical
    socket role rather than hard-coding a display name that has changed
    between Blender versions.
    """
    return socket.name == _PRINCIPLED_SOCKET_NAMES[role]


# ---------------------------------------------------------------------------
# Replacement node helpers
# ---------------------------------------------------------------------------


def new_separate_color(node_tree, mode: str = "RGB"):
    """Add a Separate Color node (RGB mode by default)."""
    node = node_tree.nodes.new("ShaderNodeSeparateColor")
    node.mode = mode
    return node


def new_combine_color(node_tree, mode: str = "RGB"):
    """Add a Combine Color node (RGB mode by default).

    Inputs in RGB mode are named ``Red``/``Green``/``Blue``.
    """
    node = node_tree.nodes.new("ShaderNodeCombineColor")
    node.mode = mode
    return node


def new_mix_rgba(node_tree, blend_type: str = "MIX", factor: float = 1.0):
    """Add a Mix node configured for RGBA data.

    Sockets in RGBA mode: inputs ``Factor``, ``A``, ``B``; output ``Result``.
    """
    node = node_tree.nodes.new("ShaderNodeMix")
    node.data_type = "RGBA"
    node.blend_type = blend_type
    node.inputs["Factor"].default_value = factor
    return node


# ---------------------------------------------------------------------------
# Node group socket helpers
# ---------------------------------------------------------------------------


def node_group_add_input(group, name: str, socket_type: str):
    """Add an input socket to a node group's interface (Blender 4.0+ API)."""
    return group.interface.new_socket(name=name, in_out="INPUT", socket_type=socket_type)


def node_group_add_output(group, name: str, socket_type: str):
    """Add an output socket to a node group's interface (Blender 4.0+ API)."""
    return group.interface.new_socket(name=name, in_out="OUTPUT", socket_type=socket_type)


# ---------------------------------------------------------------------------
# Material / mesh tweaks
# ---------------------------------------------------------------------------


def set_alpha_clip(material) -> None:
    """Mark a material as alpha-clipped using the EEVEE-Next API."""
    # EEVEE Next (Blender 4.2+) replaced ``blend_method`` with
    # ``surface_render_method``.  ``DITHERED`` is the closest equivalent of
    # the old ``CLIP`` mode for masked geometry.
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    else:  # pragma: no cover — defensive fallback for non-EEVEE-Next builds
        material.blend_method = "CLIP"


def apply_custom_split_normals(mesh, normals) -> None:
    """Apply custom per-vertex split normals to ``mesh``.

    In Blender 4.1+ the ``use_auto_smooth`` flag was removed; custom normals
    are honoured automatically as long as the faces are marked smooth and
    the mesh has been validated.
    """
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.normals_split_custom_set_from_vertices(normals)


# ---------------------------------------------------------------------------
# Vertex color helpers
# ---------------------------------------------------------------------------


def new_corner_color_attribute(mesh, name: str):
    """Create a per-corner byte-color attribute (replaces ``vertex_colors.new``)."""
    return mesh.color_attributes.new(name=name, type="BYTE_COLOR", domain="CORNER")
