# counter

The minimal "hello world" example: an 8-bit synchronous up-counter with
a reset, driven by a cocotb test that verifies the output increments
every clock edge.

## What this example demonstrates

- The minimum cocotb-vivado runner invocation: `get_runner("vivado")` →
  `build()` → `test()`.
- A `@cocotb.test()` function as the testbench body, with a
  `cocotb.clock.Clock` driving the design's clock.

## Run

```bash
source /path/to/Vivado/<version>/settings64.sh
cd examples/counter
pytest -s test_counter.py
```
