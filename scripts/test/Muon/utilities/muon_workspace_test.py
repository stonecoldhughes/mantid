import unittest
import six

from Muon.GUI.Common.muon_workspace import MuonWorkspace, add_directory_structure

import mantid.simpleapi as simpleapi
from mantid.api import ITableWorkspace, WorkspaceGroup
import mantid.api as api
from mantid.dataobjects import Workspace2D


class MuonWorkspaceTest(unittest.TestCase):
    """
    The MuonWorkspace object is a key class in the muon interface. It is a wrapper around a normal
    Mantid workspace, which maintains a handle to the workspace whilst allowing it to be in the ADS
    or not.

    This allows certain workspaces to be held in the interface, and displayed to the user as and
    when they are necessary.

    It has some extra functionality which allows the workspace to be put in the ADS inside a "folder
    structure" using workspace groups. So for example if I give the name "dir1/dir2/name" then a
    workspace called "name" will be placed inside a group called "dir2" which will istelf be placed
    inside a group called "dir1".

    This allows the complex array of different workspaces from the muon interface to be structured
    in the ADS to improve the user experience.

    """

    def setUp(self):
        assert simpleapi.mtd.size() == 0

    def tearDown(self):
        # clear the ADS
        simpleapi.mtd.clear()

    # ----------------------------------------------------------------------------------------------
    # Test Initialization
    # ----------------------------------------------------------------------------------------------

    def test_that_cannot_initialize_without_supplying_a_workspace(self):
        with self.assertRaises(TypeError):
            MuonWorkspace()

    def test_that_can_initialize_with_Workspace2D_object(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        assert isinstance(workspace, Workspace2D)

        MuonWorkspace(workspace=workspace)

    def test_that_can_initialize_with_TableWorkspace_object(self):
        table_workspace = simpleapi.CreateEmptyTableWorkspace()
        table_workspace.addColumn("int", "col1", 0)
        table_workspace.addColumn("int", "col2", 0)
        [table_workspace.addRow([i + 1, 2 * i]) for i in range(4)]

        assert isinstance(table_workspace, ITableWorkspace)

        MuonWorkspace(workspace=table_workspace)

    def test_that_cannot_initialize_with_WorkspaceGroup_object(self):
        group_workspace = api.WorkspaceGroup()
        assert isinstance(group_workspace, WorkspaceGroup)

        with self.assertRaises(AttributeError):
            MuonWorkspace(workspace=group_workspace)

    def test_that_cannot_initialize_with_non_workspace_objects(self):
        with self.assertRaises(AttributeError):
            MuonWorkspace(workspace="string")

        with self.assertRaises(AttributeError):
            MuonWorkspace(workspace=1234)

        with self.assertRaises(AttributeError):
            MuonWorkspace(workspace=5.5)

    def test_that_initialized_object_is_not_in_ADS_by_default(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        self.assertEqual(workspace_handle.is_hidden, True)

    def test_that_initialized_object_starts_with_empty_string_for_name(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        self.assertEqual(workspace_handle.name, "")

    # ----------------------------------------------------------------------------------------------
    # Test Show/Hide
    # ----------------------------------------------------------------------------------------------

    def test_that_cannot_modify_is_in_ads_property(self):
        # the ADS handling interface is restricted to the show() / hide() methods
        pass

    def test_that_showing_the_workspace_with_empty_string_for_name_raises_ValueError(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        with self.assertRaises(ValueError):
            workspace_handle.show("")

    def test_that_showing_the_workspace_puts_it_in_ADS(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        workspace_handle.show("test")

        self.assertTrue(simpleapi.mtd.doesExist("test"))
        ads_workspace = simpleapi.mtd["test"]
        six.assertCountEqual(self, ads_workspace.readX(0), [1, 2, 3, 4])
        six.assertCountEqual(self, ads_workspace.readY(0), [10, 10, 10, 10])

    def test_that_hiding_the_workspace_removes_it_from_ADS(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)
        workspace_handle.show("test")

        workspace_handle.hide()

        self.assertEqual(workspace_handle.is_hidden, True)
        self.assertFalse(simpleapi.mtd.doesExist("test"))

    def test_that_workspace_property_returns_workspace_when_not_in_ADS(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        ws_property = workspace_handle.workspace

        six.assertCountEqual(self, ws_property.readX(0), [1, 2, 3, 4])
        six.assertCountEqual(self, ws_property.readY(0), [10, 10, 10, 10])

    def test_that_workspace_property_returns_workspace_when_in_ADS(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        workspace_handle.show("arbitrary_name")
        ws_property = workspace_handle.workspace

        six.assertCountEqual(self, ws_property.readX(0), [1, 2, 3, 4])
        six.assertCountEqual(self, ws_property.readY(0), [10, 10, 10, 10])

    def test_that_can_change_name_when_workspace_not_in_ADS(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        workspace_handle.name = "new_name"

        self.assertEqual(workspace_handle.name, "new_name")

    def test_that_running_show_twice_with_different_names_causes_the_workspace_to_be_moved(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        workspace_handle.show("name1")
        workspace_handle.show("name2")

        self.assertFalse(simpleapi.mtd.doesExist("name1"))
        self.assertTrue(simpleapi.mtd.doesExist("name2"))

    def test_that_cannot_change_name_when_workspace_in_ADS(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        workspace_handle.show("name1")

        with self.assertRaises(ValueError):
            workspace_handle.name = "new_name"

    def test_that_hiding_workspace_more_than_once_has_no_effect_but_raises_RuntimeWarning(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)
        workspace_handle.show("name1")

        workspace_handle.hide()

        with self.assertRaises(RuntimeWarning):
            workspace_handle.hide()

    def test_that_if_workspace_deleted_from_ADS_then_hide_raises_a_RuntimeWarning(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)
        workspace_handle.show("name1")

        simpleapi.mtd.clear()

        with self.assertRaises(RuntimeWarning):
            workspace_handle.hide()

    def test_that_hiding_workspace_deletes_groups_which_are_left_empty(self):
        # TODO
        pass

    def test_that_hiding_workspace_does_not_delete_groups_which_still_contain_workspaces(self):
        # TODO
        pass

    # ----------------------------------------------------------------------------------------------
    # Overwriting the workspace via the workspace property
    # ----------------------------------------------------------------------------------------------

    def test_that_setting_a_new_workspace_removes_the_previous_one_from_the_ADS(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)
        workspace_handle.show("name1")

        workspace2 = simpleapi.CreateWorkspace(dataX=[5, 6, 7, 8], dataY=[20, 20, 20, 20])

        self.assertTrue(simpleapi.mtd.doesExist("name1"))
        workspace_handle.workspace = workspace2
        self.assertFalse(simpleapi.mtd.doesExist("name1"))

    def test_that_setting_a_new_workspace_resets_the_name_to_empty_string(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)
        workspace_handle.show("name1")

        workspace2 = simpleapi.CreateWorkspace(dataX=[5, 6, 7, 8], dataY=[20, 20, 20, 20])

        self.assertEqual(workspace_handle.name, "name1")
        workspace_handle.workspace = workspace2
        self.assertEqual(workspace_handle.name, "")


class MuonWorkspaceAddDirectoryTest(unittest.TestCase):
    """
    Test the functionality surrounding adding "directory structures" to the ADS, in other words
    adding nested structures of WorkspaceGroups to help structure the data.
    """

    def setUp(self):
        assert simpleapi.mtd.size() == 0

    def tearDown(self):
        # clear the ADS
        simpleapi.mtd.clear()

    def assert_group_workspace_exists(self, name):
        self.assertTrue(simpleapi.mtd.doesExist(name))
        self.assertEqual(type(simpleapi.mtd.retrieve(name)), WorkspaceGroup)

    def assert_group1_is_inside_group2(self, group1_name, group2_name):
        group2 = simpleapi.mtd.retrieve(group2_name)
        self.assertIn(group1_name, group2.getNames())

    def assert_workspace_in_group(self, workspace_name, group_name):
        group = simpleapi.mtd.retrieve(group_name)
        self.assertIn(workspace_name, group.getNames())

    # ----------------------------------------------------------------------------------------------
    # Test add_directory_structure function
    # ----------------------------------------------------------------------------------------------

    def test_that_passing_empty_list_has_no_effect(self):
        add_directory_structure([])

        self.assertEqual(simpleapi.mtd.size(), 0)

    def test_that_passing_a_list_of_a_single_string_creates_an_empty_group_in_ADS(self):
        add_directory_structure(["testGroup"])

        self.assertEqual(simpleapi.mtd.size(), 1)
        self.assertTrue(simpleapi.mtd.doesExist("testGroup"))
        self.assertEqual(type(simpleapi.mtd.retrieve("testGroup")), WorkspaceGroup)

        group = simpleapi.mtd.retrieve("testGroup")
        self.assertEqual(group.getNumberOfEntries(), 0)

    def test_that_passing_a_list_of_strings_creates_a_group_for_each_string(self):
        add_directory_structure(["testGroup1", "testGroup2", "testGroup3"])

        self.assertEqual(simpleapi.mtd.size(), 3)
        self.assert_group_workspace_exists("testGroup1")
        self.assert_group_workspace_exists("testGroup2")
        self.assert_group_workspace_exists("testGroup3")

    def test_raises_ValueError_if_duplicate_names_given(self):
        # this is necessary due to the ADS requiring all names to be unique irrespectie of object
        # type or nesting

        with self.assertRaises(ValueError):
            add_directory_structure(["testGroup1", "testGroup2", "testGroup2"])

    def test_that_for_two_names_the_second_group_is_nested_inside_the_first(self):
        add_directory_structure(["testGroup1", "testGroup2"])

        self.assert_group_workspace_exists("testGroup1")
        self.assert_group_workspace_exists("testGroup2")

        self.assert_group1_is_inside_group2("testGroup2", "testGroup1")

    def test_that_nested_groups_up_to_four_layers_are_possible(self):
        add_directory_structure(["testGroup1", "testGroup2", "testGroup3", "testGroup4"])

        self.assert_group1_is_inside_group2("testGroup2", "testGroup1")
        self.assert_group1_is_inside_group2("testGroup3", "testGroup2")
        self.assert_group1_is_inside_group2("testGroup4", "testGroup3")

    def test_that_overwriting_previous_structure_with_a_permutation_works(self):
        add_directory_structure(["testGroup1", "testGroup2", "testGroup3", "testGroup4"])

        add_directory_structure(["testGroup4", "testGroup3", "testGroup2", "testGroup1"])

        self.assert_group1_is_inside_group2("testGroup1", "testGroup2")
        self.assert_group1_is_inside_group2("testGroup2", "testGroup3")
        self.assert_group1_is_inside_group2("testGroup3", "testGroup4")

    def test_that_if_workspace_already_exists_it_is_removed(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        simpleapi.mtd.add("testGroup1", workspace)

        add_directory_structure(["testGroup1", "testGroup2"])

        self.assert_group_workspace_exists("testGroup1")
        self.assert_group_workspace_exists("testGroup2")
        self.assert_group1_is_inside_group2("testGroup2", "testGroup1")

    # ----------------------------------------------------------------------------------------------
    # Test directory structure functionality in Muonworkspace
    # ----------------------------------------------------------------------------------------------

    def test_that_if_workspace_exists_with_same_name_as_group_then_it_is_replaced(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        simpleapi.mtd.add("group", workspace)

        workspace_handle = MuonWorkspace(workspace=workspace)
        workspace_handle.show("group/ws1")

        self.assert_group_workspace_exists("group")

    def test_that_workspace_added_correctly_for_single_nested_structure(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        workspace_handle.show("group1/ws1")

        self.assert_group_workspace_exists("group1")
        self.assert_workspace_in_group("ws1", "group1")

    def test_that_workspace_added_correctly_for_doubly_nested_structure(self):
        workspace = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle = MuonWorkspace(workspace=workspace)

        workspace_handle.show("group1/group2/ws1")

        self.assert_group_workspace_exists("group1")
        self.assert_group_workspace_exists("group2")
        self.assert_group1_is_inside_group2("group2", "group1")
        self.assert_workspace_in_group("ws1", "group2")

    def test_that_workspaces_in_existing_folders_are_not_moved_by_directory_manipulation(self):
        workspace1 = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace2 = simpleapi.CreateWorkspace(dataX=[1, 2, 3, 4], dataY=[10, 10, 10, 10])
        workspace_handle1 = MuonWorkspace(workspace=workspace1)
        workspace_handle2 = MuonWorkspace(workspace=workspace2)

        workspace_handle1.show("group1/group2/ws1")
        workspace_handle2.show("group1/group2/group3/ws2")

        self.assert_group_workspace_exists("group1")
        self.assert_group_workspace_exists("group2")
        self.assert_group_workspace_exists("group3")
        self.assert_group1_is_inside_group2("group2", "group1")
        self.assert_group1_is_inside_group2("group3", "group2")
        self.assert_workspace_in_group("ws1", "group2")
        self.assert_workspace_in_group("ws2", "group3")


if __name__ == '__main__':
    unittest.main(buffer=False, verbosity=2)
