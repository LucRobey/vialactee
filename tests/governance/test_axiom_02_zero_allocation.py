"""
tests/governance/test_axiom_02_zero_allocation.py
Enforces AXIOM-02: Zero Dynamic Heap Allocations in Render Hot Path
- AST inspection of Mode_master.update()
- Connector.on_frame_tick decoupling
- Transition_Director.is_in_transition property
"""
import ast
import inspect
import os
import unittest
import unittest.mock

from core.Mode_master import Mode_master
from connectors.Connector import Connector
from core.Transition_Director import Transition_Director


class TestAxiom02ZeroAllocation(unittest.TestCase):
    def test_mode_master_update_no_str_type_allocations(self):
        """Verify Mode_master.update() does not invoke str(type(...)) dynamically."""
        source = inspect.getsource(Mode_master.update)
        self.assertNotIn(
            "str(type(", source,
            "AXIOM-02 violation: dynamic str(type(...)) allocation found in Mode_master.update()"
        )

    def test_mode_master_caches_rpi_hardware(self):
        """Verify Mode_master initializes and caches _is_rpi_hardware."""
        init_source = inspect.getsource(Mode_master.__init__)
        self.assertIn(
            "_is_rpi_hardware", init_source,
            "AXIOM-02 violation: _is_rpi_hardware must be cached in __init__"
        )

    def test_transition_director_is_in_transition_property(self):
        """Verify Transition_Director provides boolean is_in_transition property."""
        self.assertTrue(hasattr(Transition_Director, "is_in_transition"))
        prop = getattr(Transition_Director, "is_in_transition")
        self.assertTrue(isinstance(prop, property), "is_in_transition must be a property")

    def test_connector_on_frame_tick_zero_overhead_bypass(self):
        """Verify Connector.on_frame_tick exits immediately if no websockets connected."""
        source = inspect.getsource(Connector.on_frame_tick)
        self.assertIn(
            "len(self.active_websockets) == 0", source,
            "AXIOM-02 violation: on_frame_tick must bypass when active_websockets is empty"
        )

    def test_connector_on_frame_tick_runtime_bypass(self):
        """Verify Connector.on_frame_tick does not touch mode_master when no WS connected."""
        import asyncio
        connector = Connector(None, {"startServer": False})
        mock_mm = unittest.mock.MagicMock()
        asyncio.run(connector.on_frame_tick(mock_mm))
        mock_mm.get_state_snapshot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
