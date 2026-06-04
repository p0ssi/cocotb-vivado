# One-shot recipe to produce a minimal Block Design (bd_simple.bd) with
# plain-signal top-level ports. Tests whether VivadoIp can ingest a .bd
# directly and whether the BD's top-level signals are reachable from
# cocotb without an explicit RTL wrapper.
#
# The design is a single 8-bit NOT gate: data_in[7:0] -> data_out[7:0].
# No interface ports, no clocks, no resets — keeps the surface minimal
# and isolates the question about .bd dispatch.

create_project -in_memory -force -part xczu7eg-ffvc1156-2-e

file mkdir ip
create_bd_design -dir [pwd]/ip bd_simple
current_bd_design bd_simple

create_bd_port -dir I -from 7 -to 0 data_in
create_bd_port -dir O -from 7 -to 0 data_out

create_bd_cell -type ip -vlnv xilinx.com:ip:util_vector_logic:2.0 inverter
set_property -dict {
    CONFIG.C_OPERATION {not}
    CONFIG.C_SIZE {8}
} [get_bd_cells inverter]

connect_bd_net [get_bd_ports data_in]  [get_bd_pins inverter/Op1]
connect_bd_net [get_bd_ports data_out] [get_bd_pins inverter/Res]

validate_bd_design
save_bd_design

generate_target simulation [get_files [pwd]/ip/bd_simple/bd_simple.bd]
close_project
exit
