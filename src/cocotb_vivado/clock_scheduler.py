import logging
import typing
from collections import defaultdict
from decimal import Decimal
from numbers import Real

import cocotb.clock
from cocotb import start_soon
from cocotb.utils import get_sim_steps, get_time_from_sim_steps, get_sim_time
from cocotb.task import Task
from cocotb.triggers import Timer, Event


class ScheduledClock:
    """
    Simple 50:50 duty cycle clock driver.

    Mimicing cocotb v1.9.2 interface, although cycle count mechanism is deprecated in v2.0.0
    """
    def __init__(self, signal, period: float|Real|Decimal, units: str = "step"):
        self.signal = signal
        self.period = get_sim_steps(period, units)
        self.frequency = 1 / get_time_from_sim_steps(self.period, units="us")
        self.start_high = False
        self.cycles: int | None = None  # run indefinitely
        self._remaining_cycles = self.cycles
        self._task: Task | None = None
        self._start_time = 0
        self._stop_event = Event()

    async def start(self, cycles: int|None = None, start_high: bool = True):
        """ Start the clock by adding it to the scheduler's clock collection. """
        self.cycles = cycles
        self._remaining_cycles = self.cycles
        self.start_high = start_high

        # record the start time for phase offset, and drive signal initial state
        self._start_time = get_sim_time()
        self._drive_signal(False)

        _scheduler.add_clock(self)
        await self._stop_event.wait()  # wait for clock stop event
        self.stop()

    def stop(self):
        _scheduler.remove_clock(self)

    def _drive_signal(self, new_value: bool):
        """ Set clock signal state """
        if self._remaining_cycles is not None:
            current_value = self.signal.value
            if current_value.is_resolvable:
                if current_value  ^ self.start_high and not new_value:
                    # falling edge, reduce the cycle count
                    self._remaining_cycles -= 1
                if self._remaining_cycles <= 0:
                    # clock finished
                    self._stop_event.set()

        # drive the signal taking phase inversion into account
        self.signal.setimmediatevalue(new_value ^ self.start_high)


class ClockScheduler:
    """
    ClockSheduler singleton instantiated at module import.

    Keeps track of test cases' Clock objects, and implements polling mechanism to implement
    alternative trigger events at every input clock edge.
    """
    def __init__(self):
        self.clocks: list[ScheduledClock] = []
        self.poll_event = Event()
        self.current_time = 0
        self.log = logging.getLogger(self.__module__)
        self.log.setLevel(logging.INFO)
        self._scheduler_task: Task | None = None

    def reset(self):
        self.clocks = []
        self._scheduler_task = None

    def add_clock(self, new_clock: ScheduledClock):
        if self._scheduler_task is not None and self._scheduler_task.done():
            # detect if scheduler task was started but cancelled -> reset sceduler to start fresh
            # this is expected when:
            # 1. previous cocotb.test() or module finishes
            # 2. last running ScheduledClock is stopped
            self.reset()

        for clk in self.clocks:
            if new_clock.signal == clk.signal:
                raise RuntimeError(f"signal {clk.signal._name} already assigned a clock driver")

        # add the clock to scheduler
        self.clocks.append(new_clock)

        # start the sceduler task if not already running
        if self._scheduler_task is None:
            self._scheduler_task = start_soon(self.run())

        # Log clock configuration
        self.log.info("Driving Clock signal: '%s', Frequency: %.3f MHz", new_clock.signal._name, new_clock.frequency)

    def remove_clock(self, clock: ScheduledClock):
        self.clocks.remove(clock)
        if not self.clocks:
            # last clock removed, stop the scheduler
            self._scheduler_task.cancel()

    def _get_clock_transitions(self, current_time):
        """
        Calculate next clock transitions for registered clocks.

        Clock cycle is defined as 50% low - 50% high polarity
        """
        # Advance beyond the current timestep to capture the _next_ transition, hence +1
        current_time += 1

        clk_transitions = []
        for clk in self.clocks:
            half_period = clk.period / 2.0  # assume 50% duty cycle

            # Find the position in the cycle.
            cycle_pos = (current_time - clk._start_time) % clk.period

            if cycle_pos < half_period:
                # Currently low, next transition is rising edge
                transition_time = current_time + (half_period - cycle_pos)
                transition_to = 1
            else:
                # Currently high, next transition is falling edge
                transition_time = current_time + (clk.period - cycle_pos)
                transition_to = 0

            clk_transitions.append((transition_time, (clk, transition_to)))

        # Find earliest time and collect all transitions at that time
        next_transition_time = min(t for t, _ in clk_transitions)
        next_transitions = [item for t, item in clk_transitions if t == next_transition_time]

        return next_transition_time, next_transitions

    async def run(self):
        """ ClockScheduler main coroutine. """
        self.log.info("ClockScheduler started")
        while self.clocks:
            sim_time = get_sim_time()
            next_transition_time, next_clock_transition_ops = self._get_clock_transitions(sim_time)

            wait_time = next_transition_time - sim_time
            await Timer(wait_time, units="step")

            # drive scheduled clk transitions
            for clk, value in next_clock_transition_ops:
                clk._drive_signal(value)

            # trigger update event on every scheduled clock edge
            self.poll_event.set()
            self.poll_event.clear()


# Instantiate scheduler singleton at import
_scheduler = ClockScheduler()


# Overloaded transition triggers using ClockScheduler's poll event
class FallingEdge:
    def __init__(self, signal):
        self.signal = signal

    def __await__(self):
        return self._async_method().__await__()

    async def _async_method(self):
        prev = self.signal.value
        while True:
            await _scheduler.poll_event.wait()
            now = self.signal.value
            if prev.is_resolvable and now.is_resolvable and prev == 1 and now == 0:
                break
            prev = now


class RisingEdge:
    def __init__(self, signal):
        self.signal = signal

    def __await__(self):
        return self._async_method().__await__()

    async def _async_method(self):
        prev = self.signal.value
        while True:
            await _scheduler.poll_event.wait()
            now = self.signal.value
            if prev.is_resolvable and now.is_resolvable and prev == 0 and now == 1:
                break
            prev = now


class Edge:
    def __init__(self, signal):
        self.signal = signal

    def __await__(self):
        return self._async_method().__await__()

    async def _async_method(self):
        prev = self.signal.value
        while True:
            await _scheduler.poll_event.wait()
            now = self.signal.value
            if prev.is_resolvable and now.is_resolvable and prev != now:
                break
            prev = now
