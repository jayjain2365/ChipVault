`timescale 1ns / 1ps

// ============================================================
// MODULE 4: Fuzzy Extractor (128-bit FINAL VERSION)
//
// PURPOSE:
//   PUF output has small noise between readings due to
//   temperature/voltage variation. This module ensures
//   the SAME 128-bit private key is reproduced every time,
//   even if a few bits in the PUF response flip.
//
// METHOD:
//   - Split 128-bit PUF into 16 blocks of 8 bits each
//   - ENROLLMENT: Store golden reference block values
//   - REPRODUCTION: Compare noisy block to golden block
//     -> If exactly 1-bit differs, correct it
//     -> If 0-bit differs, already correct
//     -> If 2+ bits differ, correction fails (flagged)
//
// NOTE:
//   This is a simplified single-error-correcting model.
//   Production version would use full BCH(255,131) or similar.
//   This model proves the CONCEPT and ARCHITECTURE correctly.
// ============================================================

module fuzzy_extractor #(
    parameter PUF_BITS    = 128,
    parameter BLOCK_SIZE  = 8,
    parameter NUM_BLOCKS  = 16          // PUF_BITS / BLOCK_SIZE
)(
    input  wire                   clk,
    input  wire                   reset,

    input  wire [PUF_BITS-1:0]    puf_in,
    input  wire                   puf_valid,
    input  wire                   gen_mode,      // 1=enroll, 0=reproduce

    output reg  [PUF_BITS-1:0]    key_out,
    output reg                    key_valid,
    output reg  [NUM_BLOCKS-1:0]  helper_data,   // 1 parity bit/block

    output reg  [NUM_BLOCKS-1:0]  error_flag     // 1 = uncorrectable block
);

    // --------------------------------------------------------
    // Stored golden reference (from enrollment)
    // --------------------------------------------------------
    reg [PUF_BITS-1:0] golden_puf;

    integer i;
    reg [BLOCK_SIZE-1:0] block_in;
    reg [BLOCK_SIZE-1:0] block_gold;
    reg [BLOCK_SIZE-1:0] corrected_block;
    reg [BLOCK_SIZE-1:0] bit_errors;

    // --------------------------------------------------------
    // Main Logic
    // --------------------------------------------------------
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            key_out     <= 0;
            key_valid   <= 0;
            helper_data <= 0;
            error_flag  <= 0;
            golden_puf  <= 0;
        end
        else begin
            key_valid <= 0;

            if (puf_valid) begin

                // ================================================
                // ENROLLMENT MODE (gen_mode = 1)
                // Run ONCE per chip, at manufacturing/setup time
                // ================================================
                if (gen_mode) begin

                    golden_puf <= puf_in;
                    key_out    <= puf_in;
                    error_flag <= 0;

                    for (i = 0; i < NUM_BLOCKS; i = i + 1) begin
                        block_in = puf_in[i*BLOCK_SIZE +: BLOCK_SIZE];
                        // Parity helper bit (even parity)
                        helper_data[i] <= ^block_in;
                    end

                    key_valid <= 1;
                end

                // ================================================
                // REPRODUCTION MODE (gen_mode = 0)
                // Run EVERY payment, regenerating the same key
                // ================================================
                else begin

                    for (i = 0; i < NUM_BLOCKS; i = i + 1) begin

                        block_in   = puf_in[i*BLOCK_SIZE +: BLOCK_SIZE];
                        block_gold = golden_puf[i*BLOCK_SIZE +: BLOCK_SIZE];

                        bit_errors = block_in ^ block_gold;
                        corrected_block = block_in;

                        if (bit_errors != 0) begin
                            // Check if EXACTLY 1 bit differs
                            // (power-of-2 check: x & (x-1) == 0)
                            if ((bit_errors & (bit_errors - 1)) == 0) begin
                                corrected_block = block_gold; // corrected
                                error_flag[i]   <= 0;
                            end
                            else begin
                                // 2+ bit errors -> cannot correct
                                corrected_block = block_in;   // leave as-is
                                error_flag[i]   <= 1;
                            end
                        end
                        else begin
                            error_flag[i] <= 0; // no error
                        end

                        key_out[i*BLOCK_SIZE +: BLOCK_SIZE]
                            <= corrected_block;
                    end

                    key_valid <= 1;
                end
            end
        end
    end

endmodule