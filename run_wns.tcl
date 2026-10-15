# ==============================================================================
# OpenSTA Script: Check WNS & Failing Path Summary
# ==============================================================================
read_liberty /tmp/opensta_custom.lib
read_verilog soc_top_benchmark.v
link_design soc_top_benchmark
read_sdc constraints.sdc

# Report overall Worst Negative Slack and Total Negative Slack
puts "\n----------------------------------------------------------------------"
puts "                       STA WNS REPORT SUMMARY                        "
puts "----------------------------------------------------------------------"
report_worst_slack -max
report_worst_slack -min

# Detailed check of the top 1 setup failing path
puts "\n----------------------------------------------------------------------"
puts "                      CRITICAL PATH DETAIL (MAX)                      "
puts "----------------------------------------------------------------------"
report_checks -path_delay max -fields {slew cap input net fanout} -digits 4 -group_count 1