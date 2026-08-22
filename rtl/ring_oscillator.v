`timescale 1ns / 1ps

module ring_oscillator #(
    parameter N_STAGES   = 5,
    parameter GATE_DELAY = 1      // Delay of each gate (ns)
)(
    input  wire enable,
    output wire out
);

    (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *)
    wire [N_STAGES-1:0] stage;

    (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *)
    wire feedback;

    (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *)
    wire gated_fb;

    // Enable gate
    and #(GATE_DELAY) AND0 (gated_fb, feedback, enable);

    genvar i;
    generate
        for(i = 0; i < N_STAGES; i = i + 1)
        begin : INV_CHAIN

            if(i == 0)
                not #(GATE_DELAY) INV0(stage[0], gated_fb);
            else
                not #(GATE_DELAY) INVX(stage[i], stage[i-1]);

        end
    endgenerate

    assign feedback = stage[N_STAGES-1];
    assign out      = stage[N_STAGES-1];

endmodule