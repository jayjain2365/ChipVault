`timescale 1ns / 1ps

// ============================================================
// TESTBENCH - Module 3: RO PUF Core
//
// PURPOSE:
//   1. Start PUF measurement
//   2. Wait for done
//   3. Display 4-bit PUF response
//   4. Repeat test for consistency
// ============================================================

module tb_ro_puf_core;

    // --------------------------------------------------------
    // Reduced Parameters for Fast Simulation
    // --------------------------------------------------------
    parameter NUM_ROS       = 8;
    parameter PUF_BITS      = 4;
    parameter N_STAGES      = 5;
    parameter GATE_DELAY    = 1;
    parameter WINDOW_CYCLES = 200;  // Small for sim
    parameter COUNTER_WIDTH = 16;

    parameter CLK_PERIOD    = 10;   // 100 MHz

    // --------------------------------------------------------
    // Signals
    // --------------------------------------------------------
    reg clk;
    reg reset;
    reg start;

    wire [PUF_BITS-1:0] puf_response;
    reg [PUF_BITS-1:0] first_response;
    wire done;
        reg [PUF_BITS-1:0] first_response;
    // --------------------------------------------------------
    // Instantiate DUT
    // --------------------------------------------------------
    ro_puf_core #(
        .NUM_ROS       (NUM_ROS),
        .PUF_BITS      (PUF_BITS),
        .N_STAGES      (N_STAGES),
        .GATE_DELAY    (GATE_DELAY),
        .WINDOW_CYCLES (WINDOW_CYCLES),
        .COUNTER_WIDTH (COUNTER_WIDTH)
    ) DUT (
        .clk         (clk),
        .reset       (reset),
        .start       (start),
        .puf_response(puf_response),
        .done        (done)
    );

    // --------------------------------------------------------
    // Clock Generation
    // --------------------------------------------------------
    initial clk = 0;
    always #(CLK_PERIOD/2) clk = ~clk;

    // --------------------------------------------------------
    // Test Sequence
    // --------------------------------------------------------
    initial begin

        $dumpfile("puf_core_sim.vcd");
        $dumpvars(0, tb_ro_puf_core);

        $display("======================================");
        $display("   Module 3: RO PUF Core Test");
        $display("======================================");

        // --------------------------------------------
        // Reset
        // --------------------------------------------
        reset = 1;
        start = 0;
        repeat(5) @(posedge clk);
        reset = 0;
        repeat(5) @(posedge clk);

        // --------------------------------------------
        // TEST 1 - First Measurement
        // --------------------------------------------
        $display("\n[TEST 1] Starting PUF measurement...");

        start = 1;
        repeat(3) @(posedge clk);
        start = 0;

        wait(done == 1'b1);
        @(posedge clk);

        $display("[TEST 1] DONE!");
        $display("[TEST 1] PUF Response = %b", puf_response);

        // Store first response
        first_response = puf_response;

        repeat(10) @(posedge clk);

        // --------------------------------------------
        // TEST 2 - Repeat Measurement
        // --------------------------------------------
        $display("\n[TEST 2] Repeat measurement for consistency...");

        reset = 1;
        repeat(5) @(posedge clk);
        reset = 0;
        repeat(5) @(posedge clk);

        start = 1;
        repeat(3) @(posedge clk);
        start = 0;

        wait(done == 1'b1);
        @(posedge clk);

        $display("[TEST 2] PUF Response = %b", puf_response);

        if (puf_response == first_response)
            $display("[TEST 2] PASS ✅ Same PUF ID (stable)");
        else
            $display("[TEST 2] FAIL ❌ PUF ID changed");

        repeat(10) @(posedge clk);

        $display("\n======================================");
        $display("   Module 3 Simulation Complete");
        $display("======================================");

        $finish;
    end

    // --------------------------------------------------------
    // Monitor
    // --------------------------------------------------------
    always @(posedge done) begin
        $display("[MONITOR] Done at time=%0t | PUF=%b",
                 $time, puf_response);
    end

endmodule