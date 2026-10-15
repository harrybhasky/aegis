module top(input clk, input rst, input [31:0] in, output reg [31:0] out);
  reg [31:0] comb;
  always @* begin
    comb = in + 1; // simple comb logic
  end
  always @(posedge clk) begin
    if (rst) out <= 0; else out <= comb;
  end
endmodule
