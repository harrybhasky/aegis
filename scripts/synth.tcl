read_verilog $::env(RTL_FILE)
synth -top top
dfflibmap -liberty pdk/my_cells.lib
abc -liberty pdk/my_cells.lib
clean
write_verilog -noattr output/netlist.v
