`timescale 1ns / 1ps

// ============================================================
// TESTBENCH - Module 6: PUF-Pay FULL SYSTEM
// PRODUCTION SCALE - 256 ROs, 128-bit key
// ============================================================

module tb_puf_pay_top;

    parameter NUM_ROS        = 256;
    parameter PUF_BITS       = 128;
    parameter BLOCK_SIZE     = 8;
    parameter NUM_BLOCKS     = 16;
    parameter N_STAGES       = 5;
    parameter GATE_DELAY     = 1;
    parameter WINDOW_CYCLES  = 1000;
    parameter COUNTER_WIDTH  = 16;
    parameter CLK_PERIOD     = 10;

    reg clk;
    reg reset;
    reg start;
    reg gen_mode;
    reg [7:0] voltage_level;
    reg [7:0] temp_level;
    reg auth_fail;
    reg auth_success;

    wire [PUF_BITS-1:0]   key_out;
    wire                  key_valid;
    wire [NUM_BLOCKS-1:0] helper_data;
    wire [NUM_BLOCKS-1:0] error_flag;
    wire                  puf_done;
    wire                  tamper_alert;
    wire                  system_lock;
    wire [3:0]            fail_count;

    reg [PUF_BITS-1:0] enrolled_key;
    integer file;
    // --------------------------------------------------------
    // DUT
    // --------------------------------------------------------
    puf_pay_top #(
        .NUM_ROS       (NUM_ROS),
        .PUF_BITS      (PUF_BITS),
        .BLOCK_SIZE    (BLOCK_SIZE),
        .NUM_BLOCKS    (NUM_BLOCKS),
        .N_STAGES      (N_STAGES),
        .GATE_DELAY    (GATE_DELAY),
        .WINDOW_CYCLES (WINDOW_CYCLES),
        .COUNTER_WIDTH (COUNTER_WIDTH)
    ) DUT (
        .clk           (clk),
        .reset         (reset),
        .start         (start),
        .gen_mode      (gen_mode),
        .voltage_level (voltage_level),
        .temp_level    (temp_level),
        .auth_fail     (auth_fail),
        .auth_success  (auth_success),
        .key_out       (key_out),
        .key_valid     (key_valid),
        .helper_data   (helper_data),
        .error_flag    (error_flag),
        .puf_done      (puf_done),
        .tamper_alert  (tamper_alert),
        .system_lock   (system_lock),
        .fail_count    (fail_count)
    );

    // --------------------------------------------------------
    // Clock - 100 MHz
    // --------------------------------------------------------
    initial clk = 0;
    always #(CLK_PERIOD/2) clk = ~clk;

    // --------------------------------------------------------
    // Main Test
    // --------------------------------------------------------
    initial begin

        $display("==============================================");
        $display("  PUF-Pay FULL SYSTEM TEST");
        $display("  256 ROs -> 128-bit Private Key");
        $display("==============================================");

        reset         = 1;
        start         = 0;
        gen_mode      = 0;
        voltage_level = 8'h80;
        temp_level    = 8'h50;
        auth_fail     = 0;
        auth_success  = 0;

        repeat(5) @(posedge clk);
        reset = 0;
        repeat(5) @(posedge clk);

        // ============================================
        // TEST 1: ENROLLMENT
        // ============================================
        $display("\n[TEST 1] ENROLLMENT PHASE");
        $display("Please wait - 256 ROs measuring 1000 cycles...");

        gen_mode = 1;
        start    = 1;
        repeat(3) @(posedge clk);
        start = 0;

        wait(key_valid == 1'b1);
        @(posedge clk);

        enrolled_key = key_out;
        $display("\n[TEST 1] ENROLLMENT COMPLETE ✅");
        $display("128-bit Private Key = %h", enrolled_key);
        file = $fopen("C:/Users/jayja/OneDrive/Desktop/PUF/PUF - HACKATHON/shared/puf_key.txt", "w");
        $fwrite(file, "%h", enrolled_key);
        $fclose(file);
        $display("PUF key written to shared/puf_key.txt");
        $fwrite(file, "%h\n", enrolled_key);
        $fclose(file);
        $display("PUF key written to shared/puf_key.txt");
        $display("Helper Data (16 bits) = %b", helper_data);

        repeat(20) @(posedge clk);

        // ============================================
        // TEST 2: PAYMENT - REGENERATE SAME KEY
        // ============================================
        $display("\n[TEST 2] PAYMENT PHASE - Regenerating key");

        reset = 1;
        repeat(5) @(posedge clk);
        reset = 0;
        repeat(5) @(posedge clk);

        gen_mode = 0;
        start    = 1;
        repeat(3) @(posedge clk);
        start = 0;

        wait(key_valid == 1'b1);
        @(posedge clk);

        $display("Regenerated Key = %h", key_out);
        $display("Original Key    = %h", enrolled_key);

        if (key_out == enrolled_key)
            $display("[TEST 2] PASS ✅ Same 128-bit key regenerated");
        else
            $display("[TEST 2] FAIL ❌ Key mismatch");

        repeat(20) @(posedge clk);

        // ============================================
        // TEST 3: TAMPER ATTACK
        // ============================================
        $display("\n[TEST 3] Voltage glitch attack simulation");

        voltage_level = 8'hFF;
        repeat(3) @(posedge clk);

        if (tamper_alert && system_lock)
            $display("[TEST 3] PASS ✅ Attack detected + locked");
        else
            $display("[TEST 3] FAIL ❌");

        voltage_level = 8'h80;
        repeat(5) @(posedge clk);

        // Try to operate while locked
        $display("\n[TEST 3b] Attempting operation while LOCKED");
        gen_mode = 0;
        start    = 1;
        repeat(10) @(posedge clk);
        start = 0;
        repeat(20) @(posedge clk);

        if (system_lock)
            $display("[TEST 3b] PASS ✅ Locked state maintained");
        else
            $display("[TEST 3b] FAIL ❌ Lock released");

        $display("\n==============================================");
        $display("  PUF-Pay FULL SYSTEM TEST COMPLETE");
        $display("==============================================");

        $finish;
    end

    // --------------------------------------------------------
    // Monitor
    // --------------------------------------------------------
    always @(posedge key_valid) begin
        $display("[MONITOR] KEY VALID at t=%0t | key=%h", $time, key_out);
    end

    always @(posedge tamper_alert) begin
        $display("[MONITOR] 🚨 TAMPER at t=%0t", $time);
    end

endmodule