module params_dut #(
    parameter WIDTH = 8
) (
    input  [WIDTH-1:0] vec_in,
    output [WIDTH-1:0] vec_out
);

    assign vec_out = vec_in;

endmodule
