# One-shot recipe to produce blk_mem_kilobyte.xci for whatever Vivado
# the host is running. Invoked by VivadoIp's builder_tcl hook when the
# .xci is absent or this script is newer than it.
#
# Configures a 1024x8 true dual-port RAM. set_part is overridden
# in-memory by VivadoIp's own TCL on the actual generation pass;
# the part set here only governs create_ip device family resolution.

create_project -in_memory -force -part xczu7eg-ffvc1156-2-e
file mkdir ip
create_ip -name blk_mem_gen -vendor xilinx.com -library ip \
    -module_name blk_mem_kilobyte -dir [pwd]/ip
set_property -dict {
    CONFIG.Memory_Type {True_Dual_Port_RAM}
    CONFIG.Write_Width_A {8}
    CONFIG.Write_Depth_A {1024}
} [get_ips blk_mem_kilobyte]
generate_target simulation [get_files blk_mem_kilobyte.xci]
close_project
exit
