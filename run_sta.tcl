read_liberty /tmp/opensta_custom.lib
read_verilog soc_top_benchmark.v
link_design soc_top_benchmark
read_sdc constraints.sdc
report_checks -path_delay max -fields {slew cap input net fanout} -digits 4
report_worst_slack -max
