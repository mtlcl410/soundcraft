## Verification of the Beat Clock corrections in their owning PR

Revision `{head}` contains the corrections previously reviewed in the MTC branch. The tests run without enabling MTC or external Beat Clock following.

| Path exercised | Failure in the old behavior | Expected result |
|---|---|---|
| A new locate overtakes a queued SPP | The superseded position can reach the output. | The queue drops messages from the old transport pass, including an SPP due exactly at the new locate. An unchanged pass still sends its queued sequence. |
| An audible presentation outlives its tempo-map revision | Uncached output can be encoded against the latest session. | Wait for a matching map and pass. A destination already holding that exact map can continue. |
| A Stop fails to reach the driver | Relaunch begins with Start and F8. | Retry Stop before Start and the first F8. |
| Rendered delay crosses a sample-rate edit | The old 4,800-frame delay from a 48 kHz callback was reported as 50 ms after a switch to 96 kHz. | The same rendered delay remains 100 ms. |
| Worker stalls during clock repayment | Repayment can remain active past its window. | A new transport positioning sequence takes over when that window expires. A normal recovery repays all ticks within a beat. |
| Rounded pulse boundary and out-of-range SPP | A duplicate F8 can be scheduled on launch and an SPP warning can disappear on the next poll. | Deliver one launch clock and retain the warning until position changes. |
| Duplicate endpoint ID on an unnamed device | A named device can still appear usable with the same ID. | Exclude the ambiguous endpoint and retain independent devices. |
| Endpoint remains listed after bounded retries | Recovery can stop checking the listed endpoint. | Permit a new presence probe after the cooldown and recheck the original callback fault under the graph lock. |
| Manual reconnect and output selection | A recovered idle warning can persist or recovery can target a superseded host/device. | Clear the stale warning on success and retain the actual selected host and device after a failed Apply. |

The local red run reproduced 13 previous behaviors on `7ff81296`. A fourteenth failure came from the deliberate mutation described below. The corresponding fourteen tests then passed in the #1662 layer.

The route-isolation regression sends distinct message types to two routes. Swapping the queued route IDs in a mutation makes the test fail. This mutation tests the assertion's ability to detect a routing mix-up. Physical MIDI measurements remain the earlier acceptance evidence. [Original review, results and prior hardware evidence](https://github.com/storytold/soundcraft/pull/1663#issuecomment-7074865328)

