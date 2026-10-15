| Design | Class | Mutation | Lock checksum | Lint | LCM sim | EQY | CDC re-check |
|---|---|---|---|---|---|---|---|
| soc | equivalent | wfull compare as XOR-reduce | pass | pass | pass | PASS | pass |
| soc | functional_bug | full flag compares against un-inverted MSBs | pass | pass | **FAIL** (8157) | FAIL | - |
| soc | sync_edit | second synchronizer stage samples d directly | **FAIL** | pass | **FAIL** (8146) | FAIL | - |
| soc | gray_binary | write pointer launched in binary | pass | pass | **FAIL** (2541) | FAIL | - |
| soc | comb_launch | Gray pointer driven combinationally from the binary register | pass | pass | pass | FAIL | **FAIL** |
| async_fifo | equivalent | full compare as XOR-reduce | pass | pass | pass | PASS | pass |
| async_fifo | functional_bug | binary increment ignores full | pass | pass | pass | FAIL | pass |
| async_fifo | sync_edit | read-pointer synchronizer reduced to one stage | **FAIL** | pass | **FAIL** (4) | FAIL | - |
| async_fifo | gray_binary | write pointer launched in binary | pass | pass | pass | FAIL | **FAIL** |
