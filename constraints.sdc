# ==============================================================================
# SDC CONSTRAINTS: 5 MASTER CLOCKS + 21 GENERATED CLOCKS + CDC GROUPS
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. DEFINE 5 MASTER ASYNCHRONOUS CLOCKS
# ------------------------------------------------------------------------------
# Overclocked clk_master_main to 0.15ns (6.67 GHz) to force negative slack
create_clock -name clk_master_main -period 0.15 [get_ports clk_master_main]
create_clock -name clk_master_mem  -period 8.0  [get_ports clk_master_mem]   ;# 125 MHz
create_clock -name clk_master_peri -period 20.0 [get_ports clk_master_peri]  ;# 50 MHz
create_clock -name clk_master_dsp  -period 5.0  [get_ports clk_master_dsp]   ;# 200 MHz
create_clock -name clk_master_ext  -period 40.0 [get_ports clk_master_ext]   ;# 25 MHz

# ------------------------------------------------------------------------------
# 2. DEFINE 21 GENERATED CLOCKS (Using create_generated_clock)
# ------------------------------------------------------------------------------

# -- Master 1 Generated Clocks (5 Total) --
create_generated_clock -name clk_main_div2  -source [get_ports clk_master_main] -divide_by 2  [get_pins u_div_m1_1/clk_out_reg/Q]
create_generated_clock -name clk_main_div4  -source [get_ports clk_master_main] -divide_by 4  [get_pins u_div_m1_2/clk_out_reg/Q]
create_generated_clock -name clk_main_div8  -source [get_ports clk_master_main] -divide_by 8  [get_pins u_div_m1_3/clk_out_reg/Q]
create_generated_clock -name clk_main_div16 -source [get_ports clk_master_main] -divide_by 16 [get_pins u_div_m1_4/clk_out_reg/Q]
create_generated_clock -name clk_main_div32 -source [get_ports clk_master_main] -divide_by 32 [get_pins u_div_m1_5/clk_out_reg/Q]

# -- Master 2 Generated Clocks (4 Total) --
create_generated_clock -name clk_mem_div2   -source [get_ports clk_master_mem]  -divide_by 2  [get_pins u_div_m2_1/clk_out_reg/Q]
create_generated_clock -name clk_mem_div4   -source [get_ports clk_master_mem]  -divide_by 4  [get_pins u_div_m2_2/clk_out_reg/Q]
create_generated_clock -name clk_mem_div8   -source [get_ports clk_master_mem]  -divide_by 8  [get_pins u_div_m2_3/clk_out_reg/Q]
create_generated_clock -name clk_mem_div16  -source [get_ports clk_master_mem]  -divide_by 16 [get_pins u_div_m2_4/clk_out_reg/Q]

# -- Master 3 Generated Clocks (4 Total) --
create_generated_clock -name clk_peri_div2  -source [get_ports clk_master_peri] -divide_by 2  [get_pins u_div_m3_1/clk_out_reg/Q]
create_generated_clock -name clk_peri_div4  -source [get_ports clk_master_peri] -divide_by 4  [get_pins u_div_m3_2/clk_out_reg/Q]
create_generated_clock -name clk_peri_div8  -source [get_ports clk_master_peri] -divide_by 8  [get_pins u_div_m3_3/clk_out_reg/Q]
create_generated_clock -name clk_peri_div16 -source [get_ports clk_master_peri] -divide_by 16 [get_pins u_div_m3_4/clk_out_reg/Q]

# -- Master 4 Generated Clocks (4 Total) --
create_generated_clock -name clk_dsp_div2   -source [get_ports clk_master_dsp]  -divide_by 2  [get_pins u_div_m4_1/clk_out_reg/Q]
create_generated_clock -name clk_dsp_div4   -source [get_ports clk_master_dsp]  -divide_by 4  [get_pins u_div_m4_2/clk_out_reg/Q]
create_generated_clock -name clk_dsp_div8   -source [get_ports clk_master_dsp]  -divide_by 8  [get_pins u_div_m4_3/clk_out_reg/Q]
create_generated_clock -name clk_dsp_div16  -source [get_ports clk_master_dsp]  -divide_by 16 [get_pins u_div_m4_4/clk_out_reg/Q]

# -- Master 5 Generated Clocks (4 Total) --
create_generated_clock -name clk_ext_div2   -source [get_ports clk_master_ext]  -divide_by 2  [get_pins u_div_m5_1/clk_out_reg/Q]
create_generated_clock -name clk_ext_div4   -source [get_ports clk_master_ext]  -divide_by 4  [get_pins u_div_m5_2/clk_out_reg/Q]
create_generated_clock -name clk_ext_div8   -source [get_ports clk_master_ext]  -divide_by 8  [get_pins u_div_m5_3/clk_out_reg/Q]
create_generated_clock -name clk_ext_div16  -source [get_ports clk_master_ext]  -divide_by 16 [get_pins u_div_m5_4/clk_out_reg/Q]

# ------------------------------------------------------------------------------
# 3. ASYNCHRONOUS CLOCK GROUPS (Isolation of Unrelated Domains for CDC)
# ------------------------------------------------------------------------------
set_clock_groups -asynchronous \
  -group [get_clocks {clk_master_main clk_main_div2 clk_main_div4 clk_main_div8 clk_main_div16 clk_main_div32}] \
  -group [get_clocks {clk_master_mem  clk_mem_div2  clk_mem_div4  clk_mem_div8  clk_mem_div16}] \
  -group [get_clocks {clk_master_peri clk_peri_div2 clk_peri_div4 clk_peri_div8 clk_peri_div16}] \
  -group [get_clocks {clk_master_dsp  clk_dsp_div2  clk_dsp_div4  clk_dsp_div8  clk_dsp_div16}] \
  -group [get_clocks {clk_master_ext  clk_ext_div2  clk_ext_div4  clk_ext_div8  clk_ext_div16}]

# ------------------------------------------------------------------------------
# 4. TIMING DERATING & UNCERTAINTY
# ------------------------------------------------------------------------------
set_clock_uncertainty 0.02 [get_clocks *]
set_input_delay  0.05 -clock clk_master_main [get_ports gpio_in*]
set_output_delay 0.05 -clock clk_master_main [get_ports gpio_out*]