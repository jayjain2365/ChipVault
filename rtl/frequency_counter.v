`timescale 1ns / 1ps

module frequency_counter #(
    parameter WINDOW_CYCLES  = 1000,
    parameter COUNTER_WIDTH  = 16
)(
    input  wire clk,
    input  wire reset,
    input  wire ro_signal,
    input  wire start,
    output reg  done,
    output reg  [COUNTER_WIDTH-1:0] count_value
);

    // --------------------------------------------------------
    // Internal Registers
    // --------------------------------------------------------
    reg [COUNTER_WIDTH-1:0] ro_count;
    reg [31:0]              window_count;
    reg                     measuring;

    // --------------------------------------------------------
    // Double Flop Synchronizer for ro_signal
    // Brings ro_signal safely into clk domain
    // --------------------------------------------------------
    reg ro_sync_1, ro_sync_2, ro_sync_3;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            ro_sync_1 <= 0;
            ro_sync_2 <= 0;
            ro_sync_3 <= 0;
        end
        else begin
            ro_sync_1 <= ro_signal;   // First flop
            ro_sync_2 <= ro_sync_1;   // Second flop
            ro_sync_3 <= ro_sync_2;   // Third flop
        end
    end

    // Rising edge detected in clk domain
    wire ro_rising = (ro_sync_2 == 1'b1) && (ro_sync_3 == 1'b0);

    // --------------------------------------------------------
    // Main Control Logic
    // --------------------------------------------------------
    always @(posedge clk or posedge reset) begin

        if (reset) begin
            ro_count     <= 0;
            window_count <= 0;
            measuring    <= 0;
            done         <= 0;
            count_value  <= 0;
        end

        else begin

            // START condition
            if (start && !measuring && !done) begin
                measuring    <= 1;
                window_count <= 0;
                ro_count     <= 0;
                done         <= 0;
            end

            // MEASURING state
            else if (measuring) begin

                // Count RO rising edges
                if (ro_rising)
                    ro_count <= ro_count + 1;

                // Count reference clock cycles
                if (window_count < WINDOW_CYCLES - 1) begin
                    window_count <= window_count + 1;
                end

                // Window complete
                else begin
                    measuring   <= 0;
                    count_value <= ro_count;
                    done        <= 1;
                end
            end

        end
    end

endmodule