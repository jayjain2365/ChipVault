`timescale 1ns / 1ps

// ============================================================
// TESTBENCH - Module 4: Fuzzy Extractor (128-bit)
//
// TESTS:
//   TEST 1: Enrollment - generate golden key
//   TEST 2: Reproduction with 0 errors -> key must match
//   TEST 3: Reproduction with 1-bit error per block -> corrected
//   TEST 4: Reproduction with 2-bit error in one block -> flagged
// ============================================================

module tb_fuzzy_extractor;

    parameter PUF_BITS   = 128;
    parameter BLOCK_SIZE = 8;
    parameter NUM_BLOCKS = 16;

    reg clk;
    reg reset;
    reg [PUF_BITS-1:0] puf_in;
    reg puf_valid;
    reg gen_mode;

    wire [PUF_BITS-1:0]   key_out;
    wire                  key_valid;
    wire [NUM_BLOCKS-1:0] helper_data;
    wire [NUM_BLOCKS-1:0] error_flag;

    reg [PUF_BITS-1:0] enrolled_key;
    reg [PUF_BITS-1:0] original_puf;

    // --------------------------------------------------------
    // DUT
    // --------------------------------------------------------
    fuzzy_extractor #(
        .PUF_BITS   (PUF_BITS),
        .BLOCK_SIZE (BLOCK_SIZE),
        .NUM_BLOCKS (NUM_BLOCKS)
    ) DUT (
        .clk        (clk),
        .reset      (reset),
        .puf_in     (puf_in),
        .puf_valid  (puf_valid),
        .gen_mode   (gen_mode),
        .key_out    (key_out),
        .key_valid  (key_valid),
        .helper_data(helper_data),
        .error_flag (error_flag)
    );

    // --------------------------------------------------------
    // Clock - 100 MHz
    // --------------------------------------------------------
    initial clk = 0;
    always #5 clk = ~clk;

    // --------------------------------------------------------
    // Main Test Sequence
    // --------------------------------------------------------
    initial begin

        $display("=========================================");
        $display("  Module 4: Fuzzy Extractor Test (128-bit)");
        $display("=========================================");

        reset     = 1;
        puf_valid = 0;
        gen_mode  = 0;
        puf_in    = 0;
        #20;
        reset = 0;
        #10;

        // Example 128-bit "silicon" PUF value
        original_puf = 128'hA5B3C7D9E1F2A4B6C8D0E3F5A7B9C1D3;

        // ======================================================
        // TEST 1: ENROLLMENT
        // ======================================================
        $display("\n[TEST 1] ENROLLMENT PHASE");
        gen_mode  = 1;
        puf_in    = original_puf;
        puf_valid = 1;
        #10;
        puf_valid = 0;
        #20;

        enrolled_key = key_out;

        $display("Enrolled Key = %h", enrolled_key);
        $display("Helper Data  = %b", helper_data);

        if (enrolled_key == original_puf)
            $display("[TEST 1] PASS ✅ Enrollment stored correctly");
        else
            $display("[TEST 1] FAIL ❌");

        #20;

        // ======================================================
        // TEST 2: REPRODUCTION - NO NOISE
        // ======================================================
        $display("\n[TEST 2] REPRODUCTION - NO ERROR");
        gen_mode  = 0;
        puf_in    = original_puf;   // identical reading
        puf_valid = 1;
        #10;
        puf_valid = 0;
        #20;

        $display("Recovered Key = %h", key_out);
        $display("Error Flags   = %b", error_flag);

        if (key_out == enrolled_key)
            $display("[TEST 2] PASS ✅ Key matches with no noise");
        else
            $display("[TEST 2] FAIL ❌");

        #20;

        // ======================================================
        // TEST 3: REPRODUCTION - 1 BIT ERROR PER BLOCK
        // Flip bit 0 of every 8-bit block (16 total single-bit errors)
        // ======================================================
        $display("\n[TEST 3] REPRODUCTION - 1-BIT ERROR PER BLOCK");
        gen_mode  = 0;
        puf_in    = original_puf ^ 128'h01010101010101010101010101010101;
        puf_valid = 1;
        #10;
        puf_valid = 0;
        #20;

        $display("Noisy Input   = %h", original_puf ^ 128'h01010101010101010101010101010101);
        $display("Recovered Key = %h", key_out);
        $display("Error Flags   = %b (should be all 0 = corrected)", error_flag);

        if (key_out == enrolled_key)
            $display("[TEST 3] PASS ✅ All 1-bit errors corrected");
        else
            $display("[TEST 3] FAIL ❌ Correction failed");

        #20;

        // ======================================================
        // TEST 4: REPRODUCTION - 2 BIT ERROR IN ONE BLOCK
        // Flip 2 bits within the SAME block -> uncorrectable
        // ======================================================
        $display("\n[TEST 4] REPRODUCTION - 2-BIT ERROR IN ONE BLOCK");
        gen_mode  = 0;
        // Flip bit0 and bit1 of the lowest byte (block 0)
        puf_in    = original_puf ^ 128'h00000000000000000000000000000003;
        puf_valid = 1;
        #10;
        puf_valid = 0;
        #20;

        $display("Recovered Key = %h", key_out);
        $display("Error Flags   = %b (bit0 should be 1 = uncorrectable)", error_flag);

        if (error_flag[0] == 1'b1)
            $display("[TEST 4] PASS ✅ Uncorrectable error correctly flagged");
        else
            $display("[TEST 4] FAIL ❌ Error not flagged");

        #20;

        $display("\n=========================================");
        $display("  Module 4 Simulation Complete");
        $display("=========================================");

        $finish;
    end

endmodule