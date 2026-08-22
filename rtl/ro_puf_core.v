`timescale 1ns / 1ps

// ============================================================
// MODULE 3: RO PUF Core (PRODUCTION SCALE + CHIP_SEED ENTROPY)
// 256 Ring Oscillators -> 128-bit Unique Per-Chip PUF Response
//
// CHIP_SEED simulates a DIFFERENT physical chip.
// Different CHIP_SEED = different silicon = different key.
// ============================================================

module ro_puf_core #(
    parameter NUM_ROS        = 256,
    parameter PUF_BITS       = 128,
    parameter N_STAGES       = 5,
    parameter GATE_DELAY     = 1,
    parameter WINDOW_CYCLES  = 1000,
    parameter COUNTER_WIDTH  = 16,
    parameter CHIP_SEED      = 1      // Unique per physical chip
)(
    input  wire clk,
    input  wire reset,
    input  wire start,

    output reg  [PUF_BITS-1:0] puf_response,
    output reg  done
);

    wire [NUM_ROS-1:0]        ro_out;
    wire [NUM_ROS-1:0]        fc_done;
    wire [COUNTER_WIDTH-1:0]  fc_count [0:NUM_ROS-1];

    reg  [NUM_ROS-1:0]        ro_enable;
    reg                       all_done;
    integer                   k;

    // --------------------------------------------------------
    // Instantiate 256 Ring Oscillators
    // CHIP_SEED mixed into hash -> different chip = different
    // delay pattern = different frequencies = different key
    // --------------------------------------------------------
    genvar i;
    generate
        for (i = 0; i < NUM_ROS; i = i + 1) begin : ro_array

            localparam integer RAW_HASH  =
                ((i * 2654435761) ^ (i << 3) ^ (i >> 2) ^ (i * 17)
                 ^ (CHIP_SEED * 40503) ^ (CHIP_SEED << 5));
            localparam integer PSEUDO    = (RAW_HASH & 32'h7FFFFFFF) % 7;
            localparam integer RO_DELAY  = GATE_DELAY + PSEUDO;

            ring_oscillator #(
                .N_STAGES  (N_STAGES),
                .GATE_DELAY(RO_DELAY)
            ) RO_INST (
                .enable(ro_enable[i]),
                .out   (ro_out[i])
            );
        end
    endgenerate

    // --------------------------------------------------------
    // 256 Frequency Counters
    // --------------------------------------------------------
    genvar j;
    generate
        for (j = 0; j < NUM_ROS; j = j + 1) begin : fc_array
            frequency_counter #(
                .WINDOW_CYCLES (WINDOW_CYCLES),
                .COUNTER_WIDTH (COUNTER_WIDTH)
            ) FC_INST (
                .clk        (clk),
                .reset      (reset),
                .ro_signal  (ro_out[j]),
                .start      (start),
                .done       (fc_done[j]),
                .count_value(fc_count[j])
            );
        end
    endgenerate

    // --------------------------------------------------------
    // Wait for all counters to finish
    // --------------------------------------------------------
    always @(posedge clk or posedge reset) begin
        if (reset)
            all_done <= 0;
        else
            all_done <= (fc_done == {NUM_ROS{1'b1}});
    end

    // --------------------------------------------------------
    // Enable + Pairwise Comparison -> 128-bit PUF Response
    // --------------------------------------------------------
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            puf_response <= 0;
            done         <= 0;
            ro_enable    <= 0;
        end
        else begin

            if (start)
                ro_enable <= {NUM_ROS{1'b1}};

            if (all_done && !done) begin
                for (k = 0; k < PUF_BITS; k = k + 1) begin
                    if (fc_count[2*k] > fc_count[2*k+1])
                        puf_response[k] <= 1'b1;
                    else
                        puf_response[k] <= 1'b0;
                end
                done      <= 1;
                ro_enable <= 0;
            end
        end
    end

endmodule