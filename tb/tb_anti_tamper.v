`timescale 1ns / 1ps

// ============================================================
// TESTBENCH - Module 5: Anti-Tamper Monitor
//
// TESTS:
//   TEST 1: Normal operation - no tamper, no lock
//   TEST 2: Voltage glitch attack -> lock + zeroize
//   TEST 3: Lock persists even after voltage returns to normal
//   TEST 4: Reset clears the lock
//   TEST 5: Temperature attack -> lock + zeroize
//   TEST 6: Repeated auth failures -> lock + zeroize
//   TEST 7: auth_success resets failure counter
// ============================================================

module tb_anti_tamper;

    reg clk;
    reg reset;
    reg [7:0] voltage_level;
    reg [7:0] temp_level;
    reg auth_fail;
    reg auth_success;

    wire tamper_alert;
    wire zeroize;
    wire system_lock;
    wire [3:0] fail_count;

    // --------------------------------------------------------
    // DUT
    // --------------------------------------------------------
    anti_tamper #(
        .VOLTAGE_MAX  (8'hF0),
        .VOLTAGE_MIN  (8'h10),
        .TEMP_MAX     (8'hE0),
        .TEMP_MIN     (8'h05),
        .MAX_FAILURES (4'd3)
    ) DUT (
        .clk           (clk),
        .reset         (reset),
        .voltage_level (voltage_level),
        .temp_level    (temp_level),
        .auth_fail     (auth_fail),
        .auth_success  (auth_success),
        .tamper_alert  (tamper_alert),
        .zeroize       (zeroize),
        .system_lock   (system_lock),
        .fail_count    (fail_count)
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
        $display("  Module 5: Anti-Tamper Monitor Test");
        $display("=========================================");

        // Init
        reset         = 1;
        voltage_level = 8'h80;   // normal
        temp_level    = 8'h50;   // normal
        auth_fail     = 0;
        auth_success  = 0;
        #20;
        reset = 0;
        #20;

        // ======================================================
        // TEST 1: Normal Operation
        // ======================================================
        $display("\n[TEST 1] Normal operating conditions");
        voltage_level = 8'h80;
        temp_level    = 8'h50;
        #20;

        if (tamper_alert == 0 && system_lock == 0)
            $display("[TEST 1] PASS ✅ No false alarm");
        else
            $display("[TEST 1] FAIL ❌ Unexpected alarm");

        // ======================================================
        // TEST 2: Voltage Glitch Attack
        // ======================================================
        $display("\n[TEST 2] Voltage glitch attack (voltage = 0xFF)");
        voltage_level = 8'hFF;   // above VOLTAGE_MAX
        #10;

        if (tamper_alert == 1 && zeroize == 1 && system_lock == 1)
            $display("[TEST 2] PASS ✅ Tamper detected, key zeroized, locked");
        else
            $display("[TEST 2] FAIL ❌ Tamper not detected properly");

        #20;

        // ======================================================
        // TEST 3: Lock Persists Even After Voltage Normalizes
        // ======================================================
        $display("\n[TEST 3] Voltage back to normal - lock should PERSIST");
        voltage_level = 8'h80;   // attacker releases glitch
        #30;

        if (system_lock == 1)
            $display("[TEST 3] PASS ✅ System remains locked (sticky)");
        else
            $display("[TEST 3] FAIL ❌ Lock incorrectly cleared");

        // ======================================================
        // TEST 4: Reset Clears the Lock
        // ======================================================
        $display("\n[TEST 4] Applying full reset");
        reset = 1;
        #20;
        reset = 0;
        #20;

        if (system_lock == 0 && tamper_alert == 0)
            $display("[TEST 4] PASS ✅ Reset cleared lock");
        else
            $display("[TEST 4] FAIL ❌ Lock did not clear");

        // ======================================================
        // TEST 5: Temperature Attack
        // ======================================================
        $display("\n[TEST 5] Temperature attack (temp = 0xFF)");
        voltage_level = 8'h80;
        temp_level    = 8'hFF;   // above TEMP_MAX
        #10;

        if (tamper_alert == 1 && system_lock == 1)
            $display("[TEST 5] PASS ✅ Temp attack detected and locked");
        else
            $display("[TEST 5] FAIL ❌ Temp attack missed");

        // Reset for next test
        reset = 1;
        #20;
        reset = 0;
        temp_level = 8'h50;
        #20;

        // ======================================================
        // TEST 6: Repeated Auth Failures (Brute Force)
        // ======================================================
        $display("\n[TEST 6] Simulating 3 wrong PIN/signature attempts");

        auth_fail = 1;
        @(posedge clk); #1;
        auth_fail = 0;
        #10;
        $display("  After 1 failure -> fail_count=%0d, lock=%b", fail_count, system_lock);

        auth_fail = 1;
        @(posedge clk); #1;
        auth_fail = 0;
        #10;
        $display("  After 2 failures -> fail_count=%0d, lock=%b", fail_count, system_lock);

        auth_fail = 1;
        @(posedge clk); #1;
        auth_fail = 0;
        #10;
        $display("  After 3 failures -> fail_count=%0d, lock=%b", fail_count, system_lock);

        if (system_lock == 1)
            $display("[TEST 6] PASS ✅ Brute force lockout triggered");
        else
            $display("[TEST 6] FAIL ❌ Lockout did not trigger");

        // Reset for next test
        reset = 1;
        #20;
        reset = 0;
        #20;

        // ======================================================
        // TEST 7: auth_success Resets Failure Counter
        // ======================================================
        $display("\n[TEST 7] auth_success should reset fail_count");

        auth_fail = 1;
        @(posedge clk); #1;
        auth_fail = 0;
        #10;
        $display("  After 1 failure -> fail_count=%0d", fail_count);

        auth_success = 1;
        @(posedge clk); #1;
        auth_success = 0;
        #10;
        $display("  After success   -> fail_count=%0d", fail_count);

        if (fail_count == 0)
            $display("[TEST 7] PASS ✅ Successful auth reset counter");
        else
            $display("[TEST 7] FAIL ❌ Counter not reset");

        #30;

        $display("\n=========================================");
        $display("  Module 5 Simulation Complete");
        $display("=========================================");

        $finish;
    end

    // --------------------------------------------------------
    // Monitor
    // --------------------------------------------------------
    always @(posedge zeroize) begin
        $display("[MONITOR] 🔴 ZEROIZE pulse at time=%0t - KEY ERASED", $time);
    end

    always @(posedge tamper_alert) begin
        $display("[MONITOR] 🚨 TAMPER ALERT at time=%0t", $time);
    end

endmodule