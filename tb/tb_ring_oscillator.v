`timescale 1ns / 1ps

module tb_ring_oscillator;

    reg tb_enable;
    wire tb_out;

    ring_oscillator #(
        .N_STAGES(5),
        .GATE_DELAY(1)
    ) DUT (
        .enable(tb_enable),
        .out(tb_out)
    );

    initial begin

        $dumpfile("ring_oscillator.vcd");
        $dumpvars(0, tb_ring_oscillator);

        tb_enable = 0;

        // Wait before enabling
        #50;

        tb_enable = 1;

        // Let oscillator run
        #500;

        tb_enable = 0;

        #100;

        tb_enable = 1;

        #500;

        $finish;
    end

endmodule