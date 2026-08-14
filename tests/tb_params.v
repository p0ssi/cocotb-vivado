module tb_params #(
    parameter WIDTH = 8,
    parameter DEPTH = 4
) (
    input clk,
    input [WIDTH-1:0] vec_in,
    output [WIDTH-1:0] vec_out,
    output [DEPTH-1:0] depth_out
);

    assign vec_out = vec_in;
    assign depth_out = {DEPTH{clk}};

endmodule
