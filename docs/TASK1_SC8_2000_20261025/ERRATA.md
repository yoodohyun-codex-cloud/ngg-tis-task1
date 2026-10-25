# Terminology correction to SC8 report a31cabc8

The reported manufactured 0.0200608%→0.00576461% is the **FVM shared-interface flux error relative to the exact analytic continuum solution at k_fd**. It is not an error against an exact discrete-network truth. This isolates vertical discretization for the finite-difference lateral symbol. Physical-k versus k_fd captures lateral-symbol error separately. The values, original calculation, original report and all raw data are preserved; REPORT-v2.md corrects this wording.

The actual SC8 cylinder has no known exact continuum solution. Its independent one-sided mismatch is not an analytic truth error; the unchanged5% flags remain failed and adoption/fullconvergence remain false.
