"""Test-wide guards.

Tests import swiftbar/gympulse.10m.py directly; without this guard Python
drops __pycache__/*.pyc into swiftbar/, and if SwiftBar is pointed at that
folder it picks the .pyc up as a broken plugin (real incident: the menu-bar
item vanished).
"""
import sys

sys.dont_write_bytecode = True
