# Copyright cocotb-vivado contributors
# Copyright 2026 Kiran Vuksanaj
# Licensed under the Apache License 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
#
# Derived from vicoco's gpi_emulation
# (https://github.com/kiran-vuksanaj/vicoco); adapted for cocotb 1.x/2.x.

"""``cocotb.simulator`` replacement that talks to the XSI manager.

Forward every callback registration and handle query to
:class:`cocotb_vivado.stub.manager.Mgr`. Mirrors vicoco's
``gpi_emulation.py`` shape (cocotb 1.x flavor) for the call surface
and forwarding pattern.
"""

import traceback

from .manager import Mgr

# GPI type tags cocotb 1.x checks against ``get_type()``.
MODULE = 0
STRUCTURE = 1
REG = 2
NET = 3
NETARRAY = 4
REAL = 5
INTEGER = 6
ENUM = 8
STRING = 9
GENARRAY = 10

# Edge-type constants for value-change callbacks (cocotb 1.x convention).
RISING = 11
FALLING = 12
VALUE_CHANGE = 13

# Used by XsimRootHandle.iterate; cocotb expects the module to have it.
OBJECTS = []


def get_root_handle(root_name):
    return Mgr.inst().get_root_handle()


def register_timed_callback(t, cb, ud):
    try:
        return Mgr.inst().register_timed_callback(t, cb, ud)
    except Exception as e:
        print(f"Exception while registering timed callback: {e!s}")
        traceback.print_exc()


def register_value_change_callback(handle, callback, edge, ud):
    return Mgr.inst().register_value_change_callback(handle, callback, edge, ud)


def register_readonly_callback(cb, ud):
    return Mgr.inst().register_readonly_callback(cb, ud)


def register_nextstep_callback(cb, ud):
    # cocotb's "nextstep" semantically means "fire after the smallest
    # advance"; the timed queue with t=1 gives that ordering.
    return Mgr.inst().register_timed_callback(1, cb, ud)


def register_rwsynch_callback(cb, ud):
    return Mgr.inst().register_readwrite_callback(cb, ud)


def stop_simulator():
    Mgr.inst().stop_simulator()


def log_msg(*args, **kwargs):
    raise Exception("cocotb-xsim: Calling cocotb log_msg is not supported")


def log_level(level):
    pass


def is_running(*args, **kwargs):
    raise Exception("cocotb-xsim: Calling cocotb is_running is not supported")


def get_sim_time():
    time = Mgr.inst().get_sim_time()
    # cocotb 1.x expects a (upper32, lower32) tuple.
    return (0, time)


def get_precision():
    # cocotb expects an int log-base-10 of the precision; matches vicoco's
    # hardcoded picosecond default. XSI's get_int(xsiTimePrecisionKernel)
    # returns the kernel precision but cocotb wants a fixed exponent.
    return -12


def get_simulator_product():
    return f"cocotb-vivado-sim with design {Mgr.inst().get_design_name()}"


def get_simulator_version():
    return "0.0.1"
