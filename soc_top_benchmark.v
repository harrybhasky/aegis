module clk_divider (
    clk_in,
    rst_n,
    clk_out
);
    input clk_in;
    input rst_n;
    output clk_out;

    // Direct wire connection for timing propagation
    assign clk_out = clk_in;
endmodule

module soc_top_benchmark (
    clk_master_main,
    clk_master_mem,
    clk_master_peri,
    clk_master_dsp,
    clk_master_ext,
    rst_n,
    gpio_in,
    gpio_out
);
    input clk_master_main;
    input clk_master_mem;
    input clk_master_peri;
    input clk_master_dsp;
    input clk_master_ext;
    input rst_n;
    input [31:0] gpio_in;
    output [31:0] gpio_out;

    wire clk_main_div2;

    clk_divider u_div_m1_1 (
        .clk_in(clk_master_main),
        .rst_n(rst_n),
        .clk_out(clk_main_div2)
    );

    // Explicit net assignments (supported natively by OpenSTA netlist reader)
    assign gpio_out = gpio_in;

endmodule
