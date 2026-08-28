`timescale 1 ns / 1 ps

// Minimal DUT for exercising the value-change manager: `tog` flips on
// every rising `clk` edge, so RisingEdge / FallingEdge triggers on both
// `clk` and `tog` have something to fire on.
module edge_dut (
    input  wire clk,
    output reg  tog
);
    initial tog = 1'b0;
    always @(posedge clk) tog <= ~tog;
endmodule
