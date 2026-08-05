# parameters

Sweep a top-level Verilog parameter through the Python runner. The DUT
is a pass-through with a parameterized vector width; pytest's
`@pytest.mark.parametrize` drives `runner.build(parameters=...)` with
WIDTH ∈ {8, 16, 32, 64}, and the cocotb test reads `len(dut.vec_out)`
to verify the elaborated width matches.

## What this example demonstrates

- `runner.build(parameters={"WIDTH": w})` forwarding values to xelab as
  `-generic_top WIDTH=w`.
- Pytest parametrization driving multiple build/test cycles from a
  single test source.
- Reading the elaborated width inside the cocotb test via
  `len(dut.vec_out)`.

## Run

```bash
source /path/to/Vivado/<version>/settings64.sh
cd examples/parameters
pytest -s test_parameters.py
```
