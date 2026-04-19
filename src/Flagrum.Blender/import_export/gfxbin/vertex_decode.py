"""Vectorised decoders for Luminous vertex streams.

The legacy code path (see the commented-out block in ``gmdlimporter.py``)
walked every vertex in a Python loop and called ``np.frombuffer`` per element
per vertex.  For meshes with tens of thousands of vertices and 4-6 elements
this single loop dominated import time.

This module replaces that pattern with a single ``np.frombuffer`` call per
vertex stream using a structured ``numpy`` dtype that reproduces the on-disk
record layout (matching ``GmdlVertexStream.stride`` exactly, including any
padding bytes between elements).  Each element is then decoded into its
final float / integer form with one vectorised expression instead of N
Python iterations.
"""

from __future__ import annotations

import numpy as np

from .gmdl.gmdlvertexelementformat import ElementFormat

# Per-format raw numpy dtype + component count + post-decode conversion.
#
# ``raw_dtype`` is the storage type as it sits in the buffer (little-endian).
# ``count`` is how many components the element has.
# ``scale`` (when set) divides the raw integer values to produce the final
# normalised ``float32`` output; ``signed_norm`` uses ``1 / 0x7F`` style
# division and is applied to signed integer normalised formats.
_FORMAT_DECODERS: dict[ElementFormat, tuple[np.dtype, int, str]] = {
    ElementFormat.XYZ32_Float: (np.dtype("<f4"), 3, "float"),
    ElementFormat.XY32_Float: (np.dtype("<f4"), 2, "float"),
    ElementFormat.XY16_SintN: (np.dtype("<i2"), 2, "signed_norm"),
    ElementFormat.XY16_UintN: (np.dtype("<u2"), 2, "unsigned_norm"),
    ElementFormat.XY16_Float: (np.dtype("<f2"), 2, "float"),
    ElementFormat.XYZW8_UintN: (np.dtype("<u1"), 4, "unsigned_norm"),
    ElementFormat.XYZW8_Uint: (np.dtype("<u1"), 4, "uint"),
    ElementFormat.XYZW8_SintN: (np.dtype("<i1"), 4, "signed_norm"),
    ElementFormat.XYZW8_Sint: (np.dtype("<i1"), 4, "int"),
    ElementFormat.XYZW16_Uint: (np.dtype("<u2"), 4, "uint"),
    ElementFormat.XYZW32_Uint: (np.dtype("<u4"), 4, "uint"),
}


# Maximum signed value for each integer dtype kind (used by signed_norm).
_SIGNED_MAX = {
    np.dtype("<i1"): 0x7F,
    np.dtype("<i2"): 0x7FFF,
    np.dtype("<i4"): 0x7FFFFFFF,
}

# Maximum unsigned value for each integer dtype kind (used by unsigned_norm).
_UNSIGNED_MAX = {
    np.dtype("<u1"): 0xFF,
    np.dtype("<u2"): 0xFFFF,
    np.dtype("<u4"): 0xFFFFFFFF,
}


def _build_struct_dtype(stream) -> tuple[np.dtype, list]:
    """Build a structured dtype for ``stream`` plus the list of decodable elements.

    Elements with unsupported formats (those missing from ``_FORMAT_DECODERS``)
    are skipped so they don't break the structured read for the rest.
    """
    names: list[str] = []
    formats: list = []
    offsets: list[int] = []
    decodable: list = []

    for index, element in enumerate(stream.elements):
        decoder = _FORMAT_DECODERS.get(element.format)
        if decoder is None:
            print(f"[ERROR] Unsupported element format {element.format!s} on {element.semantic}")
            continue
        raw_dtype, count, _ = decoder
        # Field names must be unique even if two semantics collide; index
        # them to guarantee uniqueness within the structured dtype.
        field_name = f"f{index}"
        names.append(field_name)
        formats.append((raw_dtype, count) if count > 1 else raw_dtype)
        offsets.append(element.offset)
        decodable.append((field_name, element))

    struct_dtype = np.dtype(
        {
            "names": names,
            "formats": formats,
            "offsets": offsets,
            "itemsize": stream.stride,
        }
    )
    return struct_dtype, decodable


def _convert(raw: np.ndarray, element_format: ElementFormat) -> np.ndarray:
    """Apply the post-decode conversion for ``element_format`` to ``raw``."""
    decoder = _FORMAT_DECODERS[element_format]
    raw_dtype, _count, kind = decoder

    # Ensure 2D shape ``(N, count)`` even for single-component fields so
    # downstream code can index uniformly.  Structured field reads return
    # shape ``(N,)`` for count == 1 and ``(N, count)`` for count > 1.
    if raw.ndim == 1:
        raw = raw.reshape(-1, 1)

    if kind == "float":
        return raw.astype(np.float32, copy=False)
    if kind == "signed_norm":
        scale = np.float32(1.0 / _SIGNED_MAX[raw_dtype])
        return raw.astype(np.float32) * scale
    if kind == "unsigned_norm":
        scale = np.float32(1.0 / _UNSIGNED_MAX[raw_dtype])
        return raw.astype(np.float32) * scale
    if kind in ("uint", "int"):
        # Keep raw integer values (callers index into bone tables, etc.).
        # Copy so the caller can mutate without aliasing the buffer.
        return raw.copy()
    raise ValueError(f"Unknown decode kind {kind!r} for {element_format!r}")


def decode_vertex_streams(buffer: bytes, mesh_data) -> dict[str, np.ndarray]:
    """Decode every vertex stream of ``mesh_data`` in one structured read.

    Returns a ``{semantic: ndarray}`` map.  Float arrays are ``float32``
    and shaped ``(vertex_count, components)``; integer arrays preserve their
    on-disk dtype so downstream code can use them as indices verbatim.
    """
    semantics: dict[str, np.ndarray] = {}
    vertex_count = mesh_data.vertex_count
    if vertex_count <= 0:
        return semantics

    for stream in mesh_data.vertex_streams:
        struct_dtype, decodable = _build_struct_dtype(stream)
        if not decodable:
            continue

        base_offset = mesh_data.vertex_buffer_offset + stream.offset
        records = np.frombuffer(
            buffer,
            dtype=struct_dtype,
            count=vertex_count,
            offset=base_offset,
        )

        for field_name, element in decodable:
            semantics[element.semantic] = _convert(records[field_name], element.format)

    return semantics
