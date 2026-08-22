`timescale 1ns / 1ps

// ============================================================
// MODULE 5: Anti-Tamper Monitor
//
// PURPOSE:
//   Continuously monitors chip health for attack attempts.
//   If ANY tamper condition is detected:
//     1. Raise tamper_alert
//     2. Zeroize (erase) the private key immediately
//     3. Lock the system permanently until hardware reset
//
// MONITORS:
//   1. Voltage glitch attack   (voltage_level too high/low)
//   2. Temperature attack      (temp_level too high/low)
//   3. Repeated auth failures  (brute force attempts)
//
// SECURITY PRINCIPLE:
//   Once tampered, system_lock stays HIGH forever,
//   even if the attack condition goes away.
//   Only a full external reset can clear it.
// ============================================================

module anti_tamper #(
    parameter VOLTAGE_MAX   = 8'hF0,  // Upper safe voltage
    parameter VOLTAGE_MIN   = 8'h10,  // Lower safe voltage
    parameter TEMP_MAX      = 8'hE0,  // Upper safe temperature
    parameter TEMP_MIN      = 8'h05,  // Lower safe temperature
    parameter MAX_FAILURES  = 4'd3    // Max allowed auth failures
)(
    input  wire       clk,
    input  wire       reset,          // Full hardware reset (clears lock)

    // Sensor inputs
    input  wire [7:0] voltage_level,
    input  wire [7:0] temp_level,

    // Authentication feedback
    input  wire       auth_fail,      // Pulse = 1 failed attempt
    input  wire       auth_success,   // Pulse = clears fail counter

    // Outputs
    output reg        tamper_alert,   // 1 = currently under attack
    output reg        zeroize,        // 1-cycle pulse = erase key NOW
    output reg        system_lock,    // 1 = permanently locked
    output reg [3:0]  fail_count      // Current failure count (debug)
);

    // --------------------------------------------------------
    // Internal Alarm Signals
    // --------------------------------------------------------
    wire voltage_alarm;
    wire temp_alarm;
    wire fail_alarm;
    wire any_tamper;

    assign voltage_alarm = (voltage_level > VOLTAGE_MAX) ||
                            (voltage_level < VOLTAGE_MIN);

    assign temp_alarm    = (temp_level > TEMP_MAX) ||
                            (temp_level < TEMP_MIN);

    assign fail_alarm    = (fail_count >= MAX_FAILURES);

    assign any_tamper    = voltage_alarm || temp_alarm || fail_alarm;

    // --------------------------------------------------------
    // Failure Counter Logic
    // --------------------------------------------------------
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            fail_count <= 0;
        end
        else begin
            if (system_lock) begin
                // Locked - ignore further attempts
                fail_count <= fail_count;
            end
            else if (auth_fail) begin
                fail_count <= fail_count + 1;
            end
            else if (auth_success) begin
                fail_count <= 0;  // Reset on successful auth
            end
        end
    end

    // --------------------------------------------------------
    // Main Tamper Detection + Lock Logic
    // --------------------------------------------------------
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            tamper_alert <= 0;
            zeroize      <= 0;
            system_lock  <= 0;
        end
        else begin

            // Default: no zeroize pulse unless triggered this cycle
            zeroize <= 0;

            if (system_lock) begin
                // STAY LOCKED - sticky until hardware reset
                tamper_alert <= 1;
                system_lock  <= 1;
            end
            else if (any_tamper) begin
                // NEW tamper event detected
                tamper_alert <= 1;
                zeroize      <= 1;   // Pulse to erase key THIS cycle
                system_lock  <= 1;   // Latch lock permanently
            end
            else begin
                tamper_alert <= 0;
                system_lock  <= 0;
            end
        end
    end

endmodule