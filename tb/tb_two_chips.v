`timescale 1ns / 1ps

// ============================================================
// TESTBENCH: Two-Chip Comparison
// Simulates a REAL chip (CHIP_SEED=1) and an ATTACKER's
// cloned/different chip (CHIP_SEED=77).
// Both run the SAME RTL, but different silicon -> different keys.
// ============================================================

module tb_two_chips;

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

    // ------------------- CHIP A (Real / Legitimate) -------------------
    wire [PUF_BITS-1:0]   keyA_out;
    wire                  keyA_valid;
    wire [NUM_BLOCKS-1:0] helperA_data;
    wire [NUM_BLOCKS-1:0] errorA_flag;
    wire                  pufA_done, tamperA_alert, lockA;
    wire [3:0]            failA_count;

    puf_pay_top #(
        .NUM_ROS(NUM_ROS), .PUF_BITS(PUF_BITS), .BLOCK_SIZE(BLOCK_SIZE),
        .NUM_BLOCKS(NUM_BLOCKS), .N_STAGES(N_STAGES), .GATE_DELAY(GATE_DELAY),
        .WINDOW_CYCLES(WINDOW_CYCLES), .COUNTER_WIDTH(COUNTER_WIDTH),
        .CHIP_SEED(1)                              // <-- REAL CHIP
    ) CHIP_A (
        .clk(clk), .reset(reset), .start(start), .gen_mode(gen_mode),
        .voltage_level(voltage_level), .temp_level(temp_level),
        .auth_fail(auth_fail), .auth_success(auth_success),
        .key_out(keyA_out), .key_valid(keyA_valid),
        .helper_data(helperA_data), .error_flag(errorA_flag),
        .puf_done(pufA_done), .tamper_alert(tamperA_alert),
        .system_lock(lockA), .fail_count(failA_count)
    );

    // ------------------- CHIP B (Attacker / Cloned) --------------------
    wire [PUF_BITS-1:0]   keyB_out;
    wire                  keyB_valid;
    wire [NUM_BLOCKS-1:0] helperB_data;
    wire [NUM_BLOCKS-1:0] errorB_flag;
    wire                  pufB_done, tamperB_alert, lockB;
    wire [3:0]            failB_count;

    puf_pay_top #(
        .NUM_ROS(NUM_ROS), .PUF_BITS(PUF_BITS), .BLOCK_SIZE(BLOCK_SIZE),
        .NUM_BLOCKS(NUM_BLOCKS), .N_STAGES(N_STAGES), .GATE_DELAY(GATE_DELAY),
        .WINDOW_CYCLES(WINDOW_CYCLES), .COUNTER_WIDTH(COUNTER_WIDTH),
        .CHIP_SEED(77)                             // <-- ATTACKER CHIP
    ) CHIP_B (
        .clk(clk), .reset(reset), .start(start), .gen_mode(gen_mode),
        .voltage_level(voltage_level), .temp_level(temp_level),
        .auth_fail(auth_fail), .auth_success(auth_success),
        .key_out(keyB_out), .key_valid(keyB_valid),
        .helper_data(helperB_data), .error_flag(errorB_flag),
        .puf_done(pufB_done), .tamper_alert(tamperB_alert),
        .system_lock(lockB), .fail_count(failB_count)
    );

    // --------------------------------------------------------
    // Clock
    // --------------------------------------------------------
    initial clk = 0;
    always #(CLK_PERIOD/2) clk = ~clk;

    // --------------------------------------------------------
    // File handles (declared at top - Verilog rule)
    // --------------------------------------------------------
    integer fileA, fileB;

    // --------------------------------------------------------
    // Main Sequence
    // --------------------------------------------------------
    initial begin

        $display("==============================================");
        $display("  TWO-CHIP PUF TEST");
        $display("  Chip A = Legitimate | Chip B = Attacker Clone");
        $display("==============================================");

        reset = 1; start = 0; gen_mode = 1;
        voltage_level = 8'h80; temp_level = 8'h50;
        auth_fail = 0; auth_success = 0;

        repeat(5) @(posedge clk);
        reset = 0;
        repeat(5) @(posedge clk);

        $display("\n[ENROLLMENT] Both chips generating keys in parallel...");
        $display("Please wait - 256 ROs x 2 chips measuring 1000 cycles...");

        start = 1;
        repeat(3) @(posedge clk);
        start = 0;

        // Wait for BOTH chips to finish
        wait(keyA_valid == 1'b1 && keyB_valid == 1'b1);
        @(posedge clk);

        $display("\n[RESULT] Chip A key = %h", keyA_out);
        $display("[RESULT] Chip B key = %h", keyB_out);

        if (keyA_out != keyB_out)
            $display("[CHECK] PASS ✅ Different chips produced DIFFERENT keys");
        else
            $display("[CHECK] FAIL ❌ Keys matched (unexpected)");

        // Write Chip A key to file
        fileA = $fopen("C:/Users/jayja/OneDrive/Desktop/PUF/PUF - HACKATHON/shared/puf_key_chipA.txt", "w");
        $fwrite(fileA, "%h", keyA_out);
        $fclose(fileA);
        $display("Chip A key written to shared/puf_key_chipA.txt");

        // Write Chip B key to file
        fileB = $fopen("C:/Users/jayja/OneDrive/Desktop/PUF/PUF - HACKATHON/shared/puf_key_chipB.txt", "w");
        $fwrite(fileB, "%h", keyB_out);
        $fclose(fileB);
        $display("Chip B key written to shared/puf_key_chipB.txt");

        repeat(10) @(posedge clk);

        $display("\n==============================================");
        $display("  TWO-CHIP TEST COMPLETE");
        $display("==============================================");

        $finish;
    end

endmodule