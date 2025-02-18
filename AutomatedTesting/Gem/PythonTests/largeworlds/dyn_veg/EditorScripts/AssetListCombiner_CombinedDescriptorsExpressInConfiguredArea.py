"""
Copyright (c) Contributors to the Open 3D Engine Project.
For complete copyright and license terms please see the LICENSE at the root of this distribution.

SPDX-License-Identifier: Apache-2.0 OR MIT
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import azlmbr.bus as bus
import azlmbr.editor as editor
import azlmbr.legacy.general as general
import azlmbr.math as math
import azlmbr.paths
import azlmbr.vegetation as vegetation

sys.path.append(os.path.join(azlmbr.paths.devroot, 'AutomatedTesting', 'Gem', 'PythonTests'))
import editor_python_test_tools.hydra_editor_utils as hydra
from editor_python_test_tools.editor_test_helper import EditorTestHelper
from largeworlds.large_worlds_utils import editor_dynveg_test_helper as dynveg


class TestAssetListCombiner(EditorTestHelper):
    def __init__(self):
        EditorTestHelper.__init__(self, log_prefix="AssetListCombiner_CombinedDescriptors", args=["level"])

    def run_test(self):
        """
        Summary:
        Combined descriptors appear as expected in a vegetation area. Also verifies remove/replace of assigned Asset
        Lists.

        Expected Behavior:
        Vegetation fills in the area using the assets assigned to both Vegetation Asset Lists.

        Test Steps:
         1) Create a new, temporary level
         2) Create 3 entities with Vegetation Asset List components set to spawn different descriptors
         3) Create a planting surface and add a Vegetation System Settings level component with instances set to spawn
            on center instead of corner
         4) Create a spawner using a Vegetation Asset List Combiner component and a Weight Selector, and disallow
            spawning empty assets
         5) Add 2 of the Asset List entities to the Vegetation Asset List Combiner component (PinkFlower and Empty)
         6) Create a Constant Gradient entity as a child of the spawner entity, and a Dither Gradient Modifier entity
            as a child of the Constant Gradient entity, and configure for a checkerboard pattern
         7) Pin the Dither Gradient Entity to the Asset Weight Selector of the spawner entity
         8) Validate instance count with configured Asset List Combiner
         9) Replace the reference to the 2nd asset list on the Vegetation Asset List Combiner component and validate
            instance count
        10) Remove the referenced Asset Lists on the Asset List Combiner, Disable/Re-enable the Asset List
            Combiner component to force a refresh, and validate instance count

        Note:
        - This test file must be called from the Open 3D Engine Editor command terminal
        - Any passed and failed tests are written to the Editor.log file.
                Parsing the file or running a log_monitor are required to observe the test results.

        :return: None
        """

        def create_asset_list_entity(name, center, dynamic_slice_asset_path):
            asset_list_entity = hydra.Entity(name)
            asset_list_entity.create_entity(
                center,
                ["Vegetation Asset List"]
            )
            if asset_list_entity.id.IsValid():
                print(f"'{asset_list_entity.name}' created")

            # Set the Asset List to a Dynamic Slice spawner with a specific slice asset selected
            dynamic_slice_spawner = vegetation.DynamicSliceInstanceSpawner()
            dynamic_slice_spawner.SetSliceAssetPath(dynamic_slice_asset_path)
            descriptor = hydra.get_component_property_value(asset_list_entity.components[0],
                                                            "Configuration|Embedded Assets|[0]")
            descriptor.spawner = dynamic_slice_spawner
            asset_list_entity.get_set_test(0, "Configuration|Embedded Assets|[0]", descriptor)
            return asset_list_entity

        # 1) Create a new, temporary level
        self.test_success = self.create_level(
            self.args["level"],
            heightmap_resolution=1024,
            heightmap_meters_per_pixel=1,
            terrain_texture_resolution=4096,
            use_terrain=False,
        )

        # Set view of planting area for visual debugging
        general.set_current_view_position(512.0, 500.0, 38.0)
        general.set_current_view_rotation(-20.0, 0.0, 0.0)

        # 2) Create 3 entities with Vegetation Asset List components set to spawn different descriptors
        center_point = math.Vector3(512.0, 512.0, 32.0)
        asset_path = os.path.join("Slices", "PinkFlower.dynamicslice")
        asset_path2 = os.path.join("Slices", "PurpleFlower.dynamicslice")
        asset_list_entity = create_asset_list_entity("Asset List 1", center_point, asset_path)
        asset_list_entity2 = create_asset_list_entity("Asset List 2", center_point, None)
        asset_list_entity3 = create_asset_list_entity("Asset List 3", center_point, asset_path2)

        # 3) Create a planting surface and add a Vegetation System Settings level component with instances set to spawn
        # on center instead of corner
        dynveg.create_surface_entity("Surface Entity", center_point, 32.0, 32.0, 1.0)
        veg_system_settings_component = hydra.add_level_component("Vegetation System Settings")
        editor.EditorComponentAPIBus(bus.Broadcast, "SetComponentProperty", veg_system_settings_component,
                                     'Configuration|Area System Settings|Sector Point Snap Mode', 1)

        # 4) Create a spawner using a Vegetation Asset List Combiner component and a Weight Selector, and disallow
        # spawning empty assets
        spawner_entity = dynveg.create_vegetation_area("Spawner Entity", center_point, 16.0, 16.0, 16.0, None)
        spawner_entity.remove_component("Vegetation Asset List")
        spawner_entity.add_component("Vegetation Asset List Combiner")
        spawner_entity.add_component("Vegetation Asset Weight Selector")
        spawner_entity.get_set_test(0, "Configuration|Allow Empty Assets", False)

        # 5) Add the Asset List entities to the Vegetation Asset List Combiner component
        asset_list_entities = [asset_list_entity.id, asset_list_entity2.id]
        spawner_entity.get_set_test(2, "Configuration|Descriptor Providers", asset_list_entities)

        # 6) Create a Constant Gradient entity as a child of the spawner entity, and a Dither Gradient Modifier entity
        # as a child of the Constant Gradient entity, and configure for a checkerboard pattern
        components_to_add = ["Constant Gradient"]
        constant_gradient_entity = hydra.Entity("Constant Gradient Entity")
        constant_gradient_entity.create_entity(center_point, components_to_add, parent_id=spawner_entity.id)
        constant_gradient_entity.get_set_test(0, "Configuration|Value", 0.5)

        components_to_add = ["Dither Gradient Modifier"]
        dither_gradient_entity = hydra.Entity("Dither Gradient Entity")
        dither_gradient_entity.create_entity(center_point, components_to_add, parent_id=constant_gradient_entity.id)
        dither_gradient_entity.get_set_test(0, "Configuration|Gradient|Gradient Entity Id", constant_gradient_entity.id)

        # 7) Pin the Dither Gradient Entity to the Asset Weight Selector of the spawner entity
        spawner_entity.get_set_test(3, "Configuration|Gradient|Gradient Entity Id", dither_gradient_entity.id)

        # 8) Validate instance count. We should now have 200 instances in the spawner area as every other instance
        # should be an empty asset which the spawner is set to disallow
        num_expected = 20 * 20 / 2
        success = self.wait_for_condition(lambda: dynveg.validate_instance_count_in_entity_shape(spawner_entity.id,
                                                                                                 num_expected), 5.0)
        self.test_success = success and self.test_success

        # 9) Replace the reference to the 2nd asset list on the Vegetation Asset List Combiner component and validate
        # instance count. Should now be 400 instances as the empty spaces can now be claimed by the new descriptor
        spawner_entity.get_set_test(2, "Configuration|Descriptor Providers|[1]", asset_list_entity3.id)
        num_expected = 20 * 20
        success = self.wait_for_condition(lambda: dynveg.validate_instance_count_in_entity_shape(spawner_entity.id,
                                                                                                 num_expected), 5.0)
        self.test_success = success and self.test_success

        # 10) Remove the referenced Asset Lists on the Asset List Combiner, Disable/Re-enable the Asset List
        # Combiner component to force a refresh, and validate instance count. We should now have 0 instances.
        pte = hydra.get_property_tree(spawner_entity.components[2])
        path = "Configuration|Descriptor Providers"
        pte.reset_container(path)
        # Component refresh is currently necessary due to container operations not causing a refresh (LY-120947)
        editor.EditorComponentAPIBus(bus.Broadcast, "DisableComponents", [spawner_entity.components[2]])
        editor.EditorComponentAPIBus(bus.Broadcast, "EnableComponents", [spawner_entity.components[2]])
        num_expected = 0
        success = self.wait_for_condition(lambda: dynveg.validate_instance_count_in_entity_shape(spawner_entity.id,
                                                                                                 num_expected), 5.0)
        self.test_success = success and self.test_success


test = TestAssetListCombiner()
test.run()
