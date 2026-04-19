import bpy
from bpy.props import PointerProperty
from bpy.utils import register_class, unregister_class

from .globals import FlagrumGlobals
from .import_export.menu import (
    ExportOperator,
    FlagrumImportMenu,
    ImportEnvironmentOperator,
    ImportOperator,
    ImportTerrainOperator,
)
from .panel.cleanup_panel import (
    CleanupPanel,
    DeleteUnusedBonesOperator,
    DeleteUnusedVGroupsOperator,
    NormaliseWeightsOperator,
)
from .panel.material_data import FlagrumMaterialProperty, FlagrumMaterialPropertyCollection, MaterialSettings
from .panel.material_panel import (
    ClearTextureOperator,
    MaterialCopyOperator,
    MaterialEditorPanel,
    MaterialImportOperator,
    MaterialPasteOperator,
    MaterialResetOperator,
    TextureSlotOperator,
)
from .panel.normals_panel import NormalsPanel, SplitEdgesOperator, UseCustomNormalsOperator
from .panel.parts_panel import (
    AddPartsGroupOperator,
    AssignPartsGroupOperator,
    DeselectPartsGroupOperator,
    PartsGroup,
    PartsGroupsList,
    PartsSettings,
    PartsSystemPanel,
    PartsVertex,
    RemovePartsGroupOperator,
    SelectPartsGroupOperator,
    UnassignPartsGroupOperator,
)
from .panel.rendering_panel import RenderingPanel, SetEmissionOperator, ToggleEmissionOperator

# NOTE: ``bl_info`` is intentionally absent. Packaging metadata lives in
# ``blender_manifest.toml`` (Blender Extensions Platform, 4.2+).

classes = (
    ImportOperator,
    ExportOperator,
    ImportEnvironmentOperator,
    ImportTerrainOperator,
    FlagrumImportMenu,
    FlagrumMaterialProperty,
    FlagrumMaterialPropertyCollection,
    TextureSlotOperator,
    ClearTextureOperator,
    MaterialResetOperator,
    MaterialImportOperator,
    MaterialCopyOperator,
    MaterialPasteOperator,
    MaterialEditorPanel,
    MaterialSettings,
    UseCustomNormalsOperator,
    SplitEdgesOperator,
    DeleteUnusedBonesOperator,
    DeleteUnusedVGroupsOperator,
    NormaliseWeightsOperator,
    CleanupPanel,
    NormalsPanel,
    ToggleEmissionOperator,
    SetEmissionOperator,
    RenderingPanel,
    FlagrumGlobals,
    PartsVertex,
    PartsGroup,
    PartsSettings,
    AddPartsGroupOperator,
    RemovePartsGroupOperator,
    PartsGroupsList,
    AssignPartsGroupOperator,
    UnassignPartsGroupOperator,
    SelectPartsGroupOperator,
    DeselectPartsGroupOperator,
    PartsSystemPanel,
)


def import_menu_item(self, context):
    self.layout.menu(FlagrumImportMenu.bl_idname)


def export_menu_item(self, context):
    self.layout.operator(ExportOperator.bl_idname, text="Flagrum (.fmd)")


def register():
    for cls in classes:
        register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(import_menu_item)
    bpy.types.TOPBAR_MT_file_export.append(export_menu_item)
    bpy.types.Object.flagrum_material = PointerProperty(type=MaterialSettings)
    bpy.types.Object.flagrum_parts = PointerProperty(type=PartsSettings)
    bpy.types.WindowManager.flagrum_material_clipboard = PointerProperty(type=FlagrumMaterialPropertyCollection)
    bpy.types.WindowManager.flagrum_globals = PointerProperty(type=FlagrumGlobals)


def unregister():
    del bpy.types.WindowManager.flagrum_globals
    del bpy.types.WindowManager.flagrum_material_clipboard
    del bpy.types.Object.flagrum_parts
    del bpy.types.Object.flagrum_material
    bpy.types.TOPBAR_MT_file_export.remove(export_menu_item)
    bpy.types.TOPBAR_MT_file_import.remove(import_menu_item)
    for cls in reversed(classes):
        unregister_class(cls)


if __name__ == "__main__":
    register()
