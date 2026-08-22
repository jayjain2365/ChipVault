`timescale 1ns / 1ps

module tb_frequency_counter;

    // --------------------------------------------------------
    // Parameters
    // --------------------------------------------------------
    parameter WINDOW_CYCLES  = 100;
    parameter COUNTER_WIDTH  = 16;
    parameter CLK_PERIOD     = 10;
    parameter RO_PERIOD      = 6;

    // --------------------------------------------------------
    // Signals
    // --------------------------------------------------------
    reg  clk;
    reg  reset;
    reg  ro_signal;
    reg  start;

    wire done;
    wire [COUNTER_WIDTH-1:0] count_value;

    // --------------------------------------------------------
    // Instantiate DUT
    // --------------------------------------------------------
    frequency_counter #(
        .WINDOW_CYCLES (WINDOW_CYCLES),
        .COUNTER_WIDTH (COUNTER_WIDTH)
    ) DUT (
        .clk        (clk),
        .reset      (reset),
        .ro_signal  (ro_signal),
        .start      (start),
        .done       (done),
        .count_value(count_value)
    );

    // --------------------------------------------------------
    // Reference Clock - 100 MHz
    // --------------------------------------------------------
    initial clk = 0;
    always #(CLK_PERIOD/2) clk = ~clk;

    // --------------------------------------------------------
    // Fake RO Signal - fixed period
    // --------------------------------------------------------
    initial ro_signal = 0;
    always #(RO_PERIOD/2) ro_signal = ~ro_signal;

    // --------------------------------------------------------
    // Main Test
    // --------------------------------------------------------
    initial begin

        $dumpfile("fc_sim.vcd");
        $dumpvars(0, tb_frequency_counter);

        $display("=====================================");
        $display(" Module 2: Frequency Counter Test");
        $display("=====================================");

        // ------------------------------------------------
        // Reset
        // ------------------------------------------------
        reset = 1;
        start = 0;
        repeat(5) @(posedge clk);
        reset = 0;
        repeat(3) @(posedge clk);

        // ------------------------------------------------
        // TEST 1: Normal Measurement
        // ------------------------------------------------
        $display("\n[TEST 1] Starting measurement...");

        // Hold start for 3 clock cycles
        // Guarantees clk sees it
        repeat(3) @(posedge clk);
        start = 1;
        repeat(3) @(posedge clk);
        start = 0;

        // Wait for done
        wait(done == 1'b1);
        @(posedge clk);

        $display("[TEST 1] Done asserted!");
        $display("[TEST 1] count_value  = %0d", count_value);
        $display("[TEST 1] Expected     ≈ %0d",
                 (WINDOW_CYCLES * CLK_PERIOD) / RO_PERIOD);

        if (count_value > 10 && count_value < 200)
            $display("[TEST 1] PASS ✅");
        else
            $display("[TEST 1] FAIL ❌");

        repeat(5) @(posedge clk);

        // ------------------------------------------------
        // TEST 2: Reset then measure again
        // ------------------------------------------------
        $display("\n[TEST 2] Reset and measure again...");
        reset = 1;
        repeat(5) @(posedge clk);
        reset = 0;
        repeat(3) @(posedge clk);

        start = 1;
        repeat(3) @(posedge clk);
        start = 0;

        wait(done == 1'b1);
        @(posedge clk);

        $display("[TEST 2] count_value  = %0d", count_value);

        if (count_value > 10 && count_value < 200)
            $display("[TEST 2] PASS ✅");
        else
            $display("[TEST 2] FAIL ❌");

        repeat(5) @(posedge clk);

        // ------------------------------------------------
        // TEST 3: done clears on reset
        // ------------------------------------------------
        $display("\n[TEST 3] Checking reset clears done...");
        reset = 1;
        repeat(3) @(posedge clk);

        if (done == 0)
            $display("[TEST 3] PASS ✅ done=0 after reset");
        else
            $display("[TEST 3] FAIL ❌ done still high");

        reset = 0;

        repeat(5) @(posedge clk);

        $display("\n=====================================");
        $display(" Module 2 Simulation Complete");
        $display("=====================================");

        $finish;
    end

    // --------------------------------------------------------
    // Monitor
    // --------------------------------------------------------
    always @(posedge done) begin
        $display("[MONITOR] done at time=%0t | count=%0d",
                 $time, count_value);
    end

endmodule