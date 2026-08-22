`timescale 1ns / 1ps

// ============================================================
// MODULE 6: PUF-Pay Top Level
// FINAL PRODUCTION INTEGRATION
//
// Generates 128-bit private key from silicon PUF
// Protected by anti-tamper monitoring
// ============================================================

module puf_pay_top #(
    parameter NUM_ROS        = 256,
    parameter PUF_BITS       = 128,
    parameter BLOCK_SIZE     = 8,
    parameter NUM_BLOCKS     = 16,
    parameter N_STAGES       = 5,
    parameter GATE_DELAY     = 1,
    parameter WINDOW_CYCLES  = 1000,
    parameter COUNTER_WIDTH  = 16,
    parameter CHIP_SEED      = 1  
)(
    input  wire                  clk,
    input  wire                  reset,
    input  wire                  start,
    input  wire                  gen_mode,

    // Anti-tamper sensor inputs
    input  wire [7:0]            voltage_level,
    input  wire [7:0]            temp_level,
    input  wire                  auth_fail,
    input  wire                  auth_success,

    // Key outputs
    output wire [PUF_BITS-1:0]   key_out,       // 128-bit key
    output wire                  key_valid,
    output wire [NUM_BLOCKS-1:0] helper_data,
    output wire [NUM_BLOCKS-1:0] error_flag,

    // Status outputs
    output wire                  puf_done,
    output wire                  tamper_alert,
    output wire                  system_lock,
    output wire [3:0]            fail_count
);

    wire [PUF_BITS-1:0] puf_response;
    wire                puf_core_done;
    wire                zeroize;

    // Block operation if locked
    wire safe_start   = start && !system_lock;

    // Zeroize acts as forced reset for key storage
    wire fuzzy_reset  = reset || zeroize;
    wire core_reset   = reset || zeroize;

    // --------------------------------------------------------
    // MODULE 3: RO PUF Core
    // --------------------------------------------------------
      ro_puf_core #(
        .NUM_ROS       (NUM_ROS),
        .PUF_BITS      (PUF_BITS),
        .N_STAGES      (N_STAGES),
        .GATE_DELAY    (GATE_DELAY),
        .WINDOW_CYCLES (WINDOW_CYCLES),
        .COUNTER_WIDTH (COUNTER_WIDTH),
        .CHIP_SEED     (CHIP_SEED)      // ADD THIS LINE
    ) U_PUF_CORE (
        .clk         (clk),
        .reset       (core_reset),
        .start       (safe_start),
        .puf_response(puf_response),
        .done        (puf_core_done)
    );

    // --------------------------------------------------------
    // MODULE 4: Fuzzy Extractor
    // --------------------------------------------------------
    fuzzy_extractor #(
        .PUF_BITS   (PUF_BITS),
        .BLOCK_SIZE (BLOCK_SIZE),
        .NUM_BLOCKS (NUM_BLOCKS)
    ) U_FUZZY (
        .clk         (clk),
        .reset       (fuzzy_reset),
        .puf_in      (puf_response),
        .puf_valid   (puf_core_done),
        .gen_mode    (gen_mode),
        .key_out     (key_out),
        .key_valid   (key_valid),
        .helper_data (helper_data),
        .error_flag  (error_flag)
    );

    // --------------------------------------------------------
    // MODULE 5: Anti-Tamper Monitor
    // --------------------------------------------------------
    anti_tamper U_TAMPER (
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

    assign puf_done = puf_core_done;

endmodule