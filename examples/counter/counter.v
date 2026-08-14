module counter (
    input clk,
    input rst,
    output reg [7:0] q
);

    always @(posedge clk or posedge rst) begin
        if (rst)
            q <= 8'd0;
        else
            q <= q + 1;
    end

endmodule
